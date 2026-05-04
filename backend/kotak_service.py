"""
Kotak Neo API v2 — Direct REST implementation based on official docs.

Auth flow (3 steps per official documentation):
  Step 1: TOTP Registration (one-time, done on website)
  Step 2: POST /login/1.0/tradeApiLogin  → view_token + view_sid
  Step 3: POST /login/1.0/tradeApiValidate → trade_token + trade_sid + base_url

All post-login API calls use:
  Headers: Auth=trade_token, Sid=trade_sid, Authorization=consumer_key, neo-fin-key=neotradeapi
  Base URL: base_url from step 3 response
"""

import os, time, logging, json
from typing import Optional, Dict, List
from io import StringIO
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=str(_env_path), override=True)
logger = logging.getLogger(__name__)

# ── Optional imports ──────────────────────────────────────────────────────────
try:
    import pyotp
    PYOTP_OK = True
except ImportError:
    PYOTP_OK = False
    logger.warning("pyotp not installed: pip install pyotp")

try:
    import requests as _requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

try:
    import pandas as pd
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False

# ── Constants ─────────────────────────────────────────────────────────────────
LOGIN_URL    = "https://mis.kotaksecurities.com/login/1.0/tradeApiLogin"
VALIDATE_URL = "https://mis.kotaksecurities.com/login/1.0/tradeApiValidate"
NEO_FIN_KEY  = "neotradeapi"


