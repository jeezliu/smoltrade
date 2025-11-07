"""Market data analyzer for LLM trading agent."""

from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

from ..data.base import MarketDataProvider
from ..portfolio import Portfolio
from ..utils.logger import get_logger


class MarketAnalyzer:
    """Analyzes market data and prepares it for LLM consumption."""
    
    def __init__(self, data_provider: MarketDataProvider) -> None:
        """Initialize market analyzer.
        
        Args:
            data_provider: Provider for market data
        """
        self.data_provider = data_provider
        self.logger = get_logger(self.__class__.__name__)
        
        if not TALIB_AVAILABLE:
            self.logger.warning("TA-Lib not available. Technical indicators will be limited.")
    
    def analyze_market(
        self,
        symbol: str,
        portfolio: Portfolio,
        lookback_days: int = 30,
        interval: str = "1d"
    ) -> Optional[Dict[str, Any]]:
        """Analyze market for a given symbol.
        
        Args:
            symbol: Trading symbol
            portfolio: Current portfolio state
            lookback_days: Number of days of historical data to analyze
            interval: Data interval
            
        Returns:
            Dictionary with market analysis or None if failed
        """
        try:
            # Get historical data
            candles = self.data_provider.get_history(
                symbol=symbol,
                interval=interval,
                lookback=lookback_days
            )
            
            if candles.empty:
                self.logger.warning(f"No historical data available for {symbol}")
                return None
            
            # Prepare market analysis
            analysis = {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "price_data": self._analyze_price_data(candles),
                "technical_indicators": self._calculate_technical_indicators(candles),
                "portfolio_context": self._get_portfolio_context(symbol, portfolio),
                "market_conditions": self._assess_market_conditions(candles),
            }
            
            # Add sentiment analysis if available
            sentiment = self._get_sentiment_analysis(symbol)
            if sentiment:
                analysis["sentiment"] = sentiment
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing market for {symbol}: {e}")
            return None
    
    def _analyze_price_data(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """Analyze basic price data.
        
        Args:
            candles: Historical price data
            
        Returns:
            Dictionary with price analysis
        """
        current_price = candles["close"].iloc[-1].item()
        previous_close = candles["close"].iloc[-2].item() if len(candles) > 1 else current_price
        daily_change_pct = ((current_price - previous_close) / previous_close) * 100
        
        # Recent price movements
        recent_prices = [float(x) for x in candles["close"].tail(10).values]
        
        # Price statistics
        price_stats = {
            "current_price": current_price,
            "previous_close": previous_close,
            "daily_change": current_price - previous_close,
            "daily_change_pct": round(daily_change_pct, 2),
            "volume": int(candles["volume"].iloc[-1].item()) if "volume" in candles.columns else 0,
            "recent_prices": recent_prices,
            "high_20d": float(candles["high"].tail(20).max().item()),
            "low_20d": float(candles["low"].tail(20).min().item()),
            "avg_volume_20d": int(candles["volume"].tail(20).mean().item()) if "volume" in candles.columns else 0,
        }
        
        # Price relative to moving averages
        if len(candles) >= 20:
            price_stats["sma_20"] = float(candles["close"].tail(20).mean().item())
            price_stats["price_vs_sma_20_pct"] = ((current_price - price_stats["sma_20"]) / price_stats["sma_20"]) * 100
        
        if len(candles) >= 50:
            price_stats["sma_50"] = float(candles["close"].tail(50).mean().item())
            price_stats["price_vs_sma_50_pct"] = ((current_price - price_stats["sma_50"]) / price_stats["sma_50"]) * 100
        
        return price_stats
    
    def _calculate_technical_indicators(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """Calculate technical indicators.
        
        Args:
            candles: Historical price data
            
        Returns:
            Dictionary with technical indicators
        """
        indicators = {}
        close_prices = candles["close"].values.flatten()
        high_prices = candles["high"].values.flatten() if "high" in candles.columns else close_prices
        low_prices = candles["low"].values.flatten() if "low" in candles.columns else close_prices
        volumes = candles["volume"].values.flatten() if "volume" in candles.columns else None
        
        try:
            if TALIB_AVAILABLE:
                # Moving averages
                if len(close_prices) >= 20:
                    indicators["sma_20"] = float(talib.SMA(close_prices, timeperiod=20)[-1])
                if len(close_prices) >= 50:
                    indicators["sma_50"] = float(talib.SMA(close_prices, timeperiod=50)[-1])
                if len(close_prices) >= 200:
                    indicators["sma_200"] = float(talib.SMA(close_prices, timeperiod=200)[-1])
                
                # Exponential moving averages
                if len(close_prices) >= 12:
                    indicators["ema_12"] = float(talib.EMA(close_prices, timeperiod=12)[-1])
                if len(close_prices) >= 26:
                    indicators["ema_26"] = float(talib.EMA(close_prices, timeperiod=26)[-1])
                
                # RSI
                if len(close_prices) >= 14:
                    rsi_values = talib.RSI(close_prices, timeperiod=14)
                    indicators["rsi"] = float(rsi_values[-1])
                
                # MACD
                if len(close_prices) >= 26:
                    macd, macd_signal, macd_hist = talib.MACD(close_prices)
                    indicators["macd"] = float(macd[-1]) if not np.isnan(macd[-1]) else None
                    indicators["macd_signal"] = float(macd_signal[-1]) if not np.isnan(macd_signal[-1]) else None
                    indicators["macd_histogram"] = float(macd_hist[-1]) if not np.isnan(macd_hist[-1]) else None
                
                # Bollinger Bands
                if len(close_prices) >= 20:
                    bb_upper, bb_middle, bb_lower = talib.BBANDS(close_prices, timeperiod=20)
                    indicators["bb_upper"] = float(bb_upper[-1])
                    indicators["bb_middle"] = float(bb_middle[-1])
                    indicators["bb_lower"] = float(bb_lower[-1])
                    indicators["bb_width"] = (bb_upper[-1] - bb_lower[-1]) / bb_middle[-1]
                
                # Stochastic
                if len(close_prices) >= 14:
                    slowk, slowd = talib.STOCH(high_prices, low_prices, close_prices)
                    indicators["stoch_k"] = float(slowk[-1]) if not np.isnan(slowk[-1]) else None
                    indicators["stoch_d"] = float(slowd[-1]) if not np.isnan(slowd[-1]) else None
                
                # ADX (trend strength)
                if len(close_prices) >= 14:
                    adx = talib.ADX(high_prices, low_prices, close_prices, timeperiod=14)
                    indicators["adx"] = float(adx[-1]) if not np.isnan(adx[-1]) else None
                
                # Volume indicators
                if volumes is not None and len(volumes) >= 20:
                    indicators["volume_sma_20"] = float(talib.SMA(volumes, timeperiod=20)[-1])
                    current_volume = volumes[-1]
                    indicators["volume_ratio"] = current_volume / indicators["volume_sma_20"]
            
            else:
                # Basic calculations without TA-Lib
                if len(close_prices) >= 20:
                    indicators["sma_20"] = float(np.mean(close_prices[-20:]))
                if len(close_prices) >= 50:
                    indicators["sma_50"] = float(np.mean(close_prices[-50:]))
                
                # Simple RSI calculation
                if len(close_prices) >= 15:
                    deltas = np.diff(close_prices[-15:])
                    gains = np.where(deltas > 0, deltas, 0)
                    losses = np.where(deltas < 0, -deltas, 0)
                    avg_gain = np.mean(gains)
                    avg_loss = np.mean(losses)
                    if avg_loss > 0:
                        rs = avg_gain / avg_loss
                        indicators["rsi"] = float(100 - (100 / (1 + rs)))
            
            # Volatility (20-day standard deviation of returns)
            if len(close_prices) >= 20:
                returns = np.diff(close_prices[-20:]) / close_prices[-20:-1]
                indicators["volatility_20d"] = float(np.std(returns) * np.sqrt(252))  # Annualized
            
        except Exception as e:
            self.logger.warning(f"Error calculating technical indicators: {e}")
        
        # Remove None values
        return {k: v for k, v in indicators.items() if v is not None}
    
    def _get_portfolio_context(self, symbol: str, portfolio: Portfolio) -> Dict[str, Any]:
        """Get portfolio context for the symbol.
        
        Args:
            symbol: Trading symbol
            portfolio: Current portfolio
            
        Returns:
            Dictionary with portfolio context
        """
        position_size = portfolio.position_size(symbol)
        
        # Get current price for value calculations
        try:
            current_data = self.data_provider.get_history(symbol=symbol, interval="1d", lookback=1)
            if not current_data.empty:
                current_price = current_data["close"].iloc[-1].item()
            else:
                current_price = 0.0
        except:
            current_price = 0.0
        
        position_value = position_size * current_price
        
        return {
            "position_size": position_size,
            "position_value": position_value,
            "cash": portfolio.cash,
            "total_equity": portfolio.total_equity({symbol: current_price}),
            "position_pct": (position_value / portfolio.total_equity({symbol: current_price}) * 100) if portfolio.total_equity({symbol: current_price}) > 0 else 0,
        }
    
    def _assess_market_conditions(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """Assess overall market conditions.
        
        Args:
            candles: Historical price data
            
        Returns:
            Dictionary with market conditions
        """
        conditions = {}
        
        try:
            close_prices = candles["close"].values
            
            # Trend analysis
            if len(close_prices) >= 20:
                recent_trend = (float(close_prices[-1]) - float(close_prices[-20])) / float(close_prices[-20])
                conditions["trend_20d"] = "UP" if recent_trend > 0.05 else "DOWN" if recent_trend < -0.05 else "SIDEWAYS"
                conditions["trend_20d_pct"] = float(recent_trend * 100)
            
            if len(close_prices) >= 5:
                short_trend = (float(close_prices[-1]) - float(close_prices[-5])) / float(close_prices[-5])
                conditions["trend_5d"] = "UP" if short_trend > 0.02 else "DOWN" if short_trend < -0.02 else "SIDEWAYS"
                conditions["trend_5d_pct"] = float(short_trend * 100)
            
            # Volatility assessment
            if len(close_prices) >= 20:
                recent_prices = close_prices[-20:].flatten()
                returns = np.diff(recent_prices) / recent_prices[:-1]
                volatility = np.std(returns)
                conditions["volatility_level"] = "HIGH" if volatility > 0.03 else "LOW" if volatility < 0.01 else "MEDIUM"
                conditions["daily_volatility"] = float(volatility)
            
            # Price level relative to recent range
            if len(close_prices) >= 20:
                recent_prices = close_prices[-20:].flatten()
                recent_high = np.max(recent_prices)
                recent_low = np.min(recent_prices)
                current_price = float(recent_prices[-1])
                price_position = (current_price - recent_low) / (recent_high - recent_low)
                conditions["price_position"] = float(price_position)  # 0 = at low, 1 = at high
                conditions["price_level"] = "HIGH" if price_position > 0.8 else "LOW" if price_position < 0.2 else "MEDIUM"
            
        except Exception as e:
            self.logger.warning(f"Error assessing market conditions: {e}")
        
        return conditions
    
    def _get_sentiment_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get sentiment analysis for the symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with sentiment analysis or None if not available
        """
        # This is a placeholder for sentiment analysis
        # In a real implementation, you would integrate with news APIs, social media APIs, etc.
        
        # For now, return a neutral sentiment
        return {
            "overall": "NEUTRAL",
            "news_score": 0.0,
            "social_score": 0.0,
            "analyst_rating": "HOLD",
            "last_updated": datetime.now().isoformat(),
        }