"""Strategy implementations for the autotrader package."""

from .base import BaseStrategy, Signal
from .moving_average import MovingAverageCrossStrategy

__all__ = ["BaseStrategy", "Signal", "MovingAverageCrossStrategy"]
