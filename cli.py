"""Command line interface for the automated trading bot."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from autotrader.config import BotConfig
from autotrader.data.yfinance import YFinanceDataProvider
from autotrader.engine import AutoTradingBot
from autotrader.execution.paper import PaperBroker
from autotrader.strategies.moving_average import MovingAverageCrossStrategy
from autotrader.utils.logger import setup_logging


def parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - argument validation
        raise argparse.ArgumentTypeError(f"Invalid datetime format: {value}. Use ISO format, e.g. 2024-01-01") from exc


def build_bot(config: BotConfig) -> AutoTradingBot:
    data_provider = YFinanceDataProvider()
    strategy = MovingAverageCrossStrategy(
        symbol=config.symbol,
        short_window=config.short_window,
        long_window=config.long_window,
        minimum_confidence=float(config.metadata.get("minimum_confidence", 0.005)),
    )
    broker = PaperBroker(
        starting_cash=config.cash,
        slippage_bps=config.slippage_bps,
        commission=config.commission,
    )
    return AutoTradingBot(
        config=config,
        data_provider=data_provider,
        strategy=strategy,
        execution_client=broker,
    )


def apply_overrides(config: BotConfig, overrides: Dict[str, Any]) -> BotConfig:
    updates = {key: value for key, value in overrides.items() if value is not None}
    if not updates:
        return config
    return config.copy(**updates)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Automated trading bot controller")
    parser.add_argument("--config", type=Path, help="Path to TOML or JSON configuration file")
    parser.add_argument("--symbol", type=str, help="Override configured trading symbol")
    parser.add_argument("--short-window", type=int, help="Override the short moving average window")
    parser.add_argument("--long-window", type=int, help="Override the long moving average window")
    parser.add_argument("--cash", type=float, help="Override starting cash balance")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run-once", help="Execute a single trading iteration")
    subparsers.add_parser("live", help="Start the continuous live trading loop")

    backtest_parser = subparsers.add_parser("backtest", help="Run a backtest over a fixed period")
    backtest_parser.add_argument("--start", required=True, type=parse_datetime, help="Start datetime (ISO format)")
    backtest_parser.add_argument("--end", required=True, type=parse_datetime, help="End datetime (ISO format)")

    args = parser.parse_args(argv)

    setup_logging(logging.DEBUG if args.verbose else logging.INFO)

    if args.config:
        config = BotConfig.from_file(args.config)
    else:
        config = BotConfig()

    overrides = {
        "symbol": args.symbol,
        "short_window": args.short_window,
        "long_window": args.long_window,
        "cash": args.cash,
    }
    config = apply_overrides(config, overrides)

    bot = build_bot(config)

    if args.command == "run-once":
        trade = bot.run_once()
        if trade:
            print(
                f"Executed {trade.order.side.upper()} {trade.order.quantity} {trade.order.symbol} at {trade.price:.2f}"
            )
        else:
            print("No trade executed in this iteration.")
    elif args.command == "live":  # pragma: no cover - runtime loop
        bot.run_forever()
    elif args.command == "backtest":
        results = bot.backtest(start=args.start, end=args.end)
        ending_equity = results["ending_equity"]
        total_return = results["total_return"] * 100
        max_drawdown = results["max_drawdown"] * 100
        print("Backtest complete:\n")
        print(f"  Trades executed: {len(results['trades'])}")
        print(f"  Ending equity : ${ending_equity:,.2f}")
        print(f"  Total return  : {total_return:.2f}%")
        print(f"  Max drawdown  : {max_drawdown:.2f}%")
    else:  # pragma: no cover - defensive
        parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
