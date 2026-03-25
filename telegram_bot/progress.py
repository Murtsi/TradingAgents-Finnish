from __future__ import annotations
import asyncio
import logging
from typing import Any
from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)

# LangGraph node-nimet → suomenkieliset vaiheet
# Nimet tulevat setup.py:n workflow.add_node() kutsuista
STAGE_MAP: dict[str, str] = {
    # Analyytikot (add_node käyttää f"{analyst_type.capitalize()} Analyst")
    "market analyst":        "Tekninen analyysi",
    "social analyst":        "Sentimenttianalyysi",
    "news analyst":          "Uutisanalyysi",
    "fundamentals analyst":  "Fundamenttianalyysi",
    # Tutkijat
    "bull researcher":       "Bull-tutkija",
    "bear researcher":       "Bear-tutkija",
    "research manager":      "Väittelytuomari",
    # Päätöksenteko
    "trader":                "Kaupankäyntipäätös",
    "aggressive analyst":    "Riskiarvio (aggressiivinen)",
    "neutral analyst":       "Riskiarvio (neutraali)",
    "conservative analyst":  "Riskiarvio (konservatiivinen)",
    "portfolio manager":     "Salkunhoitaja",
}

# Järjestetty lista käyttöliittymään (näytetään tässä järjestyksessä)
ALL_STAGES = [
    "Fundamenttianalyysi",
    "Tekninen analyysi",
    "Sentimenttianalyysi",
    "Uutisanalyysi",
    "Bull-tutkija",
    "Bear-tutkija",
    "Kaupankäyntipäätös",
    "Riskiarvio",
    "Salkunhoitaja",
]


def _build_progress_message(
    ticker: str,
    completed: list[str],
    current: str | None,
    elapsed_sec: int = 0,
) -> str:
    """Puhdas funktio — rakentaa progress-viestin nykyisen tilan perusteella."""
    lines = [
        f"Analysoin: *{ticker}*",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]
    for stage in ALL_STAGES:
        # Riskit on yhdistetty yhteen riviin UI:ssa
        if stage == "Riskiarvio":
            riskivaiheet = [s for s in completed if "Riskiarvio" in s]
            if riskivaiheet:
                lines.append("[VALMIS] Riskiarvio")
            elif current and "Riskiarvio" in current:
                lines.append("[...] Riskiarvio käynnissä...")
            else:
                lines.append("[ ] Riskiarvio")
            continue

        if stage in completed:
            lines.append(f"[VALMIS] {stage}")
        elif stage == current:
            lines.append(f"[...] {stage} käynnissä...")
        else:
            lines.append(f"[ ] {stage}")

    if elapsed_sec > 0:
        mins = elapsed_sec // 60
        secs = elapsed_sec % 60
        lines.append(f"\nKulunut: {mins} min {secs:02d} s")

    return "\n".join(lines)


class AnalysisProgressCallback(BaseCallbackHandler):
    """
    LangChain callback joka päivittää Telegram-viestiä reaaliajassa.

    Kuuntelee on_chain_start-tapahtumia jotka LangGraph laukaisee
    kun kukin agentti-node käynnistyy.

    Toimii threadissa — käyttää asyncio.run_coroutine_threadsafe() pääloopille.
    """

    def __init__(self, ticker: str, loop: asyncio.AbstractEventLoop, edit_fn):
        super().__init__()
        self.ticker = ticker
        self.loop = loop
        self.edit_fn = edit_fn
        self.completed: list[str] = []
        self.current: str | None = None
        self.elapsed_sec: int = 0
        self._last_sent: str = ""  # Deduplikointi — estää turhat editMessageText-kutsut

    def _resolve_stage(self, name: str) -> str | None:
        """Etsii stage-nimen node-nimestä (case-insensitive partial match)."""
        name_lower = name.lower()
        for key, label in STAGE_MAP.items():
            if key in name_lower:
                return label
        return None

    def on_chain_start(self, serialized: dict[str, Any], inputs: Any, **kwargs) -> None:
        """Laukeaa kun LangGraph-node käynnistyy."""
        if not serialized:
            name = kwargs.get("name", "") or kwargs.get("run_name", "") or ""
        else:
            name = (
                serialized.get("name", "")
                or (serialized.get("id") or [""])[-1]
                or ""
            )
        stage = self._resolve_stage(str(name))
        if stage is None:
            return
        if self.current and self.current not in self.completed:
            self.completed.append(self.current)
        self.current = stage
        self._push_update()

    def on_chain_end(self, outputs: Any, **kwargs) -> None:
        """Laukeaa kun LangGraph-node päättyy."""
        if self.current and self.current not in self.completed:
            self.completed.append(self.current)
            self.current = None
            self._push_update()

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs) -> None:
        """Fallback: yritä tunnistaa agentti myös LLM-tasolta."""
        # LLM-tason serialized ei yleensä sisällä agentin nimeä,
        # mutta jotkut LangChain-versiot välittävät sen metadata-kentässä
        run_name = kwargs.get("run_name", "") or ""
        stage = self._resolve_stage(run_name)
        if stage and stage != self.current:
            if self.current and self.current not in self.completed:
                self.completed.append(self.current)
            self.current = stage
            self._push_update()

    def update_elapsed(self, elapsed_sec: int) -> None:
        """Päivitetään kuluneen ajan näyttö (kutsutaan background-timerista threadista)."""
        self.elapsed_sec = elapsed_sec
        self._push_update()

    async def push_update_async(self, elapsed_sec: int) -> None:
        """Päivitetään kuluneen ajan näyttö asyncio-kontekstista (ei threadista)."""
        self.elapsed_sec = elapsed_sec
        msg = _build_progress_message(self.ticker, self.completed, self.current, self.elapsed_sec)
        if msg == self._last_sent:
            return
        self._last_sent = msg
        await self.edit_fn(msg)

    def _push_update(self) -> None:
        msg = _build_progress_message(
            self.ticker, self.completed, self.current, self.elapsed_sec
        )
        if msg == self._last_sent:
            return  # Sama teksti — älä lähetä, estää 400 "message is not modified"
        self._last_sent = msg
        future = asyncio.run_coroutine_threadsafe(self.edit_fn(msg), self.loop)
        try:
            future.result(timeout=5)
        except Exception as e:
            logger.warning(f"Progress-päivitys epäonnistui: {e}")
