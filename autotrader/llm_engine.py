"""LLM-enhanced trading engine with scheduled market analysis."""

from __future__ import annotations

import signal
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from .config import BotConfig
from .data.base import MarketDataProvider
from .engine import AutoTradingBot
from .execution.base import ExecutionClient
from .agents.llm_client import LLMClient
from .agents.market_analyzer import MarketAnalyzer
from .agents.scheduler import TradingScheduler
from .strategies.llm_agent import LLMAgentStrategy
from .utils.logger import get_logger


class LLMAutoTradingBot(AutoTradingBot):
    """Enhanced trading bot with LLM-based decision making and scheduling."""
    
    def __init__(
        self,
        config: BotConfig,
        data_provider: MarketDataProvider,
        execution_client: ExecutionClient,
    ) -> None:
        """Initialize LLM trading bot.
        
        Args:
            config: Bot configuration
            data_provider: Market data provider
            execution_client: Order execution client
        """
        # Initialize parent class first to set self.config
        # We'll set strategy later
        super().__init__(config, data_provider, None, execution_client)
        
        # Initialize LLM components if enabled
        if config.llm_enabled:
            if not config.llm_api_key:
                raise ValueError("LLM API key is required when LLM is enabled")
            
            self.llm_client = LLMClient(
                api_key=config.llm_api_key,
                model=config.llm_model,
                base_url=config.llm_base_url,
                temperature=config.llm_temperature,
                max_tokens=config.llm_max_tokens,
            )
            
            self.market_analyzer = MarketAnalyzer(data_provider)
            
            self.strategy = LLMAgentStrategy(
                symbol=config.symbol,
                llm_client=self.llm_client,
                market_analyzer=self.market_analyzer,
                min_confidence=config.llm_min_confidence,
                enable_risk_filter=config.llm_enable_risk_filter,
            )
            
            # Set decision interval
            self.strategy.min_decision_interval_minutes = config.llm_min_decision_interval_minutes
            
            # Initialize scheduler
            self.scheduler = TradingScheduler()
            self._setup_scheduler()
            
        else:
            # Fall back to regular strategy initialization
            from .strategies.moving_average import MovingAverageStrategy
            self.strategy = MovingAverageStrategy(
                symbol=config.symbol,
                short_window=config.short_window,
                long_window=config.long_window,
            )
            self.scheduler = None
            self.llm_client = None
            self.market_analyzer = None
        
        # Update the strategy in parent class
        self.strategy = self.strategy
        
        self.logger.info(f"Initialized LLM trading bot (LLM enabled: {config.llm_enabled})")
    
    def _setup_scheduler(self) -> None:
        """Setup the trading scheduler."""
        if not self.scheduler or not self.config.llm_enabled:
            return
        
        # Define the trading function
        def execute_llm_trading():
            try:
                self.logger.info("Executing scheduled LLM trading analysis")
                trade = self.run_once()
                if trade:
                    self.logger.info(f"Scheduled trade executed: {trade}")
                else:
                    self.logger.debug("No trade generated in scheduled run")
            except Exception as e:
                self.logger.error(f"Error in scheduled trading: {e}")
        
        # Schedule the trading function
        self.scheduler.schedule_trading(
            trading_function=execute_llm_trading,
            interval_minutes=self.config.llm_schedule_interval_minutes,
            market_hours_only=self.config.llm_market_hours_only,
            timezone=self.config.timezone,
        )
    
    def run_scheduled(self) -> None:
        """Run the bot with scheduled LLM trading."""
        if not self.config.llm_enabled:
            self.logger.warning("LLM is not enabled. Use run_forever() for regular trading.")
            return
        
        if not self.scheduler:
            self.logger.error("Scheduler not initialized")
            return
        
        self.logger.info("Starting LLM trading bot with scheduled execution")
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.stop_scheduled()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start the scheduler
        self.scheduler.start()
        
        try:
            # Keep the main thread alive
            while self.scheduler.is_running():
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            self.stop_scheduled()
    
    def stop_scheduled(self) -> None:
        """Stop the scheduled trading."""
        if self.scheduler:
            self.scheduler.stop()
            self.logger.info("Scheduled trading stopped")
    
    def get_llm_status(self) -> Dict[str, Any]:
        """Get current LLM and scheduler status.
        
        Returns:
            Dictionary with LLM status information
        """
        if not self.config.llm_enabled:
            return {"llm_enabled": False}
        
        status = {
            "llm_enabled": True,
            "llm_model": self.config.llm_model,
            "scheduler_running": self.scheduler.is_running() if self.scheduler else False,
        }
        
        if self.scheduler:
            next_run = self.scheduler.get_next_run_time()
            status.update({
                "next_run_time": next_run.isoformat() if next_run else None,
                "scheduled_jobs": self.scheduler.list_scheduled_jobs(),
            })
        
        if hasattr(self.strategy, 'get_last_decision_info'):
            status["last_decision"] = self.strategy.get_last_decision_info()
        
        return status
    
    def run_llm_analysis(self) -> Optional[Dict[str, Any]]:
        """Run a single LLM market analysis without executing trades.
        
        Returns:
            Market analysis results or None if failed
        """
        if not self.config.llm_enabled or not self.market_analyzer:
            self.logger.warning("LLM analysis not available")
            return None
        
        try:
            analysis = self.market_analyzer.analyze_market(
                symbol=self.config.symbol,
                portfolio=self.portfolio,
                lookback_days=30
            )
            
            if analysis and self.llm_client:
                decision = self.llm_client.get_trading_decision(analysis)
                if decision:
                    analysis["llm_decision"] = decision
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error running LLM analysis: {e}")
            return None
    
    def update_llm_config(self, **kwargs) -> None:
        """Update LLM configuration parameters.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        if not self.config.llm_enabled:
            self.logger.warning("LLM is not enabled")
            return
        
        # Update config
        for key, value in kwargs.items():
            if hasattr(self.config, f"llm_{key}"):
                setattr(self.config, f"llm_{key}", value)
                self.logger.info(f"Updated llm_{key} to {value}")
        
        # Update strategy parameters if applicable
        if hasattr(self.strategy, 'update_parameters'):
            strategy_params = {}
            if 'min_confidence' in kwargs:
                strategy_params['min_confidence'] = kwargs['min_confidence']
            if 'enable_risk_filter' in kwargs:
                strategy_params['enable_risk_filter'] = kwargs['enable_risk_filter']
            if 'min_decision_interval_minutes' in kwargs:
                strategy_params['min_decision_interval_minutes'] = kwargs['min_decision_interval_minutes']
            
            if strategy_params:
                self.strategy.update_parameters(**strategy_params)
        
        # Restart scheduler if interval changed
        if 'schedule_interval_minutes' in kwargs and self.scheduler:
            self.scheduler.stop()
            self._setup_scheduler()
            self.scheduler.start()