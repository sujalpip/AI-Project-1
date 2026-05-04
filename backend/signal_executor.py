"""
Signal Executor — Bridges the AI/ML decision engine with Kotak Neo order execution.
Receives signals from the ML model + sentiment analysis and places real orders.
"""

import logging
import time
from typing import Dict, Optional
from datetime import datetime
import pytz

from kotak_service import kotak
from risk_manager import RiskManager

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

MARKET_OPEN  = (9, 15)   # 9:15 AM IST
MARKET_CLOSE = (15, 25)  # 3:25 PM IST (5 min before close)


def is_market_open() -> bool:
    """Check if NSE market is currently open."""
    now = datetime.now(IST)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    current = (now.hour, now.minute)
    return MARKET_OPEN <= current <= MARKET_CLOSE


def retry_on_failure(func, max_attempts: int = 3, delay: float = 1.0):
    """Simple retry wrapper with exponential backoff."""
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            wait = delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)


class SignalExecutor:
    """
    Executes AI trading signals as real orders via Kotak Neo API.
    
    Flow:
      ML Signal (Buy/Sell/Hold + confidence)
        → RiskManager.can_trade() check
        → Get LTP from Kotak
        → Calculate position size + stop-loss
        → Place market order
        → Place stop-loss order
        → Register position
        → Return execution result
    """

    def __init__(self, min_confidence: float = 0.65, sl_pct: float = 0.015):
        self.risk = RiskManager(
            max_risk_pct=0.01,
            max_positions=5,
            max_daily_loss_pct=0.03,
            sl_pct=sl_pct,
            min_confidence=min_confidence
        )
        self.execution_log: list = []

    def execute_signal(
        self,
        symbol: str,
        action: str,
        confidence: float,
        product: str = "MIS",
        exchange: str = "nse_cm",
        dry_run: bool = False
    ) -> Dict:
        """
        Main entry point — execute a trading signal.
        
        Args:
            symbol: NSE symbol (e.g., "RELIANCE") — without .NS suffix
            action: "Buy", "Strong Buy", "Sell", "Strong Sell", "Hold"
            confidence: ML confidence 0–100 (will be normalised to 0–1)
            product: "MIS" (intraday) or "CNC" (delivery)
            exchange: Exchange segment
            dry_run: If True, simulate without placing real orders
            
        Returns:
            dict: Execution result with order details
        """
        # Normalise confidence to 0–1
        conf_norm = confidence / 100.0 if confidence > 1 else confidence

        # Map action to transaction type
        if action in ("Buy", "Strong Buy"):
            transaction_type = "B"
            simplified_action = "Buy"
        elif action in ("Sell", "Strong Sell"):
            transaction_type = "S"
            simplified_action = "Sell"
        else:
            return self._log_result(symbol, action, conf_norm, "skipped",
                                    "Signal is Hold — no trade executed")

        # Market hours check
        if not is_market_open() and not dry_run:
            return self._log_result(symbol, action, conf_norm, "skipped",
                                    "Market is closed. Orders not placed.")

        # Kotak availability check
        if not kotak.is_available():
            return self._log_result(symbol, action, conf_norm, "error",
                                    "Kotak service not configured. Check .env file.")

        if not kotak.is_logged_in:
            return self._log_result(symbol, action, conf_norm, "error",
                                    "Not logged in to Kotak. Call /api/kotak/login first.")

        # Risk check
        try:
            capital = kotak.get_available_margin()
        except Exception as e:
            capital = 0.0
            logger.warning(f"Could not fetch margin: {e}")

        risk_check = self.risk.can_trade(symbol, simplified_action, conf_norm, capital)
        if not risk_check["allowed"]:
            return self._log_result(symbol, action, conf_norm, "blocked",
                                    risk_check["reason"])

        # Get current price
        try:
            ltp = retry_on_failure(lambda: kotak.get_ltp(symbol, exchange))
        except Exception as e:
            return self._log_result(symbol, action, conf_norm, "error",
                                    f"Failed to get LTP: {e}")

        # Calculate position size and stop-loss
        sl_price = self.risk.calculate_stop_loss(ltp, transaction_type)
        quantity = self.risk.calculate_quantity(capital, ltp, sl_price)

        if quantity == 0:
            return self._log_result(symbol, action, conf_norm, "skipped",
                                    "Calculated quantity is 0 — insufficient capital")

        logger.info(f"Executing: {symbol} {simplified_action} qty={quantity} "
                    f"ltp=₹{ltp} sl=₹{sl_price} conf={conf_norm:.1%}")

        if dry_run:
            result = self._log_result(
                symbol, action, conf_norm, "dry_run",
                f"DRY RUN — Would place {simplified_action} {quantity} shares @ ₹{ltp} | SL: ₹{sl_price}",
                order_id="DRY_RUN",
                ltp=ltp,
                quantity=quantity,
                sl_price=sl_price
            )
            return result

        # Place main order
        try:
            order_resp = retry_on_failure(
                lambda: kotak.place_market_order(symbol, transaction_type, quantity, product, exchange)
            )
            order_id = order_resp.get("nOrdNo") or order_resp.get("order_id", "unknown")
            logger.info(f"✅ Main order placed: {order_id}")

        except Exception as e:
            return self._log_result(symbol, action, conf_norm, "error",
                                    f"Order placement failed: {e}")

        # Place stop-loss order (opposite direction)
        sl_transaction = "S" if transaction_type == "B" else "B"
        sl_order_id = None
        try:
            sl_resp = retry_on_failure(
                lambda: kotak.place_sl_order(
                    symbol, sl_transaction, quantity,
                    price=sl_price,
                    trigger_price=sl_price,
                    product=product,
                    exchange=exchange
                )
            )
            sl_order_id = sl_resp.get("nOrdNo") or sl_resp.get("order_id")
            logger.info(f"✅ SL order placed: {sl_order_id} @ ₹{sl_price}")

        except Exception as e:
            logger.warning(f"⚠️  SL order failed (main order still active): {e}")

        # Register position with risk manager
        self.risk.register_position(
            symbol=symbol,
            entry_price=ltp,
            quantity=quantity,
            transaction_type=transaction_type,
            order_id=order_id,
            sl_price=sl_price
        )

        return self._log_result(
            symbol, action, conf_norm, "executed",
            f"{simplified_action} {quantity} shares @ ₹{ltp} | SL: ₹{sl_price}",
            order_id=order_id,
            sl_order_id=sl_order_id,
            ltp=ltp,
            quantity=quantity,
            sl_price=sl_price
        )

    def _log_result(
        self,
        symbol: str,
        action: str,
        confidence: float,
        status: str,
        message: str,
        order_id: Optional[str] = None,
        sl_order_id: Optional[str] = None,
        ltp: Optional[float] = None,
        quantity: Optional[int] = None,
        sl_price: Optional[float] = None
    ) -> Dict:
        """Build and log execution result."""
        result = {
            "symbol": symbol,
            "action": action,
            "confidence": round(confidence * 100, 2),
            "status": status,
            "message": message,
            "order_id": order_id,
            "sl_order_id": sl_order_id,
            "ltp": ltp,
            "quantity": quantity,
            "sl_price": sl_price,
            "timestamp": datetime.now(IST).isoformat()
        }
        self.execution_log.append(result)
        logger.info(f"[{status.upper()}] {symbol}: {message}")
        return result

    def get_execution_log(self) -> list:
        """Return full execution history."""
        return self.execution_log

    def get_risk_status(self) -> Dict:
        """Return current risk manager status."""
        return self.risk.get_status()


# Singleton instance
executor = SignalExecutor()
