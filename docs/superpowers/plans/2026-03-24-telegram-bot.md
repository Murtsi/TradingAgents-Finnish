# KauppaAgentit Telegram-botti — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lisää Telegram-botti joka vastaanottaa `/analysoi NOKIA` -komennon ja palauttaa suomalaisen multi-agent LLM-osakeanalyysin tiivistelmän Telegramin kautta.

**Architecture:** Async `python-telegram-bot` -botti ajaa `TradingAgentsGraph.propagate()`:n erillisessä threadissa (`run_in_executor`) jotta botti pysyy responsiivisena. Globaali `asyncio.Lock` elää `handlers.py`:ssä (ei task_runner:ssa). LangChain `BaseCallbackHandler` välittää agenttitilapäivitykset live-viestiin. Kaikki tiedostopolut ovat absoluuttisia — ei `os.chdir()`.

**Tech Stack:** `python-telegram-bot>=20.0`, `langchain-core` (BaseCallbackHandler), `yfinance` (ticker-validointi), `python-dotenv`, `pytest`, `pytest-asyncio`

**Spec:** `docs/superpowers/specs/2026-03-24-telegram-bot-design.md`

---

## Tiedostokartta

| Tiedosto | Toiminto |
|----------|---------|
| `telegram_bot/__init__.py` | Tyhjä paketti |
| `telegram_bot/whitelist.py` | Parsii `TELEGRAM_WHITELIST` env-muuttujasta sallitut käyttäjä-ID:t |
| `telegram_bot/progress.py` | `BaseCallbackHandler` — välittää agenttitapahtumat live-viestipäivityksiin |
| `telegram_bot/formatter.py` | Muotoilee `final_state`-dictin Telegram-markdown-viestiksi |
| `telegram_bot/omxh.py` | Ohut wrapper ticker-validoinnille ja hinnan haulle |
| `telegram_bot/task_runner.py` | `run_in_executor` wrapper — ainoa B→C migraatiopiste. Ei Lock:ia. |
| `telegram_bot/handlers.py` | `/analysoi`-käsittelijä: whitelist, ticker-validointi, `asyncio.Lock`, timeout |
| `telegram_bot/bot.py` | Entry point: `ApplicationBuilder`, rekisteröi handlerit |
| `tests/telegram_bot/test_whitelist.py` | Yksikkötestit whitelist-logiikalle |
| `tests/telegram_bot/test_formatter.py` | Yksikkötestit tuloksen muotoilulle |
| `tests/telegram_bot/test_ticker_validation.py` | Yksikkötestit ticker-validoinnille |
| `tests/telegram_bot/test_progress.py` | Yksikkötestit progress-viestin muodostamiselle |
| `tests/telegram_bot/test_handlers.py` | Yksikkötestit handler-logiikalle (whitelist-esto, validointi, lock) |
| `pyproject.toml` | Lisää `python-telegram-bot>=20.0` ja `pytest-asyncio` |
| `.env` | Lisää `TELEGRAM_BOT_TOKEN` ja `TELEGRAM_WHITELIST` placeholderit |

---

## Task 1: Riippuvuudet ja kansiorakenne

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env`
- Create: `telegram_bot/__init__.py`
- Create: `tests/telegram_bot/__init__.py`

- [ ] **Step 1: Lisää riippuvuudet pyproject.toml:iin**

```toml
# pyproject.toml — dependencies-listaan lisää:
"python-telegram-bot>=20.0",
"pytest-asyncio>=0.23.0",
```

- [ ] **Step 2: Lisää placeholderit .env:iin**

Lisää `.env`-tiedoston loppuun (`.env` on jo `.gitignore`:ssa — älä koskaan committaa sitä):
```
# Telegram-botti
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_WHITELIST=123456789,987654321
```

- [ ] **Step 3: Luo kansiorakenne**

```bash
mkdir -p telegram_bot
mkdir -p tests/telegram_bot
touch telegram_bot/__init__.py
touch tests/telegram_bot/__init__.py
```

- [ ] **Step 4: Asenna riippuvuudet**

```bash
pip install "python-telegram-bot>=20.0" "pytest-asyncio>=0.23.0"
```

Odotettu: asennus onnistuu ilman konflikteja.

- [ ] **Step 5: Commit (EI .env:iä)**

```bash
git add pyproject.toml telegram_bot/__init__.py tests/telegram_bot/__init__.py
git commit -m "chore: lisää telegram-bot kansiorakenne ja riippuvuudet"
```

---

## Task 2: whitelist.py

**Files:**
- Create: `telegram_bot/whitelist.py`
- Create: `tests/telegram_bot/test_whitelist.py`

- [ ] **Step 1: Kirjoita epäonnistuvat testit**

```python
# tests/telegram_bot/test_whitelist.py
import os
import pytest
from telegram_bot.whitelist import load_whitelist, is_allowed

