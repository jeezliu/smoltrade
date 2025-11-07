"""Paper trading execution client for simulating live orders."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from .base import ExecutionClient, Order, Trade
from ..portfolio import Portfolio


class PaperBroker(ExecutionClient):
    """Simulated broker that executes market orders at the given price."""

    def __init__(
        self,
        starting_cash: float,
        slippage_bps: float = 5.0,
        commission: float = 0.0,
    ) -> None:
        self.portfolio = Portfolio(cash=starting_cash)
        self.slippage_bps = slippage_bps
        self.commission = commission
        self.trade_history: List[Trade] = []

    def submit_order(
        self,
        order: Order,
        market_price: float,
        timestamp: datetime | None = None,
    ) -> Trade:
        if market_price <= 0:
            raise ValueError("market_price must be positive")
        timestamp = timestamp or datetime.now(tz=timezone.utc)

        slippage_mult = 1 + (self.slippage_bps / 10_000)
        if order.side == "buy":
            fill_price = market_price * slippage_mult
        else:
            fill_price = market_price / slippage_mult

        self.portfolio.update_on_fill(
            symbol=order.symbol,
            quantity=order.quantity,
            fill_price=fill_price,
            side=order.side,
            commission=self.commission,
        )

        trade = Trade(order=order, price=fill_price, timestamp=timestamp, commission=self.commission)
        self.trade_history.append(trade)
        return trade

    def reset(self, starting_cash: float | None = None) -> None:
        self.trade_history.clear()
        self.portfolio.reset(starting_cash)
