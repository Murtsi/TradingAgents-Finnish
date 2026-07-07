"""KauppaAgentit-pipelinen kääre autotraderille."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from autotrader.config import TraderConfig
from tradingagents.finnish_config import get_finnish_config
from tradingagents.graph.trading_graph import TradingAgentsGraph

logger = logging.getLogger(__name__)

VALID_DECISIONS = {"BUY", "OVERWEIGHT", "HOLD", "UNDERWEIGHT", "SELL"}


@dataclass(frozen=True)
class AnalysisResult:
    """Yhden tickerin LLM-analyysin tulos."""

    ticker: str
    decision: str
    final_state: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def _llm_overrides(config: TraderConfig) -> dict[str, Any]:
    """Mapita autotraderin LLM-tier KauppaAgentit-konfiguraatioon."""
    if config.llm_tier == "sonnet":
        return {
            "deep_think_llm": "claude-sonnet-4-20250514",
            "quick_think_llm": "claude-haiku-4-5-20251001",
        }
    return {
        "deep_think_llm": "claude-haiku-4-5-20251001",
        "quick_think_llm": "claude-haiku-4-5-20251001",
    }


def normalize_decision(decision: str | None) -> str:
    """Pidä vain tunnetut signaalit, muuten turvallinen HOLD."""
    if not decision:
        return "HOLD"
    cleaned = decision.strip().upper()
    for valid in VALID_DECISIONS:
        if cleaned == valid or cleaned.startswith(valid):
            return valid
    return "HOLD"


class PipelineAnalyzer:
    """Ajaa olemassa olevan TradingAgentsGraphin."""

    def __init__(self, config: TraderConfig):
        self.config = config

    def analyze(self, ticker: str, trade_date: str) -> AnalysisResult:
        """Aja pipeline. Virhe palauttaa turvallisen HOLD-signaalin."""
        try:
            cfg = get_finnish_config(
                {
                    **_llm_overrides(self.config),
                    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
                }
            )
            graph = TradingAgentsGraph(
                config=cfg,
                selected_analysts=["market", "social", "news", "fundamentals"],
                debug=False,
            )
            final_state, decision = graph.propagate(ticker, trade_date)
            return AnalysisResult(
                ticker=ticker,
                decision=normalize_decision(decision),
                final_state=final_state,
            )
        except Exception as exc:
            logger.exception("Autotrader-analyysi epäonnistui tickerille %s", ticker)
            return AnalysisResult(ticker=ticker, decision="HOLD", error=str(exc))
