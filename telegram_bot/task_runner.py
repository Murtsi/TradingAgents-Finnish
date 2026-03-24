"""
Analyysin ajaminen asyncio-ympäristössä.

MIGRAATIOPISTE B→C:
  Vaihtoehto B (nyt):  run_in_executor + ThreadPoolExecutor
  Vaihtoehto C (myöh): Celery task + run_in_executor(task.get)

Tämä on ainoa tiedosto joka muuttuu B→C migraatiossa.
EI sisällä asyncio.Lock:ia — se on handlers.py:ssä.
EI käytä os.chdir() — kaikki polut ovat absoluuttisia.
"""
from __future__ import annotations
import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Callable, Awaitable

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.finnish_config import get_finnish_config
from telegram_bot.progress import AnalysisProgressCallback
from telegram_bot.formatter import format_summary, format_full_report
from telegram_bot.omxh import get_current_price

logger = logging.getLogger(__name__)

# Projektin juuri absoluuttisena polkuna
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Yksi executor — max_workers=1 koska handlers.py:n Lock estää rinnakkaisajot
_executor = ThreadPoolExecutor(max_workers=1)

# Analyysin timeout sekunteina (10 minuuttia)
ANALYSIS_TIMEOUT_SEC = 600


def _sync_run_analysis(ticker: str, callback: AnalysisProgressCallback) -> dict:
    """
    Synkroninen funktio joka ajetaan threadissa.
    Uusi TradingAgentsGraph per pyyntö (instanssi on tilallinen — ei jaeta).

    Kaikki 4 analyytikkoa aina.
    TEST_MODE=true → get_finnish_config() lisää max_tokens=500 (halvempi, lyhyemmät raportit).
    """
    config = get_finnish_config({
        "results_dir": os.path.join(_PROJECT_ROOT, "results"),
    })

    # Kaikki 4 analyytikkoa aina — TEST_MODE rajoittaa max_tokens (kustannukset),
    # ei analyysilaajuutta (get_finnish_config() hoitaa TEST_OVERRIDES automaattisesti)
    selected_analysts = ["market", "social", "news", "fundamentals"]

    graph = TradingAgentsGraph(
        config=config,
        callbacks=[callback],
        debug=False,
        selected_analysts=selected_analysts,
    )
    trade_date = str(date.today())
    final_state, decision = graph.propagate(ticker, trade_date)
    final_state["_decision_raw"] = decision
    return final_state


async def _elapsed_timer(
    edit_fn: Callable[[str], Awaitable[None]],
    ticker: str,
    stop: asyncio.Event,
) -> None:
    """
    Background task: päivittää progress-viestiä 30s välein suoraan await:lla.
    EI mene callback-kautta (callback._push_update on tarkoitettu threadeille).
    """
    elapsed = 0
    while not stop.is_set():
        await asyncio.sleep(30)
        if stop.is_set():
            break
        elapsed += 30
        mins = elapsed // 60
        secs = elapsed % 60
        try:
            await edit_fn(
                f"📊 Analysoin: *{ticker}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔄 Analyysi käynnissä \\(kestää 2–5 min\\)\n"
                f"⏱ Kulunut: {mins} min {secs:02d} s"
            )
        except Exception:
            pass


async def run_analysis(
    ticker: str,
    edit_message_fn: Callable[[str], Awaitable[None]],
) -> tuple[str, str]:
    """
    Käynnistää analyysin threadissa asyncio.wait_for timeout-suojauksella.

    Returns:
        (summary_text, full_report_text)

    Raises:
        asyncio.TimeoutError: jos analyysi kestää yli ANALYSIS_TIMEOUT_SEC
        Exception: muut virheet propagoituvat kutsujalle (handlers.py käsittelee)
    """
    loop = asyncio.get_running_loop()
    callback = AnalysisProgressCallback(
        ticker=ticker.replace(".HE", ""),
        loop=loop,
        edit_fn=edit_message_fn,
    )

    # Background timer: päivittää kuluneen ajan 30s välein vaikka callbackit
    # eivät laukeaisi — varmistaa että käyttäjä tietää botin olevan hengissä
    timer_stop = asyncio.Event()
    timer_task = asyncio.create_task(_elapsed_timer(edit_message_fn, ticker, timer_stop))

    try:
        final_state = await asyncio.wait_for(
            loop.run_in_executor(_executor, _sync_run_analysis, ticker, callback),
            timeout=ANALYSIS_TIMEOUT_SEC,
        )
    finally:
        timer_stop.set()
        timer_task.cancel()
        try:
            await timer_task
        except asyncio.CancelledError:
            pass

    current_price = await loop.run_in_executor(None, get_current_price, ticker)
    summary = format_summary(final_state, current_price=current_price)
    full_report = format_full_report(final_state)
    return summary, full_report
