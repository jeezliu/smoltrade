"""Command line interface for the automated trading bot."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import json

from autotrader.config import BotConfig
from autotrader.data.yfinance import YFinanceDataProvider
from autotrader.engine import AutoTradingBot
from autotrader.execution.paper import PaperBroker
from autotrader.strategies.moving_average import MovingAverageCrossStrategy
from autotrader.llm_engine import LLMAutoTradingBot
from autotrader.utils.logger import setup_logging


def parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - argument validation
        raise argparse.ArgumentTypeError(f"Invalid datetime format: {value}. Use ISO format, e.g. 2024-01-01") from exc


def build_bot(config: BotConfig) -> AutoTradingBot:
    data_provider = YFinanceDataProvider()
    broker = PaperBroker(
        starting_cash=config.cash,
        slippage_bps=config.slippage_bps,
        commission=config.commission,
    )
    
    # Use LLM engine if enabled
    if config.llm_enabled:
        return LLMAutoTradingBot(
            config=config,
            data_provider=data_provider,
            execution_client=broker,
        )
    else:
        strategy = MovingAverageCrossStrategy(
            symbol=config.symbol,
            short_window=config.short_window,
            long_window=config.long_window,
            minimum_confidence=float(config.metadata.get("minimum_confidence", 0.005)),
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
    
    # LLM-specific arguments
    parser.add_argument("--llm-api-key", type=str, help="OpenAI API key for LLM trading")
    parser.add_argument("--llm-model", type=str, help="LLM model to use (default: gpt-4)")
    parser.add_argument("--llm-base-url", type=str, help="Custom base URL for LLM API")
    parser.add_argument("--enable-llm", action="store_true", help="Enable LLM-based trading")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run-once", help="Execute a single trading iteration")
    subparsers.add_parser("live", help="Start the continuous live trading loop")
    subparsers.add_parser("scheduled", help="Start LLM-based scheduled trading")

    backtest_parser = subparsers.add_parser("backtest", help="Run a backtest over a fixed period")
    backtest_parser.add_argument("--start", required=True, type=parse_datetime, help="Start datetime (ISO format)")
    backtest_parser.add_argument("--end", required=True, type=parse_datetime, help="End datetime (ISO format)")
    
    # LLM-specific commands
    analysis_parser = subparsers.add_parser("analyze", help="Run LLM market analysis without trading")
    status_parser = subparsers.add_parser("status", help="Get LLM trading status")

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
    
    # Apply LLM overrides
    if args.enable_llm:
        overrides["llm_enabled"] = True
    if args.llm_api_key:
        overrides["llm_api_key"] = args.llm_api_key
    if args.llm_model:
        overrides["llm_model"] = args.llm_model
    if args.llm_base_url:
        overrides["llm_base_url"] = args.llm_base_url
    
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
    elif args.command == "scheduled":  # pragma: no cover - runtime loop
        if isinstance(bot, LLMAutoTradingBot):
            bot.run_scheduled()
        else:
            print("Error: Scheduled trading requires LLM to be enabled. Use --enable-llm flag.")
    elif args.command == "analyze":
        if isinstance(bot, LLMAutoTradingBot):
            analysis = bot.run_llm_analysis()
            if analysis:
                print("LLM Market Analysis:")
                print(json.dumps(analysis, indent=2, default=str))
            else:
                print("Failed to generate LLM analysis.")
        else:
            print("Error: Analysis requires LLM to be enabled. Use --enable-llm flag.")
    elif args.command == "status":
        if isinstance(bot, LLMAutoTradingBot):
            status = bot.get_llm_status()
            print("LLM Trading Status:")
            print(json.dumps(status, indent=2, default=str))
        else:
            print("LLM is not enabled. Use --enable-llm flag to enable LLM trading.")
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
