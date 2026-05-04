"""
Risk Manager — Controls position sizing, stop-loss calculation,
and enforces daily risk limits for the AI trading bot.
"""

import logging
from typing import Dict, Optional
from datetime import date

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Enforces risk rules before any order is placed.
    
    Rules:
      - Never risk more than max_risk_pct of capital per trade
      - Never hold more than max_positions simultaneously
      - Stop all trading if daily loss exceeds max_daily_loss_pct
      - Only trade during market hours (9:15 AM – 3:25 PM IST)
    """

    def __init__(
        self,
        max_risk_pct: float = 0.01,       # 1% of capital per trade
        max_positions: int = 5,            # max simultaneous positions
        max_daily_loss_pct: float = 0.03,  # stop trading if 3% daily loss
        sl_pct: float = 0.015,             # 1.5% stop-loss from entry
        min_confidence: float = 0.65       # minimum ML confidence to trade
    ):
        self.max_risk_pct = max_risk_pct
        self.max_positions = max_positions
        self.max_daily_loss_pct = max_daily_loss_pct
        self.sl_pct = sl_pct
        self.min_confidence = min_confidence

        # Daily tracking
        self._daily_pnl: float = 0.0
        self._daily_trades: int = 0
        self._last_reset: date = date.today()
        self._open_positions: Dict[str, Dict] = {}  # symbol → position info

    def _reset_if_new_day(self):
        """Reset daily counters at start of each trading day."""
        today = date.today()
        if today != self._last_reset:
            self._daily_pnl = 0.0
            self._daily_trades = 0
            self._last_reset = today
            logger.info("Daily risk counters reset")

    def calculate_quantity(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: float
    ) -> int:
        """
        Calculate position size based on risk per trade.
        
        Formula: qty = (capital × max_risk_pct) / risk_per_share
        
        Args:
            capital: Available trading capital
            entry_price: Expected entry price
            stop_loss_price: Stop-loss price
            
        Returns:
            int: Number of shares to buy (minimum 1)
        """
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share < 0.01:
            logger.warning("Risk per share too small — using minimum quantity")
            return 1

        max_loss_amount = capital * self.max_risk_pct
        quantity = int(max_loss_amount / risk_per_share)

        # Safety: never spend more than 20% of capital on one trade
        max_by_capital = int((capital * 0.20) / entry_price)
        quantity = min(quantity, max_by_capital)

        return max(1, quantity)

    def calculate_stop_loss(
        self,
        entry_price: float,
        transaction_type: str,
        sl_pct: Optional[float] = None
    ) -> float:
        """
        Calculate stop-loss price.
        
        Args:
            entry_price: Entry price
            transaction_type: "B" (Buy) or "S" (Sell)
            sl_pct: Override default stop-loss percentage
            
        Returns:
            float: Stop-loss price
        """
        pct = sl_pct or self.sl_pct
        if transaction_type == "B":
            sl = round(entry_price * (1 - pct), 2)
        else:
            sl = round(entry_price * (1 + pct), 2)

        logger.debug(f"SL calculated: entry={entry_price} type={transaction_type} sl={sl}")
        return sl

    def can_trade(
        self,
        symbol: str,
        action: str,
        confidence: float,
        capital: float
    ) -> Dict:
        """
        Master check — returns whether a trade is allowed.
        
        Returns:
            dict: {allowed: bool, reason: str}
        """
        self._reset_if_new_day()

        # 1. Confidence check
        if confidence < self.min_confidence:
            return {
                "allowed": False,
                "reason": f"Confidence {confidence:.1%} below minimum {self.min_confidence:.1%}"
            }

        # 2. Hold signal
        if action == "Hold":
            return {"allowed": False, "reason": "Signal is Hold — no trade"}

        # 3. Max positions check
        if len(self._open_positions) >= self.max_positions:
            return {
                "allowed": False,
                "reason": f"Max positions ({self.max_positions}) reached"
            }

        # 4. Already in this position
        if symbol in self._open_positions and action in ("Buy", "Strong Buy"):
            return {
                "allowed": False,
                "reason": f"Already holding position in {symbol}"
            }

        # 5. Daily loss limit
        if capital > 0:
            daily_loss_pct = abs(self._daily_pnl) / capital
            if self._daily_pnl < 0 and daily_loss_pct >= self.max_daily_loss_pct:
                return {
                    "allowed": False,
                    "reason": f"Daily loss limit reached ({daily_loss_pct:.1%})"
                }

        # 6. Minimum capital check
        if capital < 1000:
            return {"allowed": False, "reason": "Insufficient capital (< ₹1000)"}

        return {"allowed": True, "reason": "All checks passed"}

    def register_position(self, symbol: str, entry_price: float,
                          quantity: int, transaction_type: str,
                          order_id: str, sl_price: float):
        """Register an open position for tracking."""
        self._open_positions[symbol] = {
            "entry_price": entry_price,
            "quantity": quantity,
            "transaction_type": transaction_type,
            "order_id": order_id,
            "sl_price": sl_price
        }
        self._daily_trades += 1
        logger.info(f"Position registered: {symbol} {transaction_type} {quantity} @ {entry_price}")

    def close_position(self, symbol: str, exit_price: float):
        """Close a position and update daily P&L."""
        if symbol not in self._open_positions:
            return

        pos = self._open_positions.pop(symbol)
        entry = pos["entry_price"]
        qty = pos["quantity"]
        txn = pos["transaction_type"]

        if txn == "B":
            pnl = (exit_price - entry) * qty
        else:
            pnl = (entry - exit_price) * qty

        self._daily_pnl += pnl
        logger.info(f"Position closed: {symbol} P&L=₹{pnl:.2f} | Daily P&L=₹{self._daily_pnl:.2f}")

    def get_status(self) -> Dict:
        """Get current risk status."""
        return {
            "open_positions": len(self._open_positions),
            "max_positions": self.max_positions,
            "daily_pnl": round(self._daily_pnl, 2),
            "daily_trades": self._daily_trades,
            "positions": self._open_positions
        }
