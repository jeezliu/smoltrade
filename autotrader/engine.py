"""Core orchestration engine for the automated trading bot."""

from __future__ import annotations

import math
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .config import BotConfig
from .data.base import MarketDataProvider
from .execution.base import ExecutionClient, Order, Trade
from .portfolio import Portfolio
from .strategies.base import BaseStrategy, Signal
from .utils.logger import get_logger


class AutoTradingBot:
    """Coordinate data retrieval, signal generation and order execution."""

    def __init__(
        self,
        config: BotConfig,
        data_provider: MarketDataProvider,
        strategy: BaseStrategy,
        execution_client: ExecutionClient,
    ) -> None:
        self.config = config
        self.data_provider = data_provider
        self.strategy = strategy
        self.execution_client = execution_client

        portfolio = getattr(execution_client, "portfolio", None)
        if not isinstance(portfolio, Portfolio):
            raise TypeError("Execution client must expose a Portfolio instance via 'portfolio'")
        self.portfolio: Portfolio = portfolio

        self.logger = get_logger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_once(self) -> Optional[Trade]:
        """Execute a single trading iteration."""

        candles = self._fetch_recent_data()
        if candles is None:
            return None

        signal = self._generate_signal(candles)
        if signal is None:
            return None

        price = float(candles["close"].iloc[-1])
        order = self._create_order(signal, price)
        if order is None:
            self.logger.debug("No order generated after applying risk limits")
            return None

        trade = self.execution_client.submit_order(order, market_price=price, timestamp=signal.timestamp)
        self.logger.info(
            "Executed %s %s x %.0f at %.2f", order.side.upper(), order.symbol, order.quantity, trade.price
        )
        return trade

    def run_forever(self) -> None:
        """Run the trading loop continuously until interrupted."""

        self.logger.info("Starting live trading loop for %s", self.config.symbol)
        try:
            while True:
                try:
                    self.run_once()
                except Exception as exc:  # pragma: no cover - defensive logging
                    self.logger.exception("Trading iteration failed: %s", exc)
                time.sleep(self.config.poll_interval_seconds)
        except KeyboardInterrupt:  # pragma: no cover - manual stop
            self.logger.info("Live trading loop stopped by user")

    def backtest(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Run a backtest for the configured strategy between the provided dates."""

        self.logger.info(
            "Running backtest for %s between %s and %s", self.config.symbol, start.isoformat(), end.isoformat()
        )

        self._reset_state()
        candles = self.data_provider.get_history(
            symbol=self.config.symbol,
            interval=self.config.data_interval,
            start=start,
            end=end,
        )
        if candles.empty:
            raise ValueError("No historical data retrieved for the specified period")

        equity_curve: List[Tuple[datetime, float]] = []
        for idx in range(self.strategy.minimum_history, len(candles) + 1):
            window = candles.iloc[:idx]
            signal = self._generate_signal(window)
            price = float(window["close"].iloc[-1])
            price_map = {self.config.symbol: price}

            if signal:
                order = self._create_order(signal, price)
                if order:
                    self.execution_client.submit_order(order, market_price=price, timestamp=signal.timestamp)

            equity_curve.append((window.index[-1].to_pydatetime(), self.portfolio.total_equity(price_map)))

        closing_price = float(candles["close"].iloc[-1])
        ending_equity = self.portfolio.total_equity({self.config.symbol: closing_price})
        starting_equity = self.config.cash
        total_return = (ending_equity / starting_equity) - 1
        max_drawdown = self._calculate_max_drawdown(equity_curve)

        trade_history = list(getattr(self.execution_client, "trade_history", []))
        results = {
            "trades": trade_history,
            "ending_equity": ending_equity,
            "total_return": total_return,
            "max_drawdown": max_drawdown,
            "equity_curve": equity_curve,
        }

        self.logger.info(
            "Backtest complete. Ending equity: %.2f (%.2f%%)", ending_equity, total_return * 100
        )
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_recent_data(self) -> Optional[pd.DataFrame]:
        candles = self.data_provider.get_history(
            symbol=self.config.symbol,
            interval=self.config.data_interval,
            lookback=self.config.lookback_days,
        )
        if candles.empty:
            self.logger.warning("No data returned for symbol %s", self.config.symbol)
            return None
        return candles

    def _generate_signal(self, candles: pd.DataFrame) -> Optional[Signal]:
        candles = candles.copy()
        signal = self.strategy.generate_signal(candles, self.portfolio)
        if signal:
            self.logger.debug(
                "Strategy produced signal: %s (confidence=%.2f)", signal.action.upper(), signal.confidence
            )
        return signal

    def _create_order(self, signal: Signal, market_price: float) -> Optional[Order]:
        action = signal.action.lower()
        symbol = signal.symbol

        if action not in {"buy", "sell"}:
            return None

        if action == "buy":
            current_qty = self.portfolio.position_size(symbol)
            equity = self.portfolio.total_equity({symbol: market_price})
            max_position_value = equity * self.config.max_position_pct
            current_value = current_qty * market_price
            remaining_value = max(0.0, max_position_value - current_value)

            budget = min(self.portfolio.cash * self.config.risk_per_trade, remaining_value)
            if budget <= 0:
                return None

            quantity = math.floor(budget / market_price)
            if quantity <= 0:
                return None

            return Order(symbol=symbol, quantity=quantity, side="buy")

        # SELL flow
        current_qty = self.portfolio.position_size(symbol)
        if current_qty <= 0:
            return None

        return Order(symbol=symbol, quantity=current_qty, side="sell")

    def _reset_state(self) -> None:
        portfolio_reset = getattr(self.execution_client, "reset", None)
        if callable(portfolio_reset):
            portfolio_reset(self.config.cash)
        else:  # pragma: no cover - defensive path
            raise RuntimeError("Execution client cannot be reset for backtesting")

    @staticmethod
    def _calculate_max_drawdown(equity_curve: List[Tuple[datetime, float]]) -> float:
        if not equity_curve:
            return 0.0

        peak = equity_curve[0][1]
        max_drawdown = 0.0
        for _, equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (equity / peak) - 1
            if drawdown < max_drawdown:
                max_drawdown = drawdown
        return max_drawdown
