"""LLM client for trading decisions."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, List
import logging

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from ..utils.logger import get_logger


class LLMClient:
    """Client for interacting with LLM APIs for trading decisions."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        base_url: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> None:
        """Initialize LLM client.
        
        Args:
            api_key: API key for the LLM service
            model: Model name to use
            base_url: Custom base URL for API (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package is required. Install with: pip install openai")
            
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = get_logger(self.__class__.__name__)
        
        # Initialize OpenAI client
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
            
        self.client = OpenAI(**client_kwargs)
        
        # System prompt for trading decisions
        self.system_prompt = """You are an AI trading assistant with expertise in technical analysis, 
fundamental analysis, and market sentiment analysis. Your task is to analyze the provided market data 
and make trading recommendations.

Based on the market data provided, you should:
1. Analyze technical indicators (moving averages, RSI, MACD, etc.)
2. Consider price trends and volatility
3. Assess market sentiment from news and social media if available
4. Evaluate risk factors
5. Provide a clear trading recommendation: BUY, SELL, or HOLD
6. Include a confidence score (0.0 to 1.0)
7. Provide a brief rationale for your decision

Respond in JSON format with the following structure:
{
    "action": "BUY|SELL|HOLD",
    "confidence": 0.0-1.0,
    "rationale": "Brief explanation of the decision",
    "risk_level": "LOW|MEDIUM|HIGH",
    "price_target": optional_target_price,
    "stop_loss": optional_stop_loss_price
}

Be conservative and prioritize capital preservation. Only recommend BUY when there are strong 
technical and fundamental indicators supporting the decision. Only recommend SELL when there 
are clear signs of deterioration or to take profits."""

    def get_trading_decision(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get trading decision from LLM based on market data.
        
        Args:
            market_data: Dictionary containing market information
            
        Returns:
            Dictionary with trading decision or None if failed
        """
        try:
            # Prepare user prompt with market data
            user_prompt = self._format_market_data(market_data)
            
            self.logger.debug("Sending market data to LLM for analysis")
            
            # Make API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            content = response.choices[0].message.content.strip()
            self.logger.debug(f"LLM response: {content}")
            
            # Parse JSON response
            try:
                decision = json.loads(content)
                # Validate required fields
                required_fields = ["action", "confidence", "rationale"]
                missing_fields = [field for field in required_fields if field not in decision]
                if missing_fields:
                    self.logger.warning(f"LLM response missing required fields: {missing_fields}")
                    return None
                    
                # Validate action
                if decision["action"].upper() not in ["BUY", "SELL", "HOLD"]:
                    self.logger.warning(f"Invalid action in LLM response: {decision['action']}")
                    return None
                    
                # Validate confidence
                confidence = float(decision["confidence"])
                if not 0.0 <= confidence <= 1.0:
                    self.logger.warning(f"Invalid confidence in LLM response: {confidence}")
                    return None
                    
                decision["action"] = decision["action"].upper()
                decision["confidence"] = confidence
                
                self.logger.info(
                    f"LLM decision: {decision['action']} (confidence: {confidence:.2f})"
                )
                return decision
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM response as JSON: {e}")
                self.logger.error(f"Raw response: {content}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting LLM trading decision: {e}")
            return None
    
    def _format_market_data(self, market_data: Dict[str, Any]) -> str:
        """Format market data for LLM consumption.
        
        Args:
            market_data: Raw market data dictionary
            
        Returns:
            Formatted string for LLM prompt
        """
        prompt_parts = ["MARKET DATA ANALYSIS REQUEST\n"]
        prompt_parts.append("=" * 50)
        
        # Basic price information
        if "price_data" in market_data:
            price_data = market_data["price_data"]
            prompt_parts.append("\nPRICE DATA:")
            prompt_parts.append(f"Symbol: {price_data.get('symbol', 'N/A')}")
            prompt_parts.append(f"Current Price: ${price_data.get('current_price', 'N/A')}")
            prompt_parts.append(f"Daily Change: {price_data.get('daily_change_pct', 'N/A')}%")
            prompt_parts.append(f"Volume: {price_data.get('volume', 'N/A')}")
            
            if "recent_prices" in price_data:
                recent = price_data["recent_prices"]
                prompt_parts.append(f"Recent Prices (last {len(recent)} periods):")
                for i, price in enumerate(recent[-5:]):  # Show last 5 prices
                    prompt_parts.append(f"  Period {i+1}: ${price:.2f}")
        
        # Technical indicators
        if "technical_indicators" in market_data:
            prompt_parts.append("\nTECHNICAL INDICATORS:")
            indicators = market_data["technical_indicators"]
            for indicator, value in indicators.items():
                if isinstance(value, (int, float)):
                    prompt_parts.append(f"{indicator}: {value:.4f}")
                else:
                    prompt_parts.append(f"{indicator}: {value}")
        
        # Market sentiment
        if "sentiment" in market_data:
            prompt_parts.append("\nMARKET SENTIMENT:")
            sentiment = market_data["sentiment"]
            prompt_parts.append(f"Overall Sentiment: {sentiment.get('overall', 'N/A')}")
            prompt_parts.append(f"News Score: {sentiment.get('news_score', 'N/A')}")
            prompt_parts.append(f"Social Media Score: {sentiment.get('social_score', 'N/A')}")
        
        # Portfolio context
        if "portfolio_context" in market_data:
            prompt_parts.append("\nPORTFOLIO CONTEXT:")
            portfolio = market_data["portfolio_context"]
            prompt_parts.append(f"Current Position: {portfolio.get('position_size', 0)} shares")
            prompt_parts.append(f"Position Value: ${portfolio.get('position_value', 0):.2f}")
            prompt_parts.append(f"Available Cash: ${portfolio.get('cash', 0):.2f}")
            prompt_parts.append(f"Total Equity: ${portfolio.get('total_equity', 0):.2f}")
        
        # Market conditions
        if "market_conditions" in market_data:
            prompt_parts.append("\nMARKET CONDITIONS:")
            conditions = market_data["market_conditions"]
            for condition, value in conditions.items():
                prompt_parts.append(f"{condition}: {value}")
        
        prompt_parts.append("\n" + "=" * 50)
        prompt_parts.append("Please analyze this data and provide your trading recommendation.")
        
        return "\n".join(prompt_parts)