"""Autotrader package exposing core components for building automated trading bots."""

from .config import BotConfig
from .engine import AutoTradingBot
from .llm_engine import LLMAutoTradingBot
from .agents import LLMClient, MarketAnalyzer, TradingScheduler

__all__ = [
    "BotConfig", 
    "AutoTradingBot", 
    "LLMAutoTradingBot",
    "LLMClient", 
    "MarketAnalyzer", 
    "TradingScheduler"
]
