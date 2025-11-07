# LLM-Based Trading Agent

This document describes the LLM-based trading agent functionality added to the auto-trading bot.

## Overview

The LLM trading agent uses Large Language Models (like GPT-4) to analyze market data and make trading decisions. It combines technical analysis, market sentiment, and portfolio context to generate intelligent trading signals.

## Features

- **Market Analysis**: Automatically collects and analyzes price data, technical indicators, and market conditions
- **LLM Decision Making**: Uses OpenAI's GPT models to make trading decisions based on comprehensive market analysis
- **Risk Management**: Built-in risk filters and confidence thresholds to protect capital
- **Scheduled Trading**: Automated trading at specified intervals during market hours
- **Real-time Monitoring**: Track LLM decisions and trading performance

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The additional dependencies for LLM functionality include:
- `openai>=1.0.0` - OpenAI API client
- `schedule>=1.2.0` - Task scheduling
- `ta-lib>=0.4.26` - Technical analysis library
- `requests>=2.31.0` - HTTP requests

### 2. Configure API Key

Set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or include it in your configuration file.

### 3. Configuration

Create a configuration file (e.g., `config_llm.toml`) based on `config_llm_example.toml`:

```toml
# Basic configuration
symbol = "AAPL"
cash = 10000.0

# LLM Configuration
llm_enabled = true
llm_api_key = "your-openai-api-key-here"
llm_model = "gpt-4"
llm_min_confidence = 0.6

# Scheduling
llm_schedule_interval_minutes = 60
llm_market_hours_only = true
```

## Usage

### Command Line Interface

#### Enable LLM Trading

```bash
# Run single LLM analysis
python cli.py --enable-llm --llm-api-key "your-key" analyze

# Start scheduled LLM trading
python cli.py --enable-llm --llm-api-key "your-key" scheduled

# Run one LLM trading iteration
python cli.py --enable-llm --llm-api-key "your-key" run-once

# Check LLM status
python cli.py --enable-llm --llm-api-key "your-key" status
```

#### Using Configuration File

```bash
# Use config file with LLM settings
python cli.py --config config_llm.toml scheduled

# Run analysis with config
python cli.py --config config_llm.toml analyze
```

### LLM Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `llm_enabled` | Enable LLM-based trading | `false` |
| `llm_api_key` | OpenAI API key | `""` |
| `llm_model` | OpenAI model to use | `"gpt-4"` |
| `llm_base_url` | Custom API endpoint | `None` |
| `llm_temperature` | Sampling temperature | `0.1` |
| `llm_max_tokens` | Maximum response tokens | `1000` |
| `llm_min_confidence` | Minimum confidence to act | `0.6` |
| `llm_enable_risk_filter` | Enable risk filtering | `true` |
| `llm_min_decision_interval_minutes` | Min time between decisions | `30` |
| `llm_schedule_interval_minutes` | Trading interval | `60` |
| `llm_market_hours_only` | Trade only during market hours | `true` |

## How It Works

### 1. Market Data Collection

The system collects:
- Recent price data and volume
- Technical indicators (RSI, MACD, Bollinger Bands, etc.)
- Market conditions and volatility
- Portfolio context (current positions, cash, etc.)

### 2. LLM Analysis

The market data is formatted and sent to the LLM with a detailed prompt that includes:
- Current price and recent performance
- Technical indicator analysis
- Market condition assessment
- Portfolio context
- Risk management guidelines

### 3. Decision Making

The LLM responds with a structured JSON decision:
```json
{
    "action": "BUY|SELL|HOLD",
    "confidence": 0.0-1.0,
    "rationale": "Explanation of the decision",
    "risk_level": "LOW|MEDIUM|HIGH",
    "price_target": optional_target_price,
    "stop_loss": optional_stop_loss_price
}
```

### 4. Risk Filtering

Before executing trades, the system applies risk filters:
- Confidence threshold validation
- Position size limits
- Volatility checks
- Technical indicator sanity checks
- RSI overbought/oversold conditions

