"""Yahoo Finance market data provider implementation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from .base import MarketDataProvider

try:
    import yfinance as yf
except ModuleNotFoundError as exc:  # pragma: no cover - dependency missing
    raise RuntimeError(
        "yfinance is required for the YFinanceDataProvider. Install the optional dependency "
        "or choose a different data provider."
    ) from exc


class YFinanceDataProvider(MarketDataProvider):
    """Fetch market data using the public Yahoo Finance API via yfinance."""

    def __init__(self, auto_adjust: bool = True) -> None:
        self.auto_adjust = auto_adjust

    def get_history(
        self,
        symbol: str,
        interval: str,
        lookback: Optional[int] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        if lookback is None and start is None:
            raise ValueError("Either lookback or start date must be provided")

        query_kwargs = {
            "interval": interval,
            "auto_adjust": self.auto_adjust,
            "progress": False,
        }

        if start is not None:
            query_kwargs["start"] = start
        if end is not None:
            query_kwargs["end"] = end
        if lookback is not None and start is None:
            query_kwargs["period"] = f"{max(1, lookback)}d"

        data = yf.download(symbol, **query_kwargs)
        if data.empty:
            return data

        # Normalise column casing and naming across yfinance versions
        data = data.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
            }
        )

        # Ensure index is timezone-aware (Yahoo returns naive timestamps)
        if data.index.tzinfo is None:
            data.index = data.index.tz_localize("UTC")

        return data

    def latest_price(self, symbol: str) -> float:
        info = yf.Ticker(symbol)
        price = info.fast_info.get("lastPrice")
        if price is None:
            intraday = info.history(period="1d")
            if intraday.empty:
                raise RuntimeError(f"Unable to retrieve latest price for {symbol}")
            price = float(intraday["Close"].iloc[-1])
        return float(price)
