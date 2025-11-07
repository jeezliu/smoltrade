# Auto Trading Bot

An extensible automated trading bot built with Python. The bot follows a
modular design consisting of three main components:

1. **Market data providers** – fetch market data from external sources.
2. **Strategies** – produce trading signals based on the latest market data.
3. **Execution clients** – execute orders against a broker or, in the default
   setup, a built-in paper trading simulator.

The default configuration ships with a moving-average crossover strategy that
trades a single symbol using market orders. A slippage-aware paper broker keeps
track of portfolio performance so you can test out ideas before risking real
capital.

## Features

- Clean separation of data, strategy, and execution layers.
- Moving average crossover strategy with configurable windows.
- Risk management controls for maximum position size and risk per trade.
- Paper trading broker with configurable slippage and commission.
- Backtesting support with equity curve and max drawdown calculation.
- Command line interface for one-off runs, continuous trading, and backtesting.

## Getting Started

### Prerequisites

- Python 3.11+
- `pip` for installing dependencies

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running the Bot

Execute a single trading iteration using default settings:

```bash
python cli.py run-once
```

Start the live trading loop (press `Ctrl+C` to stop):

```bash
python cli.py live
```

Run a historical backtest (dates must be provided in ISO format):

```bash
python cli.py backtest --start 2023-01-01 --end 2023-12-31
```

### Configuration

Settings can be provided via a TOML or JSON file and passed to the CLI using the
`--config` option. Example `config.toml`:

```toml
symbol = "MSFT"
cash = 20000
short_window = 10
long_window = 40
lookback_days = 180
poll_interval_seconds = 600
risk_per_trade = 0.15
max_position_pct = 0.3
slippage_bps = 3.0
commission = 0.5

[metadata]
minimum_confidence = 0.01
```

Command line flags can override the most common settings without editing the
configuration file, for example `--symbol`, `--short-window`, `--long-window`,
and `--cash`.

## Project Structure

```
autotrader/
├── config.py             # Configuration dataclasses and helpers
├── data/                 # Data provider interfaces and implementations
├── engine.py             # Trading engine orchestrating the workflow
├── execution/            # Execution client abstractions and paper broker
├── portfolio.py          # Portfolio and position management utilities
├── strategies/           # Strategy base class and concrete strategies
└── utils/                # Shared utilities (logging, etc.)
cli.py                    # Command line entry point
```

## Extending the Bot

- **Custom strategies**: inherit from `BaseStrategy` and implement
  `generate_signal`.
- **New data providers**: implement the `MarketDataProvider` interface.
- **Real brokers**: create an `ExecutionClient` that integrates with your
  broker's API.

## Disclaimer

This project is provided for educational purposes only. It does **not** offer
financial advice. Always test strategies thoroughly before trading with real
money and consult a qualified financial professional where appropriate.
