"""Configuration helpers for the automated trading bot."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional
import json

try:  # tomllib is available from Python 3.11
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - fallback for <3.11 environments
    tomllib = None  # type: ignore


@dataclass(slots=True)
class BotConfig:
    """Dataclass holding all runtime configuration options."""

    symbol: str = "AAPL"
    cash: float = 10_000.0
    short_window: int = 20
    long_window: int = 50
    lookback_days: int = 120
    data_interval: str = "1d"
    poll_interval_seconds: int = 300
    risk_per_trade: float = 0.1
    max_position_pct: float = 0.25
    data_source: str = "yfinance"
    broker: str = "paper"
    timezone: str = "America/New_York"
    slippage_bps: float = 5.0
    commission: float = 0.0

    # LLM Agent Configuration
    llm_enabled: bool = False
    llm_api_key: str = ""
    llm_model: str = "gpt-4"
    llm_base_url: Optional[str] = None
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1000
    llm_min_confidence: float = 0.6
    llm_enable_risk_filter: bool = True
    llm_min_decision_interval_minutes: int = 30
    llm_schedule_interval_minutes: int = 60
    llm_market_hours_only: bool = True

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return the configuration as a serialisable dictionary."""

        return asdict(self)

    @classmethod
    def from_mapping(cls, mapping: Dict[str, Any]) -> "BotConfig":
        """Create a :class:`BotConfig` instance from a raw mapping."""

        known_fields = {field.name for field in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        direct_values = {k: v for k, v in mapping.items() if k in known_fields}
        metadata = {k: v for k, v in mapping.items() if k not in known_fields}
        config = cls(**direct_values)
        config.metadata = metadata
        return config

    @classmethod
    def from_file(cls, path: str | Path) -> "BotConfig":
        """Load configuration from a TOML or JSON document."""

        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file '{file_path}' does not exist")

        suffix = file_path.suffix.lower()
        if suffix in {".toml", ".tml"}:
            if tomllib is None:
                raise RuntimeError("tomllib is not available on this Python interpreter")
            with file_path.open("rb") as fp:
                raw_data = tomllib.load(fp)
        elif suffix == ".json":
            with file_path.open("r", encoding="utf-8") as fp:
                raw_data = json.load(fp)
        else:
            raise ValueError("Unsupported configuration format. Use TOML or JSON.")

        if not isinstance(raw_data, dict):
            raise ValueError("Configuration root must be a mapping/dictionary")

        return cls.from_mapping(raw_data)

    def copy(self, **updates: Any) -> "BotConfig":
        """Return a shallow copy of the configuration with optional overrides."""

        data = self.to_dict()
        data.update(updates)
        metadata = data.pop("metadata", {})
        new_config = BotConfig(**data)
        new_config.metadata = metadata
        return new_config
