"""Moving average crossover trading strategy implementation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd

from .base import BaseStrategy, Signal
from ..portfolio import Portfolio


class MovingAverageCrossStrategy(BaseStrategy):
    """Classic moving average crossover strategy.

    Generates a buy signal when the short moving average crosses above the long
    moving average and the portfolio is currently flat. Generates a sell signal
    when the short moving average crosses below the long moving average and a
    position is currently open.
    """

    def __init__(
        self,
        symbol: str,
        short_window: int = 20,
        long_window: int = 50,
        minimum_confidence: float = 0.005,
    ) -> None:
        if short_window >= long_window:
            raise ValueError("short_window must be smaller than long_window")
        super().__init__(symbol=symbol)
        self.short_window = short_window
        self.long_window = long_window
        self.minimum_confidence = minimum_confidence

    @property
    def minimum_history(self) -> int:
        return self.long_window + 1

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Optional[Signal]:
        if data.empty or len(data) < self.minimum_history:
            return None

        prices = data["close"].astype(float)
        short_ma = prices.rolling(self.short_window).mean()
        long_ma = prices.rolling(self.long_window).mean()

        latest_short = short_ma.iloc[-1].item()
        latest_long = long_ma.iloc[-1].item()
        prev_short = short_ma.iloc[-2].item()
        prev_long = long_ma.iloc[-2].item()

        if pd.isna([latest_short, latest_long, prev_short, prev_long]).any():
            return None

        signal_time = data.index[-1].to_pydatetime()
        difference = latest_short - latest_long
        confidence = abs(difference) / latest_long if latest_long > 0 else 0.0

        current_position = portfolio.position_size(self.symbol)
        has_position = current_position > 0

        crossed_up = latest_short > latest_long and prev_short <= prev_long
        crossed_down = latest_short < latest_long and prev_short >= prev_long

        if crossed_up and not has_position and confidence >= self.minimum_confidence:
            return Signal(symbol=self.symbol, action="buy", timestamp=signal_time, confidence=confidence)
        if crossed_down and has_position and confidence >= self.minimum_confidence:
            return Signal(symbol=self.symbol, action="sell", timestamp=signal_time, confidence=confidence)

        return None
