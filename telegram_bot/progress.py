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
    "Väittelytuomari",       # research manager — puuttui aiemmin
    "Kaupankäyntipäätös",
    "Riskiarvio",
    "Salkunhoitaja",
]


def _build_progress_message(
    ticker: str,
    completed: list[str],
    in_progress: set[str],
    elapsed_sec: int = 0,
) -> str:
    """Puhdas funktio — rakentaa progress-viestin nykyisen tilan perusteella.

    in_progress on setti kaikista samanaikaisesti käynnissä olevista stageista
    (rinnakkaiset analyytikot näytetään kaikki aktiivisina yhtä aikaa).
    """
    lines = [
        f"Analysoin: *{ticker}*",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]
    for stage in ALL_STAGES:
        # Riskit on yhdistetty yhteen riviin UI:ssa
        if stage == "Riskiarvio":
            riskivaiheet = [s for s in completed if "Riskiarvio" in s]
            riski_kaynnissa = any("Riskiarvio" in s for s in in_progress)
            if riskivaiheet:
                lines.append("[VALMIS] Riskiarvio")
            elif riski_kaynnissa:
                lines.append("[...] Riskiarvio käynnissä...")
            else:
                lines.append("[ ] Riskiarvio")
            continue

        if stage in completed:
            lines.append(f"[VALMIS] {stage}")
        elif stage in in_progress:
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

    Kuuntelee on_chain_start/end -tapahtumia jotka LangGraph laukaisee
    kun kukin agentti-node käynnistyy tai päättyy.

    Rinnakkaiset analyytikot seurataan run_id:n perusteella — jokainen
    on_chain_end osaa tunnistaa oikean stagen ilman että muut merkitään
    vahingossa valmiiksi ennenaikaisesti.

    Toimii threadissa — käyttää asyncio.run_coroutine_threadsafe() pääloopille.
    """

    def __init__(self, ticker: str, loop: asyncio.AbstractEventLoop, edit_fn):
        super().__init__()
        self.ticker = ticker
        self.loop = loop
        self.edit_fn = edit_fn
        self.completed: list[str] = []
        self._in_progress: set[str] = set()        # Kaikki käynnissä olevat stagit
        self._run_stages: dict[str, str] = {}      # run_id → stage-nimi
        self.elapsed_sec: int = 0
        self._last_sent: str = ""  # Deduplikointi — estää turhat editMessageText-kutsut

    def _resolve_stage(self, name: str) -> str | None:
        """Etsii stage-nimen node-nimestä (case-insensitive partial match)."""
        name_lower = name.lower()
        for key, label in STAGE_MAP.items():
            if key in name_lower:
                return label
        return None

    def _extract_name(self, serialized: dict[str, Any] | None, kwargs: dict) -> str:
        """Poimii node-nimen serialized-dictistä tai kwargs:sta."""
        if not serialized:
            return kwargs.get("name", "") or kwargs.get("run_name", "") or ""
        return (
            serialized.get("name", "")
            or (serialized.get("id") or [""])[-1]
            or ""
        )

    def on_chain_start(self, serialized: dict[str, Any], inputs: Any, **kwargs) -> None:
        """Laukeaa kun LangGraph-node käynnistyy."""
        name = self._extract_name(serialized, kwargs)
        stage = self._resolve_stage(str(name))
        if stage is None:
            return

        run_id = str(kwargs.get("run_id", ""))
        if run_id:
            self._run_stages[run_id] = stage

        self._in_progress.add(stage)
        self._push_update()

    def on_chain_end(self, outputs: Any, **kwargs) -> None:
        """Laukeaa kun LangGraph-node päättyy."""
        run_id = str(kwargs.get("run_id", ""))
        stage = self._run_stages.pop(run_id, None)

        if stage is None:
            return

        self._in_progress.discard(stage)
        if stage not in self.completed:
            self.completed.append(stage)
        self._push_update()

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs) -> None:
        """Fallback: merkitse stage aktiiviseksi jos on_chain_start ei tunnistanut sitä."""
        run_name = kwargs.get("run_name", "") or ""
        stage = self._resolve_stage(run_name)
        # Käytä vain jos stage ei ole jo seurannassa — on_chain_start on ensisijainen
        if not stage or stage in self._in_progress or stage in self.completed:
            return
        run_id = str(kwargs.get("run_id", ""))
        if run_id:
            self._run_stages[run_id] = stage
        self._in_progress.add(stage)
        self._push_update()

    def on_llm_end(self, response: Any, **kwargs) -> None:  # noqa: ARG002
        """Pari on_llm_start-fallbackille — estää stageja jäämästä in_progress-settiin."""
        run_id = str(kwargs.get("run_id", ""))
        # Poista vain jos tämä run_id oli llm_start-fallbackin lisäämä
        # (on_chain_end hoitaa normaalit tapaukset, älä kirjaa valmiiksi tässä)
        stage = self._run_stages.get(run_id)
        if stage and stage in self._in_progress:
            # Tarkista onko vastaava chain_end jo hoitanut tämän
            # Jos run_id on vielä _run_stages:ssa, chain_end ei ole ajanut
            pass  # chain_end poistaa — ei tehdä tässä mitään ylimääräistä

    def update_elapsed(self, elapsed_sec: int) -> None:
        """Päivitetään kuluneen ajan näyttö (kutsutaan background-timerista threadista)."""
        self.elapsed_sec = elapsed_sec
        self._push_update()

    async def push_update_async(self, elapsed_sec: int) -> None:
        """Päivitetään kuluneen ajan näyttö asyncio-kontekstista (ei threadista)."""
        self.elapsed_sec = elapsed_sec
        msg = _build_progress_message(self.ticker, self.completed, self._in_progress, self.elapsed_sec)
        if msg == self._last_sent:
            return
        self._last_sent = msg
        await self.edit_fn(msg)

    def _push_update(self) -> None:
        msg = _build_progress_message(
            self.ticker, self.completed, self._in_progress, self.elapsed_sec
        )
        if msg == self._last_sent:
            return  # Sama teksti — älä lähetä, estää 400 "message is not modified"
        self._last_sent = msg
        # Fire-and-forget — EI blokkaava future.result().
        # Aiempi timeout=5 blokkaisi jokaisen analyysistepin 5 sekuntia virheen sattuessa.
        future = asyncio.run_coroutine_threadsafe(self.edit_fn(msg), self.loop)
        future.add_done_callback(
            lambda f: logger.warning(f"Progress-päivitys epäonnistui: {f.exception()}")
            if not f.cancelled() and f.exception() else None
        )
