"""
AI Signals Service
Generates Buy/Sell/Hold signals with confidence scores
for a watchlist of symbols using ML + FinBERT + technicals.
Results are cached and refreshed on demand.
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

DEFAULT_WATCHLIST = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "SBIN", "WIPRO", "ITC", "AXISBANK", "BAJFINANCE",
    "MARUTI", "SUNPHARMA", "HINDUNILVR", "KOTAKBANK", "ASIANPAINT",
]


class AISignalService:
    """
    Generates and caches AI signals for a watchlist.
    Runs a background refresh thread.
    """

    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._lock  = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.watchlist: List[str] = list(DEFAULT_WATCHLIST)
        self.refresh_interval = 300   # 5 minutes

    def start_background_refresh(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()
        logger.info("AI Signal background refresh started")

    def stop(self):
        self._running = False

    def _refresh_loop(self):
        while self._running:
            try:
                self._refresh_all()
            except Exception as e:
                logger.error(f"Signal refresh error: {e}")
            time.sleep(self.refresh_interval)

    def _refresh_all(self):
        for symbol in self.watchlist:
            if not self._running:
                break
            try:
                sig = self._compute_signal(symbol)
                with self._lock:
                    self._cache[symbol] = sig
            except Exception as e:
                logger.warning(f"Signal failed for {symbol}: {e}")
            time.sleep(1)  # avoid hammering APIs

    def _compute_signal(self, symbol: str) -> Dict:
        from data_fetcher import get_stock_data, get_fundamentals
        from tech_indicators import add_technical_indicators
        from model import train_predict_model
        from sentiment import get_stock_sentiment
        from decision import generate_recommendation

        ticker = f"{symbol}.NS"
        df     = get_stock_data(ticker, "3mo")
        if df.empty:
            return self._empty_signal(symbol, "No data")

        fundamentals = get_fundamentals(ticker)
        df           = add_technical_indicators(df)
        tech_pred    = train_predict_model(df)
        sentiment    = get_stock_sentiment(symbol)
        decision     = generate_recommendation(tech_pred, sentiment)

        # Latest price
        price = fundamentals.get("Current Price") or (
            float(df["Close"].iloc[-1]) if not df.empty else 0
        )

        # RSI
        rsi = float(df["RSI"].iloc[-1]) if "RSI" in df.columns and not df["RSI"].isna().all() else 50.0

        # Price change %
        if len(df) >= 2:
            prev  = float(df["Close"].iloc[-2])
            curr  = float(df["Close"].iloc[-1])
            chg   = round((curr - prev) / prev * 100, 2) if prev else 0
        else:
            chg = 0.0

        return {
            "symbol":     symbol,
            "action":     decision["action"],
            "confidence": decision["confidence"],
            "ml_signal":  decision["ml_signal"],
            "sentiment":  decision["sentiment_signal"],
            "price":      price,
            "change_pct": chg,
            "rsi":        round(rsi, 1),
            "updated_at": datetime.now(IST).isoformat(),
            "error":      None,
        }

    def _empty_signal(self, symbol: str, reason: str) -> Dict:
        return {
            "symbol": symbol, "action": "Hold", "confidence": 0,
            "ml_signal": "Hold", "sentiment": "Neutral",
            "price": 0, "change_pct": 0, "rsi": 50,
            "updated_at": datetime.now(IST).isoformat(), "error": reason,
        }

    def get_signal(self, symbol: str, force_refresh: bool = False) -> Dict:
        """Get signal for one symbol. Refreshes if not cached or forced."""
        if force_refresh or symbol not in self._cache:
            try:
                sig = self._compute_signal(symbol)
                with self._lock:
                    self._cache[symbol] = sig
            except Exception as e:
                return self._empty_signal(symbol, str(e))
        with self._lock:
            return self._cache.get(symbol, self._empty_signal(symbol, "Not computed"))

    def get_all_signals(self) -> List[Dict]:
        """Return cached signals for entire watchlist."""
        with self._lock:
            return [self._cache.get(s, self._empty_signal(s, "Pending"))
                    for s in self.watchlist]

    def set_watchlist(self, symbols: List[str]):
        self.watchlist = [s.upper() for s in symbols]
        logger.info(f"Watchlist updated: {self.watchlist}")


# Singleton
signal_service = AISignalService()