class KotakService:
    """
    Direct REST wrapper for Kotak Neo API v2.
    Uses requests library directly — no SDK dependency for auth.
    """
    _instance: Optional["KotakService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Session state
        self.is_logged_in  = False
        self.consumer_key  = ""
        self.view_token    = ""
        self.view_sid      = ""
        self.trade_token   = ""
        self.trade_sid     = ""
        self.base_url      = ""
        self._scrip_cache: Dict[str, Dict] = {}

        # Load consumer key
        self.consumer_key = os.getenv("KOTAK_CONSUMER_KEY", "").strip()
        if not self.consumer_key or self.consumer_key.startswith("YOUR_"):
            logger.warning("KOTAK_CONSUMER_KEY not set — trading disabled")

        self._initialized = True
        logger.info("KotakService initialised (direct REST mode)")

    def is_available(self) -> bool:
        return bool(self.consumer_key and not self.consumer_key.startswith("YOUR_"))

    # ── Auth headers ──────────────────────────────────────────────────────────

    def _login_headers(self) -> Dict:
        """Headers for Step 2 (totp login) and Step 3 (validate)."""
        return {
            "Authorization": self.consumer_key,
            "neo-fin-key":   NEO_FIN_KEY,
            "Content-Type":  "application/json",
        }

    def _trade_headers(self) -> Dict:
        """Headers for all post-login trading API calls."""
        return {
            "Authorization": self.consumer_key,
            "neo-fin-key":   NEO_FIN_KEY,
            "Auth":          self.trade_token,
            "Sid":           self.trade_sid,
            "Content-Type":  "application/json",
        }

    # ── Login ─────────────────────────────────────────────────────────────────

    def login(self, manual_totp: str = "") -> Dict:
        """
        Full 2-step login per official Kotak docs.

        Step 2: POST tradeApiLogin  → view_token, view_sid
        Step 3: POST tradeApiValidate → trade_token, trade_sid, base_url
        """
        if not self.is_available():
            raise RuntimeError("KOTAK_CONSUMER_KEY not set in .env")

        mobile = os.getenv("KOTAK_MOBILE", "").strip()
        ucc    = os.getenv("KOTAK_UCC",    "").strip()
        mpin   = os.getenv("KOTAK_MPIN",   "").strip()

        # Validate credentials
        missing = [k for k, v in {"KOTAK_MOBILE": mobile,
                                   "KOTAK_UCC": ucc,
                                   "KOTAK_MPIN": mpin}.items()
                   if not v or v.startswith("YOUR_")]
        if missing:
            raise ValueError(f"Missing in .env: {', '.join(missing)}")
        if len(mpin) != 6 or not mpin.isdigit():
            raise ValueError(f"KOTAK_MPIN must be exactly 6 digits, got: '{mpin}'")

        # ── Determine TOTP ──
        if manual_totp and len(manual_totp.strip()) == 6 and manual_totp.strip().isdigit():
            current_totp = manual_totp.strip()
            logger.info(f"Using manual TOTP: {current_totp}")
        else:
            if not PYOTP_OK:
                return {"status": "need_manual_totp",
                        "message": "pyotp not installed. Enter 6-digit code manually."}
            secret = os.getenv("KOTAK_TOTP_SECRET", "").strip().replace(" ", "").upper()
            if not secret or secret.startswith("YOUR_"):
                return {"status": "need_manual_totp",
                        "message": "KOTAK_TOTP_SECRET not set. Enter 6-digit code manually."}
            totp_obj  = pyotp.TOTP(secret)
            remaining = 30 - (int(time.time()) % 30)
            if remaining < 5:
                logger.info(f"TOTP expires in {remaining}s — waiting for next window...")
                time.sleep(remaining + 1)
            current_totp = totp_obj.now()
            logger.info(f"Auto TOTP: {current_totp} (valid {30-(int(time.time())%30)}s)")

        # ── STEP 2: tradeApiLogin ──────────────────────────────────────────────
        logger.info(f"Step 2: tradeApiLogin | mobile={mobile} ucc={ucc} totp={current_totp}")
        try:
            r1 = _requests.post(
                LOGIN_URL,
                headers=self._login_headers(),
                json={"mobileNumber": mobile, "ucc": ucc, "totp": current_totp},
                timeout=15
            )
            resp1 = r1.json()
            logger.info(f"tradeApiLogin response [{r1.status_code}]: {resp1}")
        except Exception as e:
            raise RuntimeError(f"tradeApiLogin network error: {e}") from e

        # Parse step 2 response
        data1 = resp1.get("data", resp1)

        # Handle error responses
        if r1.status_code != 200 or resp1.get("status") == "error":
            err_msg = resp1.get("message", str(resp1))
            err_code = str(resp1.get("errorCode", r1.status_code))

            if "totp" in err_msg.lower() and "invalid" in err_msg.lower():
                return {"status": "invalid_totp",
                        "message": "Invalid TOTP. Open Google Authenticator → Kotak entry → enter the current 6-digit code manually."}
            if "register" in err_msg.lower() or "10508" in err_code:
                return {"status": "totp_not_registered",
                        "message": "TOTP not registered. Visit kotaksecurities.com → Trade API → Register for TOTP."}
            raise RuntimeError(f"tradeApiLogin error [{err_code}]: {err_msg}")

        # Also check nested error
        if isinstance(data1, dict) and data1.get("error"):
            errs = data1["error"]
            code = str(errs[0].get("code","")) if errs else ""
            msg  = str(errs[0].get("message","")) if errs else str(errs)
            if code == "10508":
                return {"status": "totp_not_registered",
                        "message": "TOTP not registered. Visit kotaksecurities.com → Trade API → Register for TOTP."}
            if code == "10506":
                return {"status": "invalid_totp",
                        "message": "Invalid TOTP. Enter the current 6-digit code from Google Authenticator manually."}
            raise RuntimeError(f"tradeApiLogin error [{code}]: {msg}")

        # Extract view token + sid
        self.view_token = data1.get("token", "")
        self.view_sid   = data1.get("sid",   "")

        if not self.view_token or not self.view_sid:
            raise RuntimeError(f"tradeApiLogin: missing token/sid in response: {data1}")

        logger.info(f"Step 2 OK — view_token acquired, sid={self.view_sid[:8]}...")

        # ── STEP 3: tradeApiValidate ───────────────────────────────────────────
        logger.info("Step 3: tradeApiValidate with MPIN...")
        validate_headers = {
            **self._login_headers(),
            "sid":  self.view_sid,
            "Auth": self.view_token,
        }
        try:
            r2 = _requests.post(
                VALIDATE_URL,
                headers=validate_headers,
                json={"mpin": mpin},
                timeout=15
            )
            resp2 = r2.json()
            logger.info(f"tradeApiValidate response [{r2.status_code}]: {resp2}")
        except Exception as e:
            raise RuntimeError(f"tradeApiValidate network error: {e}") from e

        data2 = resp2.get("data", resp2)

        if r2.status_code != 200 or resp2.get("status") == "error":
            err_msg = resp2.get("message", str(resp2))
            raise RuntimeError(f"tradeApiValidate error: {err_msg} — check KOTAK_MPIN")

        if isinstance(data2, dict) and data2.get("error"):
            errs = data2["error"]
            code = str(errs[0].get("code","")) if errs else ""
            msg  = str(errs[0].get("message","")) if errs else str(errs)
            raise RuntimeError(f"tradeApiValidate error [{code}]: {msg} — check KOTAK_MPIN")

        # Extract trade credentials
        self.trade_token = data2.get("token",   "")
        self.trade_sid   = data2.get("sid",     "")
        self.base_url    = data2.get("baseUrl", "https://cis.kotaksecurities.com").rstrip("/")

        if not self.trade_token:
            raise RuntimeError(f"tradeApiValidate: missing trade token in response: {data2}")

        self.is_logged_in = True
        greeting = data2.get("greetingName", "")
        logger.info(f"✅ Login complete | base_url={self.base_url} | user={greeting}")

        return {
            "status":   "success",
            "method":   "totp_direct",
            "message":  f"Logged in successfully{' — ' + greeting if greeting else ''}",
            "base_url": self.base_url,
            "ucc":      data2.get("ucc", ""),
        }

    def logout(self) -> Dict:
        self.is_logged_in = False
        self.view_token = self.view_sid = self.trade_token = self.trade_sid = ""
        logger.info("Session cleared")
        return {"status": "logged_out"}

    def _require_login(self):
        if not self.is_logged_in:
            raise RuntimeError("Not logged in. Call /api/kotak/login first.")

    # ── Scrip Master ──────────────────────────────────────────────────────────

    def _get_scrip_csv_urls(self) -> Dict[str, str]:
        """
        GET {base_url}/script-details/1.0/masterscrip/file-paths
        Returns dict: {exchange_segment -> csv_url}
        """
        url = f"{self.base_url}/script-details/1.0/masterscrip/file-paths"
        headers = {"Authorization": self.consumer_key}
        r = _requests.get(url, headers=headers, timeout=10)
        data = r.json()
        logger.info(f"scrip file-paths: {data}")
        paths = data.get("data", {}).get("filesPaths", [])
        # Map segment name from URL filename
        result = {}
        for p in paths:
            fname = p.split("/")[-1].replace(".csv","").replace("-v1","")
            result[fname] = p
        return result

    def get_instrument_token(self, symbol: str, exchange: str = "nse_cm") -> Dict:
        """
        Lookup instrument token from scrip master CSV.
        Uses official file-paths endpoint, downloads CSV, caches result.
        Columns per docs: pSymbol, pExchSeg, pTrdSymbol, lLotSize, pToken
        """
        key = f"{exchange}_{symbol.upper()}"
        if key in self._scrip_cache:
            return self._scrip_cache[key]

        try:
            urls = self._get_scrip_csv_urls()
            # Try exact match then fallback variants
            csv_url = urls.get(exchange) or urls.get(f"{exchange}-v1") or urls.get(f"{exchange}_cm")
            if not csv_url:
                raise ValueError(f"No scrip CSV found for exchange '{exchange}'. Available: {list(urls.keys())}")

            logger.info(f"Downloading scrip master: {csv_url}")
            r   = _requests.get(csv_url, timeout=30)
            df  = pd.read_csv(StringIO(r.text))
            logger.info(f"Scrip CSV columns: {list(df.columns)}")

            # pSymbol is the lookup key per docs
            sym_col = "pSymbol" if "pSymbol" in df.columns else df.columns[0]
            match   = df[df[sym_col].astype(str).str.upper() == symbol.upper()]

            if match.empty:
                # Try pTrdSymbol as fallback
                if "pTrdSymbol" in df.columns:
                    match = df[df["pTrdSymbol"].astype(str).str.upper() == symbol.upper()]
            if match.empty:
                raise ValueError(f"Symbol '{symbol}' not found in {exchange} scrip master")

            row = match.iloc[0]
            result = {
                "instrument_token": str(row.get("pToken", row.get("pSymbol", symbol))),
                "trading_symbol":   str(row.get("pTrdSymbol", symbol)),
                "exchange_segment": str(row.get("pExchSeg", exchange)),
                "lot_size":         int(row.get("lLotSize", 1)),
                "p_symbol":         str(row.get("pSymbol", symbol)),
            }
            self._scrip_cache[key] = result
            logger.info(f"Cached: {symbol} → token={result['instrument_token']} ts={result['trading_symbol']}")
            return result

        except Exception as e:
            logger.error(f"get_instrument_token failed for {symbol}/{exchange}: {e}")
            raise ValueError(f"Instrument lookup failed for {symbol}: {e}") from e

    # ── Market Data ───────────────────────────────────────────────────────────

    def get_ltp(self, symbol: str, exchange: str = "nse_cm") -> float:
        """
        GET {base_url}/script-details/1.0/quotes/neosymbol/{exchange}|{pSymbol}/ltp
        Uses pSymbol from scrip master per official docs.
        """
        self._require_login()
        try:
            inst     = self.get_instrument_token(symbol, exchange)
            p_symbol = inst.get("p_symbol", symbol)
            url      = f"{self.base_url}/script-details/1.0/quotes/neosymbol/{exchange}|{p_symbol}/ltp"
            headers  = {"Authorization": self.consumer_key, "Content-Type": "application/json"}
            r        = _requests.get(url, headers=headers, timeout=8)
            data     = r.json()
            logger.debug(f"LTP response for {symbol}: {data}")

            # Response is a list per docs
            if isinstance(data, list) and data:
                return float(data[0].get("ltp", 0))
            if isinstance(data, dict):
                return float(data.get("ltp", data.get("data", {}).get("ltp", 0)))
        except Exception as e:
            logger.warning(f"LTP failed for {symbol}: {e}")
        return 0.0

    def get_quote(self, symbol: str, exchange: str = "nse_cm",
                  quote_type: str = "all") -> Dict:
        """
        GET {base_url}/script-details/1.0/quotes/neosymbol/{exchange}|{pSymbol}/{filter}
        filter: all, ltp, ohlc, depth, 52W, scrip_details, circuit_limits, oi
        """
        self._require_login()
        try:
            inst     = self.get_instrument_token(symbol, exchange)
            p_symbol = inst.get("p_symbol", symbol)
            filt     = quote_type if quote_type in ("all","ltp","ohlc","depth","52W","scrip_details","circuit_limits","oi") else "all"
            url      = f"{self.base_url}/script-details/1.0/quotes/neosymbol/{exchange}|{p_symbol}/{filt}"
            headers  = {"Authorization": self.consumer_key, "Content-Type": "application/json"}
            r        = _requests.get(url, headers=headers, timeout=8)
            data     = r.json()
            return data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else {}
        except Exception as e:
            logger.warning(f"get_quote failed for {symbol}: {e}")
            return {}

    # ── Orders ────────────────────────────────────────────────────────────────

    def _place_order(self, payload: Dict) -> Dict:
        """Core order placement using official endpoint."""
        self._require_login()
        url = f"{self.base_url}/quick/order/rule/ms/place"
        # Convert to form-encoded jData format per official docs
        import urllib.parse
        jdata = json.dumps(payload)
        try:
            headers = {**self._trade_headers(), "Content-Type": "application/x-www-form-urlencoded"}
            r = _requests.post(url, headers=headers,
                               data=urllib.parse.urlencode({"jData": jdata}),
                               timeout=10)
            resp = r.json()
            logger.info(f"Order response [{r.status_code}]: {resp}")
            return resp
        except Exception as e:
            raise RuntimeError(f"Order placement failed: {e}") from e

    def place_market_order(self, symbol: str, txn: str, qty: int,
                           product: str = "MIS", exchange: str = "nse_cm") -> Dict:
        inst = self.get_instrument_token(symbol, exchange)
        # qty must be multiple of lot size per docs
        lot  = inst.get("lot_size", 1)
        qty  = max(lot, (qty // lot) * lot)
        return self._place_order({
            "am": "NO", "dq": "0", "es": inst["exchange_segment"],
            "mp": "0",  "pc": product, "pf": "N",
            "pr": "0",  "pt": "MKT",  "qt": str(qty),
            "rt": "DAY","tp": "0",    "ts": inst["trading_symbol"],
            "tt": txn,  "ig": "AI_BOT"
        })

    def place_limit_order(self, symbol: str, txn: str, qty: int, price: float,
                          product: str = "MIS", exchange: str = "nse_cm") -> Dict:
        inst = self.get_instrument_token(symbol, exchange)
        lot  = inst.get("lot_size", 1)
        qty  = max(lot, (qty // lot) * lot)
        return self._place_order({
            "am": "NO", "dq": "0", "es": inst["exchange_segment"],
            "mp": "0",  "pc": product, "pf": "N",
            "pr": str(price), "pt": "L", "qt": str(qty),
            "rt": "DAY", "tp": "0", "ts": inst["trading_symbol"],
            "tt": txn, "ig": "AI_BOT"
        })

    def place_sl_order(self, symbol: str, txn: str, qty: int,
                       price: float, trigger_price: float,
                       product: str = "MIS", exchange: str = "nse_cm") -> Dict:
        inst = self.get_instrument_token(symbol, exchange)
        lot  = inst.get("lot_size", 1)
        qty  = max(lot, (qty // lot) * lot)
        return self._place_order({
            "am": "NO", "dq": "0", "es": inst["exchange_segment"],
            "mp": "0",  "pc": product, "pf": "N",
            "pr": str(price), "pt": "SL", "qt": str(qty),
            "rt": "DAY", "tp": str(trigger_price),
            "ts": inst["trading_symbol"], "tt": txn, "ig": "AI_BOT_SL"
        })

    def modify_order(self, order_id: str, price: Optional[float] = None,
                     quantity: Optional[int] = None,
                     trigger_price: Optional[float] = None) -> Dict:
        self._require_login()
        url = f"{self.base_url}/quick/order/rule/ms/modify"
        payload: Dict = {"no": order_id}
        if price         is not None: payload["pr"] = str(price)
        if quantity      is not None: payload["qt"] = str(quantity)
        if trigger_price is not None: payload["tp"] = str(trigger_price)
        import urllib.parse
        headers = {**self._trade_headers(), "Content-Type": "application/x-www-form-urlencoded"}
        r = _requests.post(url, headers=headers,
                           data=urllib.parse.urlencode({"jData": json.dumps(payload)}),
                           timeout=10)
        return r.json()

    def cancel_order(self, order_id: str, verify: bool = True) -> Dict:
        self._require_login()
        url = f"{self.base_url}/quick/order/rule/ms/cancel"
        import urllib.parse
        headers = {**self._trade_headers(), "Content-Type": "application/x-www-form-urlencoded"}
        r = _requests.post(url, headers=headers,
                           data=urllib.parse.urlencode({"jData": json.dumps({"no": order_id})}),
                           timeout=10)
        return r.json()

    # ── Portfolio ─────────────────────────────────────────────────────────────

    def get_positions(self) -> List[Dict]:
        """
        GET {base_url}/quick/user/positions
        Headers: Auth, Sid, neo-fin-key
        Returns list of position objects with fields:
        trdSym, sym, qty, buyAmt, sellAmt, prod, exSeg, etc.
        """
        self._require_login()
        url = f"{self.base_url}/quick/user/positions"
        try:
            r    = _requests.get(url, headers=self._trade_headers(), timeout=8)
            data = r.json()
            logger.info(f"positions raw [{r.status_code}]: {str(data)[:300]}")
            # Response: {"stat":"Ok","stCode":200,"data":[...]}
            if isinstance(data, dict):
                d = data.get("data", [])
                return d if isinstance(d, list) else []
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error(f"get_positions failed: {e}")
            return []

    def get_holdings(self) -> List[Dict]:
        """
        GET {base_url}/portfolio/v1/holdings
        Headers: Auth, Sid, neo-fin-key, accept=application/json
        Returns list with fields per new API:
        instrumentName, symbol, displaySymbol, quantity, averagePrice,
        holdingCost, closingPrice, mktValue, unrealisedGainLoss,
        sellableQuantity, exchangeSegment, instrumentToken, etc.
        """
        self._require_login()
        url = f"{self.base_url}/portfolio/v1/holdings"
        headers = {
            **self._trade_headers(),
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            r    = _requests.get(url, headers=headers, timeout=8)
            data = r.json()
            logger.info(f"holdings raw [{r.status_code}]: {str(data)[:300]}")
            if isinstance(data, dict):
                d = data.get("data", [])
                return d if isinstance(d, list) else []
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error(f"get_holdings failed: {e}")
            return []

    def get_order_book(self) -> List[Dict]:
        """
        GET {base_url}/quick/user/orders
        Headers: Auth, Sid, neo-fin-key, accept=application/json
        Response: {"stat":"Ok","stCode":200,"data":[...]}
        Key fields: nOrdNo, ordSt, trdSym, qty, prc, avgPrc,
                    trnsTp, prcTp, vldt, rejRsn, exSeg, ordDtTm
        """
        self._require_login()
        url = f"{self.base_url}/quick/user/orders"
        headers = {
            **self._trade_headers(),
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            r    = _requests.get(url, headers=headers, timeout=8)
            data = r.json()
            logger.info(f"order_book [{r.status_code}]: {str(data)[:200]}")
            if isinstance(data, dict):
                d = data.get("data", [])
                return d if isinstance(d, list) else []
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"get_order_book failed: {e}")
            return []

    def get_order_history(self, order_id: str) -> List[Dict]:
        """
        POST {base_url}/quick/user/order/history
        Body: jData={"nOrdNo":"<order_id>"}  (url-encoded)
        Returns full lifecycle of a single order.
        Key fields: nOrdNo, ordSt, flDtTm, rejRsn, qty, prc, avgPrc, prod
        """
        self._require_login()
        url = f"{self.base_url}/quick/user/order/history"
        headers = {
            **self._trade_headers(),
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        import urllib.parse
        jdata = json.dumps({"nOrdNo": order_id})
        try:
            r    = _requests.post(url, headers=headers,
                                   data=urllib.parse.urlencode({"jData": jdata}),
                                   timeout=8)
            data = r.json()
            logger.info(f"order_history [{r.status_code}]: {str(data)[:200]}")
            if isinstance(data, dict):
                d = data.get("data", [])
                return d if isinstance(d, list) else []
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"get_order_history failed: {e}")
            return []

    def get_trade_book(self) -> List[Dict]:
        """
        GET {base_url}/quick/user/trades
        Headers: Auth, Sid, neo-fin-key, accept=application/json
        Response: {"stat":"Ok","stCode":200,"data":[...]}
        Key fields: nOrdNo, trdSym, qty, avgPrc, fldQty,
                    flDt, exTm, prcTp, prod, trnsTp, exOrdId
        """
        self._require_login()
        url = f"{self.base_url}/quick/user/trades"
        headers = {
            **self._trade_headers(),
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            r    = _requests.get(url, headers=headers, timeout=8)
            data = r.json()
            logger.info(f"trade_book [{r.status_code}]: {str(data)[:200]}")
            if isinstance(data, dict):
                d = data.get("data", [])
                return d if isinstance(d, list) else []
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"get_trade_book failed: {e}")
            return []

    def get_available_margin(self, segment="ALL", exchange="ALL", product="ALL") -> float:
        """
        POST {base_url}/quick/user/limits
        jData: {"seg":"ALL","exch":"ALL","prod":"ALL"}
        Returns Net available margin from response field "Net".
        """
        self._require_login()
        url = f"{self.base_url}/quick/user/limits"
        headers = {
            **self._trade_headers(),
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        import urllib.parse
        jdata = json.dumps({"seg": segment, "exch": exchange, "prod": product})
        try:
            r    = _requests.post(url, headers=headers,
                                   data=urllib.parse.urlencode({"jData": jdata}),
                                   timeout=8)
            data = r.json()
            logger.info(f"limits raw [{r.status_code}]: {data}")

            if data.get("stat") == "Ok" or data.get("stCode") == 200:
                # Primary key per docs is "Net"
                net = data.get("Net", "0")
                try:
                    val = float(str(net).replace(",", "").strip())
                    if val > 0:
                        logger.info(f"Margin Net={val}")
                        return val
                except Exception:
                    pass
                # Fallback keys
                for key in ["CollateralValue", "NotionalCash", "AdhocMargin"]:
                    try:
                        v = float(str(data.get(key, "0")).replace(",", "").strip())
                        if v > 0:
                            logger.info(f"Margin fallback key={key} val={v}")
                            return v
                    except Exception:
                        pass
            return 0.0
        except Exception as e:
            logger.error(f"get_available_margin failed: {e}")
            return 0.0

    def get_full_limits(self, segment="ALL", exchange="ALL", product="ALL") -> Dict:
        """
        Returns the full limits response dict with all fields:
        Net, CollateralValue, MarginUsed, UnrealizedMtomPrsnt,
        RealizedMtomPrsnt, BoardLotLimit, etc.
        """
        self._require_login()
        url = f"{self.base_url}/quick/user/limits"
        headers = {
            **self._trade_headers(),
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        import urllib.parse
        jdata = json.dumps({"seg": segment, "exch": exchange, "prod": product})
        try:
            r = _requests.post(url, headers=headers,
                                data=urllib.parse.urlencode({"jData": jdata}),
                                timeout=8)
            return r.json()
        except Exception as e:
            logger.error(f"get_full_limits failed: {e}")
            return {}

    def check_margin(self, symbol: str, exchange: str, price: float,
                     order_type: str, product: str, quantity: int,
                     transaction_type: str) -> Dict:
        """
        POST {base_url}/quick/user/check-margin
        jData: {brkName, brnchId, exSeg, prc, prcTp, prod, qty, tok, trnsTp}
        Returns: avlCash, avlMrgn, ordMrgn, reqdMrgn, insufFund, rmsVldtd
        """
        self._require_login()
        inst = self.get_instrument_token(symbol, exchange)
        url  = f"{self.base_url}/quick/user/check-margin"
        headers = {
            **self._trade_headers(),
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        import urllib.parse
        jdata = json.dumps({
            "brkName": "KOTAK",
            "brnchId": "ONLINE",
            "exSeg":   inst["exchange_segment"],
            "prc":     str(price),
            "prcTp":   order_type,
            "prod":    product,
            "qty":     str(quantity),
            "tok":     inst["instrument_token"],
            "trnsTp":  transaction_type,
        })
        try:
            r    = _requests.post(url, headers=headers,
                                   data=urllib.parse.urlencode({"jData": jdata}),
                                   timeout=8)
            data = r.json()
            logger.info(f"check-margin [{r.status_code}]: {data}")
            return data
        except Exception as e:
            logger.error(f"check_margin failed: {e}")
            return {"error": str(e)}

    def get_raw_limits(self) -> Dict:
        """Debug: return raw limits response."""
        return self.get_full_limits()


# ── Singleton ─────────────────────────────────────────────────────────────────
kotak = KotakService()
