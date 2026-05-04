"""
Trading Engine
- Auto-trading bot (toggle ON/OFF)
- AI Scalping bot (1-min candles, Bank Nifty / Nifty options)
- Signal → execution pipeline
- Risk management enforcement
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
import pytz

from kotak_service import kotak
from risk_manager import RiskManager

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

MARKET_OPEN  = (9, 15)
MARKET_CLOSE = (15, 25)

OPTIONS_SYMBOLS = {
    "BANKNIFTY": {"exchange": "nse_fo", "lot_size": 15},
    "NIFTY":     {"exchange": "nse_fo", "lot_size": 50},
    "FINNIFTY":  {"exchange": "nse_fo", "lot_size": 40},
}


def market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    t = (now.hour, now.minute)
    return MARKET_OPEN <= t <= MARKET_CLOSE


class ScalpingBot:
    """
    1-minute scalping bot for Bank Nifty / Nifty options.
    Strategy: momentum breakout with 1:3 risk-reward.
    """

    def __init__(self):
        self.running      = False
        self._thread: Optional[threading.Thread] = None
        self.risk = RiskManager(
            max_risk_pct=0.005,   # 0.5% per scalp trade
            max_positions=2,
            max_daily_loss_pct=0.02,
            sl_pct=0.003,         # 0.3% SL for scalping
            min_confidence=0.60
        )
        self.log: List[Dict] = []
        self.config = {
            "symbol":       "BANKNIFTY",
            "option_type":  "CE",          # CE or PE
            "expiry":       "current",
            "lot_size":     15,
            "lots":         1,
            "rr_ratio":     3.0,           # 1:3 risk-reward
            "sl_points":    30,            # SL in points
            "target_points": 90,           # target = sl * rr_ratio
            "dry_run":      True,
        }

    def configure(self, **kwargs):
        self.config.update(kwargs)
        logger.info(f"Scalping bot configured: {self.config}")

    def start(self):
        if self.running:
            return {"status": "already_running"}
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Scalping bot started")
        return {"status": "started", "config": self.config}

    def stop(self):
        self.running = False
        logger.info("Scalping bot stopped")
        return {"status": "stopped"}

    def _run_loop(self):
        while self.running:
            try:
                if not market_open():
                    time.sleep(60)
                    continue
                if not kotak.is_logged_in:
                    time.sleep(30)
                    continue
                self._scan_and_trade()
            except Exception as e:
                logger.error(f"Scalping loop error: {e}")
            time.sleep(60)  # 1-minute candle interval

    def _scan_and_trade(self):
        """Core scalping logic — runs every 1 minute."""
        symbol = self.config["symbol"]
        try:
            # Get index LTP
            index_map = {"BANKNIFTY": "NIFTY BANK", "NIFTY": "NIFTY 50"}
            index_sym = index_map.get(symbol, symbol)

            # Momentum signal: compare last 3 LTPs
            # In production: use websocket tick data
            # Here we poll quotes as a fallback
            quote = kotak.get_quote(symbol, "nse_fo", "ohlc")
            if not quote:
                return

            open_  = float(quote.get("open",  0))
            high   = float(quote.get("high",  0))
            low    = float(quote.get("low",   0))
            close  = float(quote.get("close", 0) or quote.get("ltp", 0))

            if not all([open_, high, low, close]):
                return

            # Simple momentum: bullish if close > open and close near high
            body_pct  = (close - open_) / open_ * 100 if open_ else 0
            wick_pct  = (high - close)  / (high - low) * 100 if (high - low) else 50

            if body_pct > 0.15 and wick_pct < 30:
                signal = "CE"   # bullish → buy call
            elif body_pct < -0.15 and wick_pct > 70:
                signal = "PE"   # bearish → buy put
            else:
                self._log_event("SCAN", symbol, "No signal — sideways candle")
                return

            option_type = signal
            sl_pts      = self.config["sl_points"]
            tgt_pts     = int(sl_pts * self.config["rr_ratio"])
            lots        = self.config["lots"]
            lot_size    = OPTIONS_SYMBOLS.get(symbol, {}).get("lot_size", 15)
            qty         = lots * lot_size

            self._log_event("SIGNAL", symbol,
                            f"{option_type} signal | body={body_pct:.2f}% | SL={sl_pts}pts TGT={tgt_pts}pts")

            if self.config["dry_run"]:
                self._log_event("DRY_RUN", symbol,
                                f"Would BUY {symbol} {option_type} {qty} qty | SL={sl_pts} TGT={tgt_pts}")
                return

            # Place real order (requires instrument token lookup for options)
            # In production: search_scrip for the specific strike
            self._log_event("SKIPPED", symbol,
                            "Live options execution requires strike selection — use manual order")

        except Exception as e:
            self._log_event("ERROR", symbol, str(e))

    def _log_event(self, event_type: str, symbol: str, message: str):
        entry = {
            "type":      event_type,
            "symbol":    symbol,
            "message":   message,
            "timestamp": datetime.now(IST).isoformat()
        }
        self.log.append(entry)
        if len(self.log) > 200:
            self.log = self.log[-200:]
        logger.info(f"[SCALP/{event_type}] {symbol}: {message}")

    def get_log(self) -> List[Dict]:
        return list(reversed(self.log[-50:]))

    def get_status(self) -> Dict:
        return {
            "running":    self.running,
            "config":     self.config,
            "log_count":  len(self.log),
            "risk_status": self.risk.get_status()
        }


class AutoTrader:
    """
    Auto-trading bot — connects AI signals to order execution.
    Toggle ON/OFF. Runs on a configurable interval.
    """

    def __init__(self):
        self.running      = False
        self._thread: Optional[threading.Thread] = None
        self.risk = RiskManager(
            max_risk_pct=0.01,
            max_positions=5,
            max_daily_loss_pct=0.03,
            sl_pct=0.015,
            min_confidence=0.68
        )
        self.log: List[Dict] = []
        self.config = {
            "symbols":          ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"],
            "scan_interval_s":  300,   # scan every 5 minutes
            "min_confidence":   68.0,
            "product":          "MIS",
            "dry_run":          True,
            "max_trades_day":   10,
        }
        self._trades_today = 0

    def configure(self, **kwargs):
        self.config.update(kwargs)
        self.risk.min_confidence = self.config["min_confidence"] / 100
        logger.info(f"AutoTrader configured: {self.config}")

    def start(self):
        if self.running:
            return {"status": "already_running"}
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("AutoTrader started")
        return {"status": "started", "config": self.config}

    def stop(self):
        self.running = False
        logger.info("AutoTrader stopped")
        return {"status": "stopped"}

    def _run_loop(self):
        while self.running:
            try:
                if not market_open():
                    time.sleep(60)
                    continue
                if not kotak.is_logged_in:
                    self._log("WARN", "Not logged in — waiting")
                    time.sleep(30)
                    continue
                if self._trades_today >= self.config["max_trades_day"]:
                    self._log("LIMIT", "Max daily trades reached — pausing")
                    time.sleep(300)
                    continue
                self._scan_symbols()
            except Exception as e:
                logger.error(f"AutoTrader loop error: {e}")
            time.sleep(self.config["scan_interval_s"])

    def _scan_symbols(self):
        from data_fetcher import get_stock_data, get_fundamentals
        from tech_indicators import add_technical_indicators
        from model import train_predict_model
        from sentiment import get_stock_sentiment
        from decision import generate_recommendation

        for symbol in self.config["symbols"]:
            if not self.running:
                break
            try:
                ticker = f"{symbol}.NS"
                df = get_stock_data(ticker, "3mo")
                if df.empty:
                    continue
                df          = add_technical_indicators(df)
                tech_pred   = train_predict_model(df)
                sentiment   = get_stock_sentiment(symbol)
                decision    = generate_recommendation(tech_pred, sentiment)

                action     = decision["action"]
                confidence = decision["confidence"]

                self._log("SCAN", f"{symbol} → {action} ({confidence:.1f}%)")

                if confidence < self.config["min_confidence"]:
                    continue
                if action not in ("Buy", "Strong Buy", "Sell", "Strong Sell"):
                    continue

                self._execute(symbol, action, confidence)
                time.sleep(2)  # rate limit between symbols

            except Exception as e:
                self._log("ERROR", f"{symbol}: {e}")

    def _execute(self, symbol: str, action: str, confidence: float):
        try:
            capital = kotak.get_available_margin()
        except Exception:
            capital = 0.0

        txn = "B" if "Buy" in action else "S"
        risk_ok = self.risk.can_trade(symbol, "Buy" if txn == "B" else "Sell",
                                      confidence / 100, capital)
        if not risk_ok["allowed"]:
            self._log("BLOCKED", f"{symbol}: {risk_ok['reason']}")
            return

        try:
            ltp = kotak.get_ltp(symbol)
        except Exception as e:
            self._log("ERROR", f"{symbol} LTP failed: {e}")
            return

        sl_price = self.risk.calculate_stop_loss(ltp, txn)
        qty      = self.risk.calculate_quantity(capital, ltp, sl_price)
        if qty == 0:
            self._log("SKIP", f"{symbol}: qty=0 (insufficient capital)")
            return

        if self.config["dry_run"]:
            self._log("DRY_RUN",
                      f"{action} {symbol} qty={qty} @ ₹{ltp:.2f} | SL=₹{sl_price:.2f}")
            self._trades_today += 1
            return

        try:
            resp = kotak.place_market_order(symbol, txn, qty, self.config["product"])
            oid  = resp.get("nOrdNo", "?")
            kotak.place_sl_order(symbol, "S" if txn == "B" else "B",
                                 qty, sl_price, sl_price, self.config["product"])
            self.risk.register_position(symbol, ltp, qty, txn, oid, sl_price)
            self._trades_today += 1
            self._log("EXECUTED",
                      f"{action} {symbol} qty={qty} @ ₹{ltp:.2f} | SL=₹{sl_price:.2f} | OID={oid}")
        except Exception as e:
            self._log("ERROR", f"{symbol} order failed: {e}")

    def _log(self, event: str, message: str):
        entry = {"type": event, "message": message,
                 "timestamp": datetime.now(IST).isoformat()}
        self.log.append(entry)
        if len(self.log) > 500:
            self.log = self.log[-500:]
        logger.info(f"[AUTO/{event}] {message}")

    def get_log(self, n: int = 50) -> List[Dict]:
        return list(reversed(self.log[-n:]))

    def get_status(self) -> Dict:
        return {
            "running":       self.running,
            "config":        self.config,
            "trades_today":  self._trades_today,
            "risk_status":   self.risk.get_status()
        }


# Singletons
scalping_bot = ScalpingBot()
auto_trader  = AutoTrader()
