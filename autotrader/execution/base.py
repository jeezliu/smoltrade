"""Execution client abstractions and common order data structures."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Side = Literal["buy", "sell"]
OrderType = Literal["market", "limit"]
TimeInForce = Literal["day", "gtc"]


@dataclass(slots=True)
class Order:
    symbol: str
    quantity: float
    side: Side
    type: OrderType = "market"
    time_in_force: TimeInForce = "day"


@dataclass(slots=True)
class Trade:
    order: Order
    price: float
    timestamp: datetime
    commission: float = 0.0

    @property
    def gross_value(self) -> float:
        return self.price * self.order.quantity

    @property
    def net_value(self) -> float:
        if self.order.side == "buy":
            return self.gross_value + self.commission
        return self.gross_value - self.commission


class ExecutionClient(ABC):
    """Interface for submitting orders to a broker or exchange."""

    @abstractmethod
    def submit_order(
        self,
        order: Order,
        market_price: float,
        timestamp: datetime | None = None,
    ) -> Trade:
        """Submit an order for execution and return the resulting fill."""

    def reset(self, *_: object, **__: object) -> None:  # pragma: no cover - optional
        """Optional hook to reset client state between runs."""
        raise NotImplementedError("This execution client does not support reset()")
