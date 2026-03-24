from __future__ import annotations
import asyncio
import logging
from typing import Any
from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)

STAGE_MAP: dict[str, str] = {
    "fundamentals": "Fundamenttianalyysi",
    "market":       "Tekninen analyysi",
    "social":       "Sentimenttianalyysi",
    "news":         "Uutisanalyysi",
    "bull":         "Bull-tutkija",
    "bear":         "Bear-tutkija",
    "trader":       "Kaupankäyntipäätös",
    "risk":         "Riskiarvio",
    "portfolio":    "Salkunhoitaja",
}

ALL_STAGES = list(STAGE_MAP.values())


def _build_progress_message(ticker: str, completed: list[str], current: str | None) -> str:
    """Puhdas funktio — rakentaa progress-viestin nykyisen tilan perusteella."""
    lines = [
        f"📊 Analysoin: *{ticker}*",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]
    for stage in ALL_STAGES:
        if stage in completed:
            lines.append(f"✅ {stage}")
        elif stage == current:
            lines.append(f"🔄 {stage} käynnissä...")
        else:
            lines.append(f"⏳ {stage}")
    return "\n".join(lines)


class AnalysisProgressCallback(BaseCallbackHandler):
    """
    LangChain callback joka päivittää Telegram-viestiä reaaliajassa.
    Toimii threadissa — käyttää asyncio.run_coroutine_threadsafe() pääloopille.
    """

    def __init__(self, ticker: str, loop: asyncio.AbstractEventLoop, edit_fn):
        super().__init__()
        self.ticker = ticker
        self.loop = loop
        self.edit_fn = edit_fn
        self.completed: list[str] = []
        self.current: str | None = None

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs) -> None:
        name = serialized.get("name", "").lower()
        stage = next((label for key, label in STAGE_MAP.items() if key in name), None)
        if stage is None:
            return
        if self.current and self.current not in self.completed:
            self.completed.append(self.current)
        self.current = stage
        self._push_update()

    def on_llm_end(self, response: Any, **kwargs) -> None:
        if self.current and self.current not in self.completed:
            self.completed.append(self.current)
            self.current = None
            self._push_update()

    def _push_update(self) -> None:
        msg = _build_progress_message(self.ticker, self.completed, self.current)
        future = asyncio.run_coroutine_threadsafe(self.edit_fn(msg), self.loop)
        try:
            future.result(timeout=5)
        except Exception as e:
            logger.warning(f"Progress-päivitys epäonnistui: {e}")
