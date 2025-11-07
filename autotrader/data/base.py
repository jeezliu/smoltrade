"""Abstract base classes for market data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import pandas as pd


class MarketDataProvider(ABC):
    """Interface for obtaining market data for the trading engine."""

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        interval: str,
        lookback: Optional[int] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Return historical OHLCV data indexed by timestamp.

        Implementations should return a dataframe containing at least the columns
        ``open``, ``high``, ``low``, ``close`` and ``volume``. The index should
        be timezone-aware where possible.
        """

    @abstractmethod
    def latest_price(self, symbol: str) -> float:
        """Return the most recent tradable price for *symbol*."""
