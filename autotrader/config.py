"""Ympäristömuuttujista luettava autotrader-konfiguraatio."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _env_list(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_time(value: str | None, default: str = "09:15") -> time:
    raw = value or default
    hour, minute = raw.split(":", maxsplit=1)
    return time(hour=int(hour), minute=int(minute))


def _parse_uic_overrides(value: str | None) -> dict[str, int]:
    """Parsi muodosta 'NOKIA.HE=12345,NDA-FI.HE=67890'."""
    if not value:
        return {}
    overrides: dict[str, int] = {}
    for item in value.split(","):
        if "=" not in item:
            continue
        ticker, uic = item.split("=", maxsplit=1)
        ticker = ticker.strip().upper()
        if ticker:
            overrides[ticker] = int(uic.strip())
    return overrides


@dataclass(frozen=True)
class TraderConfig:
    """Autonomisen paper traderin asetukset.

    Oletus on Saxo SIM. Live-käyttö estetään kahdella portilla:
    SAXO_ENV=live ja ALLOW_LIVE=1. Tässä PR:ssä live ei vielä lähetä
    toimeksiantoja ilman erillistä seuraavaa vaihetta.
    """

    broker: str = "saxo"
    saxo_env: str = "sim"
    saxo_token: str | None = None
    allow_live: bool = False
    trading_halt: bool = False
    dry_run: bool = False

    database_url: str = "sqlite:///autotrader.sqlite3"
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    timezone: str = "Europe/Helsinki"
    run_time: time = time(9, 15)
    include_sweden: bool = False
    universe: list[str] = field(default_factory=list)
    extra_tickers: list[str] = field(default_factory=list)
    shortlist_size: int = 8
    max_analyses_per_run: int = 5
    llm_tier: str = "haiku"

    initial_cash: float = 10_000.0
    commission_pct: float = 0.001
    slippage_pct: float = 0.001

    max_position_pct: float = 0.12
    min_cash_buffer_pct: float = 0.08
    max_daily_orders: int = 8
    max_new_buys: int = 3
    drawdown_halt_pct: float = 0.15
    underweight_trim_pct: float = 0.50
    uic_overrides: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "TraderConfig":
        """Luo konfiguraatio ympäristömuuttujista."""
        return cls(
            broker=os.getenv("BROKER", "saxo").strip().lower(),
            saxo_env=os.getenv("SAXO_ENV", "sim").strip().lower(),
            saxo_token=os.getenv("SAXO_TOKEN"),
            allow_live=_env_bool("ALLOW_LIVE"),
            trading_halt=_env_bool("TRADING_HALT"),
            dry_run=_env_bool("AUTOTRADER_DRY_RUN"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///autotrader.sqlite3"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or os.getenv("AUTOTRADER_TELEGRAM_CHAT_ID"),
            timezone=os.getenv("AUTOTRADER_TIMEZONE", "Europe/Helsinki"),
            run_time=_parse_time(os.getenv("AUTOTRADER_RUN_TIME"), "09:15"),
            include_sweden=_env_bool("AUTOTRADER_INCLUDE_SWEDEN"),
            universe=_env_list("AUTOTRADER_UNIVERSE"),
            extra_tickers=_env_list("AUTOTRADER_EXTRA_TICKERS"),
            shortlist_size=_env_int("AUTOTRADER_SHORTLIST_SIZE", 8),
            max_analyses_per_run=_env_int("AUTOTRADER_MAX_ANALYSES", 5),
            llm_tier=os.getenv("AUTOTRADER_LLM_TIER", "haiku").strip().lower(),
            initial_cash=_env_float("AUTOTRADER_INITIAL_CASH", 10_000.0),
            commission_pct=_env_float("AUTOTRADER_COMMISSION_PCT", 0.001),
            slippage_pct=_env_float("AUTOTRADER_SLIPPAGE_PCT", 0.001),
            max_position_pct=_env_float("AUTOTRADER_MAX_POSITION_PCT", 0.12),
            min_cash_buffer_pct=_env_float("AUTOTRADER_MIN_CASH_BUFFER_PCT", 0.08),
            max_daily_orders=_env_int("AUTOTRADER_MAX_DAILY_ORDERS", 8),
            max_new_buys=_env_int("AUTOTRADER_MAX_NEW_BUYS", 3),
            drawdown_halt_pct=_env_float("AUTOTRADER_DRAWDOWN_HALT_PCT", 0.15),
            underweight_trim_pct=_env_float("AUTOTRADER_UNDERWEIGHT_TRIM_PCT", 0.50),
            uic_overrides=_parse_uic_overrides(os.getenv("SAXO_UIC_OVERRIDES")),
        ).validate()

    def validate(self) -> "TraderConfig":
        """Tarkista kriittiset asetukset ja palauta sama olio ketjutusta varten."""
        if self.broker not in {"saxo", "memory"}:
            raise ValueError("BROKER pitää olla 'saxo' tai 'memory'.")
        if self.saxo_env not in {"sim", "live"}:
            raise ValueError("SAXO_ENV pitää olla 'sim' tai 'live'.")
        if self.saxo_env == "live" and not self.allow_live:
            raise ValueError("Live-käyttö estetty: aseta SAXO_ENV=live ja ALLOW_LIVE=1.")
        if self.saxo_env == "live":
            raise ValueError("Saxo live -toimeksiantoja ei toteuteta tässä vaiheessa.")
        if self.broker == "saxo" and not self.saxo_token and not self.dry_run:
            raise ValueError("SAXO_TOKEN puuttuu Saxo SIM -brokerilta.")
        if self.shortlist_size <= 0:
            raise ValueError("AUTOTRADER_SHORTLIST_SIZE pitää olla positiivinen.")
        if self.max_analyses_per_run <= 0:
            raise ValueError("AUTOTRADER_MAX_ANALYSES pitää olla positiivinen.")
        if not 0 < self.max_position_pct <= 1:
            raise ValueError("AUTOTRADER_MAX_POSITION_PCT pitää olla välillä 0..1.")
        if not 0 <= self.min_cash_buffer_pct < 1:
            raise ValueError("AUTOTRADER_MIN_CASH_BUFFER_PCT pitää olla välillä 0..1.")
        return self

    @property
    def saxo_rest_base(self) -> str:
        if self.saxo_env == "sim":
            return "https://gateway.saxobank.com/sim/openapi"
        return "https://gateway.saxobank.com/openapi"

    @property
    def saxo_auth_base(self) -> str:
        if self.saxo_env == "sim":
            return "https://sim.logonvalidation.net"
        return "https://live.logonvalidation.net"