### 5. Trade Execution

If the decision passes all filters, the trade is executed through the standard trading engine with proper position sizing and risk management.

## Risk Management

### Built-in Protections

1. **Confidence Threshold**: Only execute trades above minimum confidence
2. **Decision Intervals**: Prevent rapid-fire trading decisions
3. **Position Limits**: Respect maximum position size limits
4. **Volatility Filtering**: Extra caution in high-volatility markets
5. **Technical Sanity Checks**: Block trades that contradict technical indicators

### Recommended Settings

- **Conservative**: `llm_min_confidence = 0.8`, `llm_min_decision_interval_minutes = 60`
- **Balanced**: `llm_min_confidence = 0.6`, `llm_min_decision_interval_minutes = 30`
- **Aggressive**: `llm_min_confidence = 0.4`, `llm_min_decision_interval_minutes = 15`

## Monitoring and Debugging

### Status Command

```bash
python cli.py --config config_llm.toml status
```

This shows:
- LLM configuration status
- Scheduler status
- Last decision information
- Next scheduled run time

### Analysis Command

```bash
python cli.py --config config_llm.toml analyze
```

This provides:
- Full market analysis
- LLM decision rationale
- Technical indicators
- Market conditions

### Logging

Enable verbose logging for detailed information:

```bash
python cli.py --config config_llm.toml --verbose scheduled
```

## Best Practices

1. **Start Small**: Begin with paper trading and small position sizes
2. **Monitor Closely**: Watch the first few decisions to ensure they make sense
3. **Adjust Confidence**: If too many trades are executed, increase the confidence threshold
4. **Market Hours**: Use `llm_market_hours_only = true` to avoid after-hours trading
5. **Regular Reviews**: Periodically review the LLM's decisions and performance

## Limitations

- **API Costs**: Each analysis consumes OpenAI API tokens
- **Latency**: LLM responses may take several seconds
- **Market Dependency**: Performance depends on market conditions and data quality
- **No Guarantees**: LLM decisions are not guaranteed to be profitable

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure your OpenAI API key is valid and has sufficient credits
2. **No Trades Executed**: Check confidence threshold and risk filter settings
3. **Scheduler Not Running**: Verify market hours configuration and timezone settings
4. **Technical Analysis Errors**: Ensure TA-Lib is properly installed

### Debug Mode

Run with verbose logging to see detailed information:

```bash
python cli.py --config config_llm.toml --verbose analyze
```

This will show:
- Market data collection
- Technical indicator calculations
- LLM prompts and responses
- Risk filter decisions

## Example Output

### Analysis Command

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "symbol": "AAPL",
  "price_data": {
    "current_price": 195.50,
    "daily_change_pct": 1.2,
    "volume": 50000000
  },
  "technical_indicators": {
    "rsi": 55.3,
    "macd": 0.82,
    "bb_upper": 198.2,
    "bb_lower": 192.8
  },
  "llm_decision": {
    "action": "BUY",
    "confidence": 0.75,
    "rationale": "Strong technical indicators with RSI in optimal range and positive momentum",
    "risk_level": "MEDIUM"
  }
}
```

### Status Command

```json
{
  "llm_enabled": true,
  "llm_model": "gpt-4",
  "scheduler_running": true,
  "next_run_time": "2024-01-15T11:00:00",
  "last_decision": {
    "last_decision": "BUY",
    "last_decision_time": "2024-01-15T10:30:00",
    "min_confidence": 0.6
  }
}
```

## Contributing

To extend the LLM trading agent:

1. **Add Custom Indicators**: Extend `MarketAnalyzer` with additional technical indicators
2. **New LLM Providers**: Modify `LLMClient` to support other LLM providers
3. **Enhanced Risk Filters**: Add more sophisticated risk management rules
4. **Sentiment Analysis**: Integrate real news and social media sentiment data

## License

This LLM trading agent is part of the auto-trading bot project and follows the same license terms.