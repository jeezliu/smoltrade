"""Portfolio and position management utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional


@dataclass
class Position:
    """Representation of an open position for a single symbol."""

    symbol: str
    quantity: float = 0.0
    average_price: float = 0.0

    def market_value(self, price: float) -> float:
        return self.quantity * price

    def is_flat(self) -> bool:
        return self.quantity == 0


class Portfolio:
    """Track current cash balance and instrument positions."""

    def __init__(self, cash: float) -> None:
        self._starting_cash = cash
        self.cash: float = cash
        self.positions: Dict[str, Position] = {}

    # --- Position helpers -------------------------------------------------

    def get_position(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)

    def position_size(self, symbol: str) -> float:
        position = self.get_position(symbol)
        return float(position.quantity) if position else 0.0

    def update_on_fill(
        self,
        symbol: str,
        quantity: float,
        fill_price: float,
        side: str,
        commission: float = 0.0,
    ) -> None:
        side = side.lower()
        if side not in {"buy", "sell"}:
            raise ValueError("side must be either 'buy' or 'sell'")
        if quantity <= 0:
            raise ValueError("quantity must be positive")

        position = self.positions.get(symbol)
        if position is None:
            position = Position(symbol=symbol)
            self.positions[symbol] = position

        if side == "buy":
            total_cost = quantity * fill_price + commission
            new_quantity = position.quantity + quantity
            if new_quantity <= 0:
                raise RuntimeError("Invalid position size after buy execution")
            position.average_price = (
                (position.quantity * position.average_price + quantity * fill_price)
                / new_quantity
            )
            position.quantity = new_quantity
            self.cash -= total_cost
        else:
            if quantity > position.quantity + 1e-9:
                raise RuntimeError("Cannot sell more than current position size")
            proceeds = quantity * fill_price - commission
            position.quantity -= quantity
            self.cash += proceeds
            if position.quantity <= 1e-9:
                del self.positions[symbol]

    # --- Valuation helpers ------------------------------------------------

    def market_value(self, prices: Mapping[str, float]) -> float:
        return sum(
            position.market_value(prices[position.symbol])
            for position in self.positions.values()
            if position.symbol in prices
        )

    def total_equity(self, prices: Mapping[str, float]) -> float:
        return self.cash + self.market_value(prices)

    def reset(self, cash: Optional[float] = None) -> None:
        self.cash = self._starting_cash if cash is None else float(cash)
        self.positions.clear()
        if cash is not None:
            self._starting_cash = float(cash)

    def holdings_snapshot(self) -> Dict[str, float]:
        return {symbol: pos.quantity for symbol, pos in self.positions.items()}
