"""
Kotak Neo WebSocket Feed Manager
Connects to HSM (market data) and HSI (order feed) using
trade_token, trade_sid, and dataCenter from login response.

WebSocket URL format (from official docs / HSLibDemo inspection):
  wss://mlhsm.kotaksecurities.com  ← HSM market feed
  wss://mlhsi.kotaksecurities.com  ← HSI order feed

Subscribe format: nse_cm|11536&1
  exchange|scrip_id&channel_type
  channel_type: 1=scrip, 2=index, 3=depth

Max: 16 channels, 200 scrips
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

HSM_URL = "wss://mlhsm.kotaksecurities.com"
HSI_URL = "wss://mlhsi.kotaksecurities.com"

MAX_SCRIPS   = 200
MAX_CHANNELS = 16


class MarketFeed:
    """
    HSM WebSocket client for live market data.
    Connects using trade_token + trade_sid + dataCenter.
    """

    def __init__(self):
        self.ws              = None
        self.connected       = False
        self.subscribed      : List[str] = []   # list of "exchange|scrip_id"
        self._lock           = threading.Lock()
        self._ticks          : Dict[str, Dict] = {}   # scrip_id → latest tick
        self._tick_callbacks : List[Callable]  = []
        self._thread         : Optional[threading.Thread] = None
        self._reconnect      = True
        self._creds          : Dict = {}

    def connect(self, trade_token: str, trade_sid: str, data_center: str) -> bool:
        """
        Establish HSM WebSocket connection.
        Credentials come from tradeApiValidate response.
        """
        self._creds = {
            "token":       trade_token,
            "sid":         trade_sid,
            "data_center": data_center,
        }
        self._reconnect = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        # Wait up to 5s for connection
        for _ in range(10):
            if self.connected:
                return True
            time.sleep(0.5)
        return self.connected

    def disconnect(self):
        self._reconnect = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        self.connected = False
        self.subscribed.clear()
        logger.info("MarketFeed disconnected")

    def _run(self):
        """Background thread — connects and maintains WebSocket."""
        try:
            import websocket as ws_lib
        except ImportError:
            logger.error("websocket-client not installed: pip install websocket-client")
            return

        while self._reconnect:
            try:
                token      = self._creds.get("token", "")
                sid        = self._creds.get("sid", "")
                dc         = self._creds.get("data_center", "")

                # Build connection URL with auth params
                url = f"{HSM_URL}?Authorization={token}&Sid={sid}&dataCenter={dc}"
                logger.info(f"Connecting HSM: {HSM_URL} dc={dc}")

                self.ws = ws_lib.WebSocketApp(
                    url,
                    on_open    = self._on_open,
                    on_message = self._on_message,
                    on_error   = self._on_error,
                    on_close   = self._on_close,
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)

            except Exception as e:
                logger.error(f"HSM WebSocket error: {e}")

            if self._reconnect:
                logger.info("HSM reconnecting in 5s...")
                time.sleep(5)

    def _on_open(self, ws):
        self.connected = True
        logger.info("HSM connected")
        # Re-subscribe if reconnecting
        if self.subscribed:
            self._send_subscribe(self.subscribed)

    def _on_message(self, ws, message):
        try:
            data = json.loads(message) if isinstance(message, str) else message
            self._process_tick(data)
        except Exception as e:
            logger.debug(f"HSM message parse error: {e} | raw: {str(message)[:100]}")

    def _on_error(self, ws, error):
        logger.warning(f"HSM error: {error}")
        self.connected = False

    def _on_close(self, ws, code, msg):
        self.connected = False
        logger.info(f"HSM closed: {code} {msg}")

    def _process_tick(self, data: dict):
        """Parse incoming tick and store latest value."""
        # Kotak tick format varies — handle common shapes
        scrip_id = (data.get("tk") or data.get("scrip_id") or
                    data.get("instrumentToken") or data.get("token", ""))
        if not scrip_id:
            return

        tick = {
            "scrip_id":  str(scrip_id),
            "ltp":       float(data.get("ltp") or data.get("last_price") or 0),
            "open":      float(data.get("o")   or data.get("open")  or 0),
            "high":      float(data.get("h")   or data.get("high")  or 0),
            "low":       float(data.get("l")   or data.get("low")   or 0),
            "close":     float(data.get("c")   or data.get("close") or 0),
            "volume":    int(data.get("v")     or data.get("vol")   or 0),
            "change":    float(data.get("chg") or data.get("change") or 0),
            "change_pct":float(data.get("chgp") or data.get("per_change") or 0),
            "bid":       float(data.get("bp1") or 0),
            "ask":       float(data.get("sp1") or 0),
            "timestamp": datetime.now(IST).isoformat(),
            "raw":       data,
        }

        with self._lock:
            self._ticks[str(scrip_id)] = tick

        for cb in self._tick_callbacks:
            try:
                cb(tick)
            except Exception as e:
                logger.debug(f"Tick callback error: {e}")

    def _send_subscribe(self, scrips: List[str]):
        """
        Send subscription message.
        Format per docs: nse_cm|11536&1
        Multiple: nse_cm|11536&1&nse_cm|11537&1
        """
        if not self.ws or not self.connected:
            return
        # Build subscription string
        sub_str = "&".join(scrips)
        msg = json.dumps({"type": "sub", "scrips": sub_str})
        try:
            self.ws.send(msg)
            logger.info(f"Subscribed: {sub_str}")
        except Exception as e:
            logger.error(f"Subscribe send failed: {e}")

    def subscribe(self, exchange: str, scrip_id: str,
                  feed_type: int = 1) -> bool:
        """
        Subscribe to a scrip.
        feed_type: 1=scrip, 2=index, 3=depth
        Returns False if limit exceeded.
        """
        if len(self.subscribed) >= MAX_SCRIPS:
            logger.warning(f"Max scrips ({MAX_SCRIPS}) reached")
            return False

        entry = f"{exchange}|{scrip_id}&{feed_type}"
        if entry not in self.subscribed:
            self.subscribed.append(entry)
            if self.connected:
                self._send_subscribe([entry])
        return True

    def subscribe_many(self, tokens: List[Dict]) -> int:
        """
        Subscribe to multiple instruments.
        tokens: [{"exchange": "nse_cm", "scrip_id": "11536"}, ...]
        Returns count subscribed.
        """
        count = 0
        for t in tokens:
            if self.subscribe(t.get("exchange","nse_cm"),
                              str(t.get("scrip_id","")),
                              t.get("feed_type", 1)):
                count += 1
        return count

    def unsubscribe(self, exchange: str, scrip_id: str):
        entry = f"{exchange}|{scrip_id}&1"
        if entry in self.subscribed:
            self.subscribed.remove(entry)
        if self.ws and self.connected:
            try:
                msg = json.dumps({"type": "unsub", "scrips": entry})
                self.ws.send(msg)
            except Exception:
                pass

    def get_tick(self, scrip_id: str) -> Optional[Dict]:
        with self._lock:
            return self._ticks.get(str(scrip_id))

    def get_all_ticks(self) -> Dict[str, Dict]:
        with self._lock:
            return dict(self._ticks)

    def add_tick_callback(self, fn: Callable):
        self._tick_callbacks.append(fn)

    def get_status(self) -> Dict:
        return {
            "connected":   self.connected,
            "subscribed":  len(self.subscribed),
            "max_scrips":  MAX_SCRIPS,
            "scrips":      self.subscribed[:20],
            "tick_count":  len(self._ticks),
        }


class OrderFeed:
    """
    HSI WebSocket client for live order updates.
    Same credentials as MarketFeed.
    """

    def __init__(self):
        self.ws          = None
        self.connected   = False
        self._updates    : List[Dict] = []
        self._lock       = threading.Lock()
        self._callbacks  : List[Callable] = []
        self._thread     : Optional[threading.Thread] = None
        self._reconnect  = True
        self._creds      : Dict = {}

    def connect(self, trade_token: str, trade_sid: str, data_center: str) -> bool:
        self._creds = {"token": trade_token, "sid": trade_sid, "data_center": data_center}
        self._reconnect = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        for _ in range(10):
            if self.connected:
                return True
            time.sleep(0.5)
        return self.connected

    def disconnect(self):
        self._reconnect = False
        if self.ws:
            try: self.ws.close()
            except Exception: pass
        self.connected = False

    def _run(self):
        try:
            import websocket as ws_lib
        except ImportError:
            logger.error("websocket-client not installed")
            return

        while self._reconnect:
            try:
                token = self._creds.get("token", "")
                sid   = self._creds.get("sid", "")
                dc    = self._creds.get("data_center", "")
                url   = f"{HSI_URL}?Authorization={token}&Sid={sid}&dataCenter={dc}"
                logger.info(f"Connecting HSI order feed: {HSI_URL}")

                self.ws = ws_lib.WebSocketApp(
                    url,
                    on_open    = lambda ws: self._on_open(ws),
                    on_message = lambda ws, msg: self._on_message(ws, msg),
                    on_error   = lambda ws, err: setattr(self, "connected", False),
                    on_close   = lambda ws, c, m: setattr(self, "connected", False),
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                logger.error(f"HSI error: {e}")
            if self._reconnect:
                time.sleep(5)

    def _on_open(self, ws):
        self.connected = True
        logger.info("HSI order feed connected")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message) if isinstance(message, str) else message
            update = {
                "order_id":  data.get("nOrdNo", data.get("orderId", "")),
                "status":    data.get("ordSt",  data.get("status", "")),
                "symbol":    data.get("trdSym", data.get("symbol", "")),
                "qty":       data.get("qty", 0),
                "price":     data.get("prc", data.get("price", 0)),
                "timestamp": datetime.now(IST).isoformat(),
                "raw":       data,
            }
            with self._lock:
                self._updates.append(update)
                if len(self._updates) > 500:
                    self._updates = self._updates[-500:]
            for cb in self._callbacks:
                try: cb(update)
                except Exception: pass
        except Exception as e:
            logger.debug(f"HSI parse error: {e}")

    def get_updates(self, n: int = 50) -> List[Dict]:
        with self._lock:
            return list(reversed(self._updates[-n:]))

    def add_callback(self, fn: Callable):
        self._callbacks.append(fn)

    def get_status(self) -> Dict:
        return {
            "connected":    self.connected,
            "update_count": len(self._updates),
        }


# ── Singletons ────────────────────────────────────────────────────────────────
market_feed = MarketFeed()
order_feed  = OrderFeed()
