"""Autotrader package exposing core components for building automated trading bots."""

from .config import BotConfig
from .engine import AutoTradingBot

__all__ = ["BotConfig", "AutoTradingBot"]
