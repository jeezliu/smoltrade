"""LLM-based trading strategy."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd

from .base import BaseStrategy, Signal
from ..agents.llm_client import LLMClient
from ..agents.market_analyzer import MarketAnalyzer
from ..data.base import MarketDataProvider
from ..portfolio import Portfolio
from ..utils.logger import get_logger


class LLMAgentStrategy(BaseStrategy):
    """Trading strategy that uses LLM for decision making."""
    
    def __init__(
        self,
        symbol: str,
        llm_client: LLMClient,
        market_analyzer: MarketAnalyzer,
        min_confidence: float = 0.6,
        enable_risk_filter: bool = True,
    ) -> None:
        """Initialize LLM agent strategy.
        
        Args:
            symbol: Trading symbol
            llm_client: LLM client for decision making
            market_analyzer: Market data analyzer
            min_confidence: Minimum confidence required to act on signals
            enable_risk_filter: Whether to apply additional risk filtering
        """
        super().__init__(symbol)
        self.llm_client = llm_client
        self.market_analyzer = market_analyzer
        self.min_confidence = min_confidence
        self.enable_risk_filter = enable_risk_filter
        self.logger = get_logger(self.__class__.__name__)
        
        # Track last decision to avoid rapid changes
        self.last_decision: Optional[str] = None
        self.last_decision_time: Optional[datetime] = None
        self.min_decision_interval_minutes = 30  # Minimum time between decisions
    
    @property
    def minimum_history(self) -> int:
        """Return minimum candles required for analysis."""
        return 30  # Need at least 30 days for technical analysis
    
    def generate_signal(
        self,
        data: pd.DataFrame,
        portfolio: Portfolio,
    ) -> Optional[Signal]:
        """Generate trading signal using LLM analysis.
        
        Args:
            data: Historical price data
            portfolio: Current portfolio state
            
        Returns:
            Trading signal or None if no decision
        """
        try:
            # Check minimum time interval between decisions
            now = datetime.now()
            if (self.last_decision_time and 
                (now - self.last_decision_time).total_seconds() < self.min_decision_interval_minutes * 60):
                self.logger.debug("Too soon since last decision, skipping")
                return None
            
            # Analyze market data
            market_analysis = self.market_analyzer.analyze_market(
                symbol=self.symbol,
                portfolio=portfolio,
                lookback_days=30
            )
            
            if not market_analysis:
                self.logger.warning("Failed to analyze market data")
                return None
            
            # Get LLM decision
            llm_decision = self.llm_client.get_trading_decision(market_analysis)
            
            if not llm_decision:
                self.logger.warning("LLM failed to provide decision")
                return None
            
            # Apply confidence filter
            if llm_decision["confidence"] < self.min_confidence:
                self.logger.info(
                    f"LLM confidence {llm_decision['confidence']:.2f} below threshold {self.min_confidence}"
                )
                return None
            
            # Apply risk filtering
            if self.enable_risk_filter and not self._risk_filter(llm_decision, market_analysis, portfolio):
                self.logger.info("Risk filter blocked the trading decision")
                return None
            
            # Create signal
            action = llm_decision["action"]
            if action == "HOLD":
                self.logger.info("LLM recommends HOLD")
                return None
            
            # Update last decision tracking
            self.last_decision = action
            self.last_decision_time = now
            
            # Log decision rationale
            self.logger.info(
                f"LLM Signal: {action} (confidence: {llm_decision['confidence']:.2f}, "
                f"risk: {llm_decision.get('risk_level', 'UNKNOWN')})"
            )
            self.logger.info(f"Rationale: {llm_decision['rationale']}")
            
            return Signal(
                symbol=self.symbol,
                action=action.lower(),
                timestamp=now,
                confidence=llm_decision["confidence"]
            )
            
        except Exception as e:
            self.logger.error(f"Error generating LLM signal: {e}")
            return None
    
    def _risk_filter(
        self,
        llm_decision: dict,
        market_analysis: dict,
        portfolio: Portfolio
    ) -> bool:
        """Apply additional risk filtering to LLM decisions.
        
        Args:
            llm_decision: Decision from LLM
            market_analysis: Market analysis data
            portfolio: Current portfolio
            
        Returns:
            True if decision passes risk filter, False otherwise
        """
        try:
            # Check if already at maximum position
            if llm_decision["action"] == "BUY":
                position_pct = market_analysis["portfolio_context"]["position_pct"]
                if position_pct > 80:  # Don't buy if position > 80% of portfolio
                    self.logger.info(f"Position size {position_pct:.1f}% too large for additional buying")
                    return False
                
                # Check if market is in high volatility
                market_conditions = market_analysis.get("market_conditions", {})
                volatility_level = market_conditions.get("volatility_level", "MEDIUM")
                if volatility_level == "HIGH":
                    # Be more cautious in high volatility
                    if llm_decision["confidence"] < 0.8:
                        self.logger.info("High volatility market requires higher confidence for buying")
                        return False
            
            # Check if trying to sell with no position
            if llm_decision["action"] == "SELL":
                position_size = market_analysis["portfolio_context"]["position_size"]
                if position_size <= 0:
                    self.logger.info("Cannot sell - no position held")
                    return False
            
            # Check risk level
            risk_level = llm_decision.get("risk_level", "MEDIUM")
            if risk_level == "HIGH":
                # Require higher confidence for high-risk trades
                if llm_decision["confidence"] < 0.8:
                    self.logger.info("High risk trade requires higher confidence")
                    return False
            
            # Technical indicators sanity check
            tech_indicators = market_analysis.get("technical_indicators", {})
            
            # RSI overbought/oversold check
            rsi = tech_indicators.get("rsi")
            if rsi:
                if llm_decision["action"] == "BUY" and rsi > 70:
                    self.logger.info(f"RSI {rsi:.1f} indicates overbought, blocking BUY signal")
                    return False
                elif llm_decision["action"] == "SELL" and rsi < 30:
                    self.logger.info(f"RSI {rsi:.1f} indicates oversold, blocking SELL signal")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in risk filter: {e}")
            # If risk filter fails, err on the side of caution
            return False
    
    def get_last_decision_info(self) -> dict:
        """Get information about the last decision.
        
        Returns:
            Dictionary with last decision information
        """
        return {
            "last_decision": self.last_decision,
            "last_decision_time": self.last_decision_time.isoformat() if self.last_decision_time else None,
            "min_confidence": self.min_confidence,
            "enable_risk_filter": self.enable_risk_filter,
        }
    
    def update_parameters(
        self,
        min_confidence: Optional[float] = None,
        enable_risk_filter: Optional[bool] = None,
        min_decision_interval_minutes: Optional[int] = None,
    ) -> None:
        """Update strategy parameters.
        
        Args:
            min_confidence: New minimum confidence threshold
            enable_risk_filter: New risk filter setting
            min_decision_interval_minutes: New minimum decision interval
        """
        if min_confidence is not None:
            self.min_confidence = min_confidence
            self.logger.info(f"Updated min_confidence to {min_confidence}")
        
        if enable_risk_filter is not None:
            self.enable_risk_filter = enable_risk_filter
            self.logger.info(f"Updated enable_risk_filter to {enable_risk_filter}")
        
        if min_decision_interval_minutes is not None:
            self.min_decision_interval_minutes = min_decision_interval_minutes
            self.logger.info(f"Updated min_decision_interval_minutes to {min_decision_interval_minutes}")