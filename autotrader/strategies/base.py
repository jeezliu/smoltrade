"""Base strategy definitions for the trading bot."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

from ..portfolio import Portfolio


@dataclass(slots=True)
class Signal:
    symbol: str
    action: str  # "buy", "sell" or "hold"
    timestamp: datetime
    confidence: float = 1.0


class BaseStrategy(ABC):
    """Abstract base class for portfolio strategies."""

    symbol: str

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    @property
    @abstractmethod
    def minimum_history(self) -> int:
        """Return minimum candles required to produce a trade decision."""

    @abstractmethod
    def generate_signal(
        self,
        data: pd.DataFrame,
        portfolio: Portfolio,
    ) -> Optional[Signal]:
        """Inspect historical data and produce a trading signal."""
