"""Osakeuniversumin muodostus."""

from __future__ import annotations

from autotrader.config import TraderConfig
from tradingagents.dataflows.omxh_utils import OMXH_COMPANY_NAMES, resolve_ticker


def build_universe(config: TraderConfig) -> list[str]:
    """Palauta FI+valinnainen EU/Nordic-universumi Yahoo Finance -tickereinä."""
    if config.universe:
        base = [resolve_ticker(ticker) for ticker in config.universe]
    else:
        base = [
            ticker
            for ticker in OMXH_COMPANY_NAMES
            if ticker.endswith(".HE") or (config.include_sweden and ticker.endswith(".ST"))
        ]

    extras = [resolve_ticker(ticker) for ticker in config.extra_tickers]
    seen: set[str] = set()
    result: list[str] = []
    for ticker in [*base, *extras]:
        normalized = ticker.upper()
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