def test_load_whitelist_parses_ids(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WHITELIST", "111,222,333")
    assert load_whitelist() == {111, 222, 333}

def test_load_whitelist_empty_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WHITELIST", "")
    assert load_whitelist() == set()

def test_load_whitelist_missing_env(monkeypatch):
    monkeypatch.delenv("TELEGRAM_WHITELIST", raising=False)
    assert load_whitelist() == set()

def test_load_whitelist_strips_spaces(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WHITELIST", " 111 , 222 ")
    assert load_whitelist() == {111, 222}

def test_is_allowed_true(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WHITELIST", "42")
    assert is_allowed(42) is True

def test_is_allowed_false(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WHITELIST", "42")
    assert is_allowed(99) is False
```

- [ ] **Step 2: Aja testit — varmista FAIL**

```bash
pytest tests/telegram_bot/test_whitelist.py -v
```

Odotettu: `ModuleNotFoundError: No module named 'telegram_bot.whitelist'`

- [ ] **Step 3: Toteuta whitelist.py**

```python
# telegram_bot/whitelist.py
import os
import logging

logger = logging.getLogger(__name__)

def load_whitelist() -> set[int]:
    """Lataa sallitut Telegram-käyttäjä-ID:t TELEGRAM_WHITELIST-muuttujasta."""
    raw = os.getenv("TELEGRAM_WHITELIST", "")
    if not raw.strip():
        return set()
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                ids.add(int(part))
            except ValueError:
                logger.warning(f"Virheellinen käyttäjä-ID whitelistissä: {part!r}")
    return ids

def is_allowed(user_id: int) -> bool:
    """Tarkistaa onko käyttäjä sallitulla whitelistillä."""
    whitelist = load_whitelist()
    allowed = user_id in whitelist
    if not allowed:
        logger.warning(f"Whitelist-esto: käyttäjä {user_id}")
    return allowed
```

- [ ] **Step 4: Aja testit — varmista PASS**

```bash
pytest tests/telegram_bot/test_whitelist.py -v
```

Odotettu: kaikki 6 testiä vihreänä.

- [ ] **Step 5: Commit**

```bash
git add telegram_bot/whitelist.py tests/telegram_bot/test_whitelist.py
git commit -m "feat: telegram whitelist-tarkistus"
```

---

## Task 3: formatter.py

`final_state` on dict joka sisältää `final_trade_decision`, `market_report`, `sentiment_report`, `news_report`, `fundamentals_report`, `trader_investment_plan`. Formatter muotoilee tämän lyhyeksi Telegram-viestiksi.

**Files:**
- Create: `telegram_bot/formatter.py`
- Create: `tests/telegram_bot/test_formatter.py`

- [ ] **Step 1: Kirjoita epäonnistuvat testit**

```python
# tests/telegram_bot/test_formatter.py
import pytest
from telegram_bot.formatter import format_summary, format_full_report, parse_decision

MOCK_STATE = {
    "company_of_interest": "NOKIA.HE",
    "trade_date": "2026-03-24",
    "final_trade_decision": "BUY - Nokia on aliarvostettu. Luottamustaso: Korkea.",
    "market_report": "Tekninen analyysi: RSI 45, trendi nouseva...",
    "sentiment_report": "Sentimentti positiivinen Kauppalehdessä...",
    "news_report": "Nokia voitti 5G-sopimuksen...",
    "fundamentals_report": "P/E 12, EV/EBITDA 8...",
    "trader_investment_plan": "Suositus: OSTA. Hintatavoite 5,00 €.",
    "investment_plan": "Riskiarvio: Kohtuullinen.",
}

def test_parse_decision_buy():
    assert parse_decision("BUY - perustelut") == "OSTA"

def test_parse_decision_sell():
    assert parse_decision("SELL - perustelut") == "MYY"

def test_parse_decision_hold():
    assert parse_decision("HOLD - perustelut") == "PIDÄ"

def test_parse_decision_case_insensitive():
    assert parse_decision("buy - lowercase") == "OSTA"

def test_format_summary_contains_ticker():
    summary = format_summary(MOCK_STATE, current_price=4.23)
    assert "NOKIA" in summary

def test_format_summary_contains_suositus():
    summary = format_summary(MOCK_STATE, current_price=4.23)
    assert "OSTA" in summary

def test_format_summary_contains_disclaimer():
    summary = format_summary(MOCK_STATE, current_price=4.23)
    assert "sijoitussuositus" in summary.lower()

def test_format_summary_contains_price():
    summary = format_summary(MOCK_STATE, current_price=4.23)
    assert "4,23" in summary

def test_format_full_report_contains_all_sections():
    report = format_full_report(MOCK_STATE)
    assert "Tekninen" in report
    assert "Sentimentti" in report
    assert "Fundamentti" in report
```

- [ ] **Step 2: Aja testit — varmista FAIL**

```bash
pytest tests/telegram_bot/test_formatter.py -v
```

- [ ] **Step 3: Toteuta formatter.py**

```python
# telegram_bot/formatter.py
from __future__ import annotations
from datetime import datetime

DISCLAIMER = "⚠️ Tämä on AI:n tuottama analyysi, ei sijoitussuositus."

DECISION_MAP = {
    "buy":  "OSTA",
    "sell": "MYY",
    "hold": "PIDÄ",
}

DECISION_EMOJI = {
    "OSTA": "🟢",
    "MYY":  "🔴",
    "PIDÄ": "🟡",
}


def parse_decision(raw: str) -> str:
    """Muuntaa upstream BUY/SELL/HOLD → OSTA/MYY/PIDÄ."""
    first = raw.strip().split()[0].lower().rstrip("-,:.")
    return DECISION_MAP.get(first, "PIDÄ")


def format_finnish_price(price: float) -> str:
    """1234.56 → '1 234,56 €'"""
    formatted = f"{price:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formatted} €"


def format_summary(state: dict, current_price: float | None = None) -> str:
    """Lyhyt yhteenveto Telegram-viestiksi."""
    ticker_raw = state.get("company_of_interest", "?")
    ticker = ticker_raw.replace(".HE", "")
    date_str = state.get("trade_date", datetime.now().strftime("%Y-%m-%d"))
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        date_fi = d.strftime("%d.%m.%Y")
    except ValueError:
        date_fi = date_str

    raw_decision = state.get("final_trade_decision", "")
    suositus = parse_decision(raw_decision)
    emoji = DECISION_EMOJI.get(suositus, "⬜")
    price_str = format_finnish_price(current_price) if current_price else "—"

    plan = state.get("trader_investment_plan", "")
    lyhyt = plan[:200].strip()
    if len(plan) > 200:
        lyhyt += "…"

    lines = [
        f"📊 *{ticker}* ({ticker_raw}) — {date_fi}",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"{emoji} *SUOSITUS: {suositus}*",
        f"💰 Kurssi: {price_str}",
        "",
        f"📝 _{lyhyt}_",
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines)


def format_full_report(state: dict) -> str:
    """Koko raportti kaikilla agenttien tuloksilla."""
    ticker_raw = state.get("company_of_interest", "?")
    ticker = ticker_raw.replace(".HE", "")
    date_str = state.get("trade_date", "")
    raw_decision = state.get("final_trade_decision", "")
    suositus = parse_decision(raw_decision)
    emoji = DECISION_EMOJI.get(suositus, "⬜")

    sections = [
        f"📊 *{ticker} — Täysi analyysi* ({date_str})",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"{emoji} *Lopullinen suositus: {suositus}*",
        "",
        "📈 *Tekninen analyysi*",
        state.get("market_report", "—")[:800],
        "",
        "💬 *Sentimenttianalyysi*",
        state.get("sentiment_report", "—")[:800],
        "",
        "📰 *Uutisanalyysi*",
        state.get("news_report", "—")[:800],
        "",
        "📋 *Fundamenttianalyysi*",
        state.get("fundamentals_report", "—")[:800],
        "",
        "⚖️ *Kaupankäyntipäätös*",
        state.get("trader_investment_plan", "—")[:600],
        "",
        "🛡 *Riskiarvio*",
        state.get("investment_plan", "—")[:400],
        "",
        DISCLAIMER,
    ]
    return "\n".join(sections)
```

- [ ] **Step 4: Aja testit — varmista PASS**

```bash
pytest tests/telegram_bot/test_formatter.py -v
```

Odotettu: kaikki 9 testiä vihreänä.

- [ ] **Step 5: Commit**

```bash
git add telegram_bot/formatter.py tests/telegram_bot/test_formatter.py
git commit -m "feat: telegram-botin tulosten formatointi"
```

---

## Task 4: progress.py + testit

LangChain `BaseCallbackHandler` joka seuraa agenttitilamuutoksia. `_build_progress_message` on puhdas funktio — täysin testattavissa ilman Telegram-riippuvuutta.

**Files:**
- Create: `telegram_bot/progress.py`
- Create: `tests/telegram_bot/test_progress.py`

- [ ] **Step 1: Kirjoita epäonnistuvat testit**

```python
# tests/telegram_bot/test_progress.py
from telegram_bot.progress import _build_progress_message, ALL_STAGES

def test_build_progress_empty():
    msg = _build_progress_message("NOKIA", completed=[], current=None)
    assert "NOKIA" in msg
    for stage in ALL_STAGES:
        assert f"⏳ {stage}" in msg

def test_build_progress_one_completed():
    msg = _build_progress_message("NOKIA", completed=["Fundamenttianalyysi"], current=None)
    assert "✅ Fundamenttianalyysi" in msg
    assert "⏳ Tekninen analyysi" in msg

def test_build_progress_current_stage():
    msg = _build_progress_message("NOKIA", completed=[], current="Sentimenttianalyysi")
    assert "🔄 Sentimenttianalyysi käynnissä..." in msg

def test_build_progress_mixed():
    msg = _build_progress_message(
        "NOKIA",
        completed=["Fundamenttianalyysi", "Sentimenttianalyysi"],
        current="Uutisanalyysi",
    )
    assert "✅ Fundamenttianalyysi" in msg
    assert "✅ Sentimenttianalyysi" in msg
    assert "🔄 Uutisanalyysi käynnissä..." in msg
    assert "⏳ Tekninen analyysi" in msg
```

- [ ] **Step 2: Aja testit — varmista FAIL**

```bash
pytest tests/telegram_bot/test_progress.py -v
```

- [ ] **Step 3: Toteuta progress.py**

```python
# telegram_bot/progress.py
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
        """
        Args:
            ticker:   Osakkeen tunnus näytölle (esim. "NOKIA")
            loop:     Pääasynkroninen event loop
            edit_fn:  Async coroutine: async def edit_fn(text: str) -> None
        """
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
```

- [ ] **Step 4: Aja testit — varmista PASS**

```bash
pytest tests/telegram_bot/test_progress.py -v
```

Odotettu: kaikki 4 testiä vihreänä.

- [ ] **Step 5: Commit**

```bash
git add telegram_bot/progress.py tests/telegram_bot/test_progress.py
git commit -m "feat: LangChain progress-callback + testit"
```

---

## Task 5: omxh.py + task_runner.py

**Files:**
- Create: `telegram_bot/omxh.py`
- Create: `telegram_bot/task_runner.py`
- Create: `tests/telegram_bot/test_ticker_validation.py`

**Tärkeää:** `task_runner.py` ei sisällä `asyncio.Lock`:ia — se kuuluu `handlers.py`:ään. Ei `os.chdir()`:iä — käytetään absoluuttisia polkuja.

- [ ] **Step 1: Kirjoita ticker-validointitestit**

```python
# tests/telegram_bot/test_ticker_validation.py
from unittest.mock import patch, MagicMock
from telegram_bot.omxh import validate_ticker

def test_validate_ticker_known_alias():
    mock_info = MagicMock()
    mock_info.last_price = 4.23
    with patch("telegram_bot.omxh.yf.Ticker") as mock_yf:
        mock_yf.return_value.fast_info = mock_info
        result = validate_ticker("NOKIA")
    assert result == "NOKIA.HE"

def test_validate_ticker_invalid_returns_none():
    mock_info = MagicMock()
    mock_info.last_price = None
    with patch("telegram_bot.omxh.yf.Ticker") as mock_yf:
        mock_yf.return_value.fast_info = mock_info
        result = validate_ticker("HÖLYNPÖLY123")
    assert result is None

def test_validate_ticker_already_has_he_suffix():
    mock_info = MagicMock()
    mock_info.last_price = 4.23
    with patch("telegram_bot.omxh.yf.Ticker") as mock_yf:
        mock_yf.return_value.fast_info = mock_info
        result = validate_ticker("NOKIA.HE")
    assert result == "NOKIA.HE"
```

- [ ] **Step 2: Aja testit — varmista FAIL**

```bash
pytest tests/telegram_bot/test_ticker_validation.py -v
```

- [ ] **Step 3: Toteuta omxh.py**

```python
# telegram_bot/omxh.py
"""Ohut wrapper ticker-validoinnille ja hinnan haulle."""
import logging
import yfinance as yf
from tradingagents.dataflows.omxh_utils import get_omxh_current_price, resolve_ticker

logger = logging.getLogger(__name__)


def get_current_price(ticker: str) -> float | None:
    """Hakee viimeisimmän kurssin EUR. Palauttaa None virhetilanteessa."""
    try:
        return get_omxh_current_price(ticker)
    except Exception as e:
        logger.warning(f"Hinnan haku epäonnistui {ticker}: {e}")
        return None


def validate_ticker(ticker: str) -> str | None:
    """
    Validoi ticker Yahoo Financesta ennen analyysin käynnistystä.
    Palauttaa Yahoo Finance -tunnuksen (esim. NOKIA.HE) tai None jos ei löydy.
    """
    try:
        yf_ticker = resolve_ticker(ticker)
        info = yf.Ticker(yf_ticker).fast_info
        if info.last_price and info.last_price > 0:
            return yf_ticker
        return None
    except Exception as e:
        logger.warning(f"Ticker-validointi epäonnistui {ticker}: {e}")
        return None
```

- [ ] **Step 4: Aja testit — varmista PASS**

```bash
pytest tests/telegram_bot/test_ticker_validation.py -v
```

- [ ] **Step 5: Toteuta task_runner.py**

```python
# telegram_bot/task_runner.py
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
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Callable, Awaitable
import asyncio

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.finnish_config import get_finnish_config
from telegram_bot.progress import AnalysisProgressCallback
from telegram_bot.formatter import format_summary, format_full_report
from telegram_bot.omxh import get_current_price

logger = logging.getLogger(__name__)

# Projektin juuri absoluuttisena polkuna (2 tasoa ylöspäin telegram_bot/:sta)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Yksi executor — max_workers=1 koska handlers.py:n Lock estää rinnakkaisajot
_executor = ThreadPoolExecutor(max_workers=1)

# Analyysin timeout sekunteina (10 minuuttia)
ANALYSIS_TIMEOUT_SEC = 600


def _sync_run_analysis(ticker: str, callback: AnalysisProgressCallback) -> dict:
    """
    Synkroninen funktio joka ajetaan threadissa.
    Uusi TradingAgentsGraph per pyyntö (instanssi on tilallinen — ei jaeta).
    """
    config = get_finnish_config({
        "results_dir": os.path.join(_PROJECT_ROOT, "results"),
    })
    graph = TradingAgentsGraph(config=config, callbacks=[callback], debug=False)
    trade_date = str(date.today())
    final_state, decision = graph.propagate(ticker, trade_date)
    final_state["_decision_raw"] = decision
    return final_state


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

    final_state = await asyncio.wait_for(
        loop.run_in_executor(_executor, _sync_run_analysis, ticker, callback),
        timeout=ANALYSIS_TIMEOUT_SEC,
    )

    current_price = await loop.run_in_executor(None, get_current_price, ticker)
    summary = format_summary(final_state, current_price=current_price)
    full_report = format_full_report(final_state)
    return summary, full_report
```

- [ ] **Step 6: Commit**

```bash
git add telegram_bot/omxh.py telegram_bot/task_runner.py tests/telegram_bot/test_ticker_validation.py
git commit -m "feat: omxh ticker-validointi ja task_runner timeout-suojauksella"
```

---

## Task 6: handlers.py + testit

**Tärkeää:** `asyncio.Lock` luodaan tässä tiedostossa — ei tuoda `task_runner`:sta.

**Files:**
- Create: `telegram_bot/handlers.py`
- Create: `tests/telegram_bot/test_handlers.py`

- [ ] **Step 1: Kirjoita epäonnistuvat testit**

```python
# tests/telegram_bot/test_handlers.py
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytest_plugins = ("pytest_asyncio",)

# Apufunktio mock-Updaten luomiseen
def make_update(user_id: int, args: list[str]):
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = "testuser"
    update.message.reply_text = AsyncMock(return_value=MagicMock(
        message_id=42,
        edit_text=AsyncMock(),
        delete=AsyncMock(),
    ))
    context = MagicMock()
    context.args = args
    return update, context

@pytest.mark.asyncio
async def test_handler_rejects_unknown_user():
    """Tuntematonta käyttäjää ei vastaukseen."""
    with patch("telegram_bot.handlers.is_allowed", return_value=False):
        from telegram_bot.handlers import analysoi_command
        update, context = make_update(user_id=999, args=["NOKIA"])
        await analysoi_command(update, context)
    update.message.reply_text.assert_not_called()

@pytest.mark.asyncio
async def test_handler_missing_args():
    """Ilman argumenttia näytetään käyttöohje."""
    with patch("telegram_bot.handlers.is_allowed", return_value=True):
        from telegram_bot.handlers import analysoi_command
        update, context = make_update(user_id=42, args=[])
        await analysoi_command(update, context)
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args[0][0]
    assert "/analysoi" in call_args

@pytest.mark.asyncio
async def test_handler_invalid_ticker():
    """Tuntematon ticker näyttää virheviestin."""
    with patch("telegram_bot.handlers.is_allowed", return_value=True), \
         patch("telegram_bot.handlers.validate_ticker", return_value=None):
        from telegram_bot.handlers import analysoi_command
        update, context = make_update(user_id=42, args=["HÖLYNPÖLY"])
        await analysoi_command(update, context)
    # Pitäisi olla kutsuttu enemmän kuin kerran (ensin "Tarkistetaan...", sitten virhe)
    assert update.message.reply_text.call_count >= 2

@pytest.mark.asyncio
async def test_handler_lock_busy():
    """Jos Lock on varattuna, näytetään 'jo käynnissä' -viesti."""
    from telegram_bot import handlers
    # Simuloi varattua lockia
    await handlers.analysis_lock.acquire()
    try:
        with patch("telegram_bot.handlers.is_allowed", return_value=True), \
             patch("telegram_bot.handlers.validate_ticker", return_value="NOKIA.HE"):
            update, context = make_update(user_id=42, args=["NOKIA"])
            await handlers.analysoi_command(update, context)
        last_call = update.message.reply_text.call_args[0][0]
        assert "käynnissä" in last_call
    finally:
        handlers.analysis_lock.release()
```

- [ ] **Step 2: Aja testit — varmista FAIL**

```bash
pytest tests/telegram_bot/test_handlers.py -v
```

- [ ] **Step 3: Toteuta handlers.py**

```python
# telegram_bot/handlers.py
from __future__ import annotations
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from telegram_bot.whitelist import is_allowed
from telegram_bot.omxh import validate_ticker
from telegram_bot.task_runner import run_analysis

logger = logging.getLogger(__name__)

# Globaali lukko — estää samanaikaiset analyysit
# Omistetaan handlers.py:ssä: Lock on handler-tason logiikkaa, ei task_runner-tason
analysis_lock = asyncio.Lock()

# Tallennetaan koko raportit muistiin inline-nappia varten
# { message_id: full_report_text }
# Huom: Kasvaa rajattomasti pitkässä ajossa — riittää suljetulle ryhmälle MVP:ssä
_full_reports: dict[int, str] = {}


async def analysoi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/analysoi [TICKER] -komennon käsittelijä."""
    user_id = update.effective_user.id

    # 1. Whitelist — hiljaisuus tuntemattomille, loki serverille
    if not is_allowed(user_id):
        logger.warning(f"Whitelist-esto: {user_id} (@{update.effective_user.username})")
        return

    # 2. Argumenttitarkistus
    args = context.args
    if not args:
        await update.message.reply_text("Käyttö: /analysoi [OSAKE]\nEsim: /analysoi NOKIA")
        return

    raw_ticker = args[0].upper().strip()

    # 3. Lockki — estä rinnakkainen ajo
    if analysis_lock.locked():
        await update.message.reply_text("⏳ Analyysi on jo käynnissä. Odota tulosta.")
        return

    # 4. Ticker-validointi Yahoo Financesta
    await update.message.reply_text(f"🔍 Tarkistetaan osake {raw_ticker}...")
    yf_ticker = validate_ticker(raw_ticker)
    if yf_ticker is None:
        await update.message.reply_text(
            f"❌ En löydä osaketta *{raw_ticker}*\n"
            f"Kokeile esim. /analysoi NOKIA tai /analysoi NESTE",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # 5. Progress-viesti
    progress_msg = await update.message.reply_text(
        f"📊 Analysoin: *{raw_ticker}*\n━━━━━━━━━━━━━━━━━━━━━\n⏳ Aloitetaan...",
        parse_mode=ParseMode.MARKDOWN,
    )

    async def edit_progress(text: str) -> None:
        try:
            await progress_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass

    # 6. Aja analyysi lukolla — käsittele timeout erikseen
    async with analysis_lock:
        try:
            summary, full_report = await run_analysis(yf_ticker, edit_progress)
        except asyncio.TimeoutError:
            logger.warning(f"Analyysi timeout: {yf_ticker}")
            await progress_msg.edit_text(
                "⏳ Analyysi kestää odotettua kauemmin — lähetan tuloksen kun valmis."
            )
            return
        except Exception as e:
            logger.error(f"Analyysi epäonnistui {yf_ticker}: {e}", exc_info=True)
            await progress_msg.edit_text(
                "❌ Analyysi epäonnistui. Yritä hetken kuluttua uudelleen."
            )
            return

    # 7. Lähetä tulos + [📄 Koko raportti] -nappi
    result_msg = await update.message.reply_text(
        summary,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📄 Koko raportti", callback_data=f"raportti:{raw_ticker}")
        ]]),
    )
    _full_reports[result_msg.message_id] = full_report
    await progress_msg.delete()


async def full_report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """[📄 Koko raportti] -napin käsittelijä."""
    query = update.callback_query
    await query.answer()

    if not is_allowed(query.from_user.id):
        return

    full_report = _full_reports.get(query.message.message_id)
    if not full_report:
        await query.message.reply_text(
            "❌ Raportti ei ole enää saatavilla. Aja /analysoi uudelleen."
        )
        return

    # Jaa 4000 merkin palasiin (Telegram max 4096)
    LIMIT = 4000
    for chunk in [full_report[i:i+LIMIT] for i in range(0, len(full_report), LIMIT)]:
        await query.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
```

- [ ] **Step 4: Aja testit — varmista PASS**

```bash
pytest tests/telegram_bot/test_handlers.py -v
```

Odotettu: kaikki 4 testiä vihreänä.

- [ ] **Step 5: Commit**

```bash
git add telegram_bot/handlers.py tests/telegram_bot/test_handlers.py
git commit -m "feat: /analysoi-käsittelijä (whitelist, lock, timeout) + testit"
```

---

## Task 7: bot.py (entry point)

**Files:**
- Create: `telegram_bot/bot.py`
- Create: `BOTTI.md`

- [ ] **Step 1: Toteuta bot.py**

```python
# telegram_bot/bot.py
"""
KauppaAgentit Telegram-botti — entry point.

Käynnistys projektin juuresta:
    python -m telegram_bot.bot
"""
from __future__ import annotations
import logging
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from telegram_bot.handlers import analysoi_command, full_report_callback

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN puuttuu .env-tiedostosta!")

    whitelist = os.getenv("TELEGRAM_WHITELIST", "")
    if not whitelist.strip():
        logger.warning("TELEGRAM_WHITELIST on tyhjä — kukaan ei pysty käyttämään bottia!")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("analysoi", analysoi_command))
    app.add_handler(CallbackQueryHandler(full_report_callback, pattern=r"^raportti:"))

    logger.info("🤖 KauppaAgentit-botti käynnistyy...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Luo BOTTI.md**

```bash
cat > BOTTI.md << 'EOF'
# KauppaAgentit Telegram-botti

## Käynnistys

1. Hanki bot token: Telegram → @BotFather → /newbot
2. Hanki oma Telegram-ID: Telegram → @userinfobot
3. Lisää .env-tiedostoon:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
   TELEGRAM_WHITELIST=123456789
   ANTHROPIC_API_KEY=sk-ant-...
   ```
4. Käynnistä projektin juuresta:
   ```bash
   python -m telegram_bot.bot
   ```

## Komennot

| Komento | Kuvaus |
|---------|--------|
| `/analysoi NOKIA` | Täysi osakeanalyysi (kestää 1–5 min) |

## Osakeesimerkkejä (OMXH)

Nokia: `NOKIA`, Nordea: `NORDEA`, Neste: `NESTE`, KONE: `KONE`, UPM: `UPM`
EOF
```

- [ ] **Step 3: Commit**

```bash
git add telegram_bot/bot.py BOTTI.md
git commit -m "feat: telegram-botin entry point ja käynnistysohje"
```

---

## Task 8: Aja kaikki yksikkötestit

- [ ] **Step 1: Aja koko testisuiteesta**

```bash
pytest tests/telegram_bot/ -v
```

Odotettu: kaikki 23 testiä vihreänä (6 + 9 + 4 + 4).

- [ ] **Step 2: Jos testejä epäonnistuu — tutki virheilmoitus ennen korjausta**

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "test: kaikki telegram-bot yksikkötestit läpi"
```

---

## Task 9: Manuaalinen integraatiotesti

Vaatii oikeat API-avaimet. Tee kehitysympäristössä.

- [ ] **Step 1: Varmista .env on täytetty**

```bash
grep -E "TELEGRAM_BOT_TOKEN|ANTHROPIC_API_KEY|TELEGRAM_WHITELIST" .env
```

Odotettu: kaikki kolme riviä näkyvät (ei `your_..._here` -arvoja).

- [ ] **Step 2: Käynnistä botti projektin juuresta**

```bash
python -m telegram_bot.bot
```

Odotettu loki: `🤖 KauppaAgentit-botti käynnistyy...`

- [ ] **Step 3: Testaa Telegramissa onnistunut tapaus**

Lähetä: `/analysoi NOKIA`

Odotettu:
1. "🔍 Tarkistetaan osake NOKIA..."
2. Progress-viesti ilmestyy ja päivittyy agentti kerrallaan
3. Lopullinen yhteenveto: OSTA/PIDÄ/MYY + [📄 Koko raportti]
4. Napin painaminen näyttää koko raportin

- [ ] **Step 4: Testaa virhetilanteet**

- `/analysoi HÖLYNPÖLY123` → ❌ En löydä osaketta...
- `/analysoi NOKIA` uudelleen analyysin aikana → ⏳ Analyysi on jo käynnissä...
- `/analysoi` (ilman argumenttia) → käyttöohje

- [ ] **Step 5: Lopullinen commit**

```bash
git add -A
git commit -m "feat: KauppaAgentit Telegram-botti valmis (Vaihe 1)"
```

---

## Huomioita toteutukselle

- **Projektin juuri:** Aja aina `python -m telegram_bot.bot` projektin juuresta. `task_runner.py` käyttää absoluuttista polkua `_PROJECT_ROOT` — ei `os.chdir()`.
- **Lock-omistajuus:** `asyncio.Lock` on `handlers.py`:ssä — ei tuoda `task_runner`:sta. Tämä on spec:n mukainen arkkitehtuuri.
- **Telegram-merkkirajoitus:** Viesti max 4096 merkkiä — `full_report_callback` jakaa pitkät raportit automaattisesti.
- **ParseMode:** Käytetään `MARKDOWN` (ei `MARKDOWN_V2`). Jos analyysin teksteissä on erikoismerkkejä jotka rikkovat parsimisen, poista `parse_mode`.
- **B→C migraatio:** Muuta vain `task_runner.py` — kaikki muu pysyy.
- **`_full_reports` muisti:** Kasvaa rajattomasti pitkässä ajossa. Hyväksyttävä MVP:ssä suljetulle ryhmälle — lisää TTL/eviction myöhemmin tarvittaessa.
