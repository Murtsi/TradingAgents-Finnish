# Design: KauppaAgentit Telegram-botti

**Päivämäärä:** 2026-03-24
**Status:** Hyväksytty (v1.1 — spec review korjaukset)
**Projekti:** KauppaAgentit (TradingAgents Suomi-fork)

---

## Tavoite

Lisätä Telegram-botti KauppaAgentit-projektiin käyttöliittymäksi suomalaiselle kuluttajalle. Käyttäjä lähettää `/analysoi NOKIA` ja saa täyden multi-agent LLM-analyysin tuloksen suomeksi Telegramin kautta.

---

## Käyttötapaukset

- **Käyttäjät:** Pieni suljettu ryhmä (whitelist), laajennettavissa myöhemmin
- **Ensisijainen komento:** `/analysoi [TICKER]` (esim. `/analysoi NOKIA`, `/analysoi NESTE`)
- **Laajennus myöhemmin:** `/hinta`, `/historia`, `/seuraa` — ei tässä versiossa

---

## Arkkitehtuuri

### Tiedostorakenne

```
telegram_bot/
├── bot.py              # Entry point — käynnistää botin
├── handlers.py         # /analysoi-komennon käsittely
├── task_runner.py      # Analyysin ajaminen (B→C migraatiopiste)
├── formatter.py        # Analyysin muotoilu Telegram-viestiksi
├── whitelist.py        # Sallitut käyttäjät
└── progress.py         # Live-päivitykset agenttitiloista
```

### Data flow

```
Käyttäjä: /analysoi NOKIA
    │
    ▼
handlers.py
    ├── Tarkista whitelist (whitelist.py) — tuntematon käyttäjä → hiljaisuus + serverlog
    ├── Validoi ticker: resolve_ticker() + yfinance-tarkistus ennen analyysiä
    ├── Tarkista globaali asyncio.Lock — jos varattu → "⏳ Analyysi käynnissä"
    ├── Lähetä "⏳ Aloitan analyysin..." -viesti
    │
    ▼
task_runner.py  (ainoa tiedosto joka muuttuu B→C)
    └── asyncio.run_in_executor(ThreadPoolExecutor)
            │
            ▼
        AnalysisCallback (progress.py) rekisteröidään LangChain-callbackiksi
        TradingAgentsGraph(config=FINNISH_CONFIG) — uusi instanssi per pyyntö
        graph.propagate(ticker, date)
            │  (on_llm_start / on_tool_start → progress.py)
            ▼
        progress.py päivittää Telegram-viestiä reaaliajassa
            │
            ▼
formatter.py
    ├── Lyhyt yhteenveto (suositus, kurssi, top riskit)
    └── Täysi raportti tallennetaan muistiin (callback_data inline-napilla)
            │
            ▼
Telegram: yhteenveto + [📄 Koko raportti]

```

---

## Tekninen toteutus

### Kirjasto

`python-telegram-bot >= 20.0` — async-native, tukee inline-nappeja ja viestin editointia.

### Vaihtoehto B (nyt) vs C (myöhemmin)

**task_runner.py** on ainoa tiedosto joka muuttuu. Ulkoinen rajapinta pysyy samana:

```python
# Vaihtoehto B — asyncio + ThreadPoolExecutor (nyt)
async def run_analysis(ticker: str, progress_cb) -> AnalysisResult:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _sync_run, ticker, progress_cb)

# Vaihtoehto C — Celery (myöhemmin)
# Oikea tapa: poll Celery AsyncResult asynkronisesti run_in_executor:lla
# asyncio.wrap_future() EI toimi Celery AsyncResult:n kanssa (se ei ole
# concurrent.futures.Future). Migraatiossa käytetään run_in_executor + polling.
async def run_analysis(ticker: str, progress_cb) -> AnalysisResult:
    loop = asyncio.get_event_loop()
    task = analyse_ticker.delay(ticker)
    return await loop.run_in_executor(None, task.get)  # blocking get threadissa
```

Kaikki muu (handlers, formatter, whitelist, progress) pysyy muuttumattomana.

### TradingAgentsGraph — instanssinhallinta

**Uusi instanssi per pyyntö.** `TradingAgentsGraph` on tilallinen (`self.curr_state`, `self.ticker`, `self.log_states_dict`) — jaettu instanssi korruptoisi tilan samanaikaisissa pyynnöissä. Alustamiskulut (~1–2 s) ovat hyväksyttäviä suhteessa 1–5 min analyysiaikaan.

### Samanaikaisuuden hallinta

```python
# handlers.py — globaali lukko
_analysis_lock = asyncio.Lock()

async def analysoi_handler(update, context):
    if _analysis_lock.locked():
        await update.message.reply_text("⏳ Analyysi on jo käynnissä. Odota tulosta.")
        return
    async with _analysis_lock:
        await run_analysis(...)
```

Yksi globaali `asyncio.Lock` on oikea ratkaisu pienelle suljetulle ryhmälle. Laajennettaessa per-käyttäjä-lukko lisätään myöhemmin.

### Progress callbacks — toteutus

`progress.py` toteuttaa LangChain `BaseCallbackHandler`:in. Analyysivaiheet tunnistetaan `on_llm_start`-tapahtuman `serialized["name"]`-kentästä, joka sisältää agentin nimen:

```python
VAIHEET = {
    "fundamentals": "Fundamenttianalyysi",
    "market":       "Tekninen analyysi",
    "social":       "Sentimenttianalyysi",
    "news":         "Uutisanalyysi",
    "bull":         "Bull-tutkija",
    "bear":         "Bear-tutkija",
    "trader":       "Kaupankäyntipäätös",
}

class AnalysisProgressCallback(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        name = serialized.get("name", "")
        for key, label in VAIHEET.items():
            if key in name.lower():
                asyncio.run_coroutine_threadsafe(
                    self._update_progress(label), self.loop
                )
                break
```

Jos agentti ei tue odotettua nimeä, edistymisviesti pysyy edellisessä tilassa — ei kaadu.

### Ticker-validointi

Validointi tapahtuu **ennen** analyysin käynnistystä kahdessa vaiheessa:

```python
# 1. Resolve ticker-muoto
yf_ticker = resolve_ticker(raw_input)  # esim. "nokia" → "NOKIA.HE"

# 2. Tarkista Yahoo Financesta että data on saatavilla (nopea kutsu)
info = yf.Ticker(yf_ticker).fast_info
if not info.get("lastPrice"):
    await update.message.reply_text(f"❌ En löydä osaketta '{raw_input}'...")
    return
```

Tämä estää "hiljaisen epäonnistumisen" jossa virhe tulisi vasta syvältä graph-ajon sisältä.

### Käyttöliittymä — analyysin edistyminen

```
📊 Analysoin: NOKIA (NOKIA.HE)
━━━━━━━━━━━━━━━━━━━━━
✅ Fundamenttianalyysi valmis
✅ Sentimenttianalyysi valmis
🔄 Uutisanalyysi käynnissä...
⏳ Tekninen analyysi
⏳ Väittely (bull vs bear)
⏳ Kaupankäyntipäätös
⏱ Kulunut: 1 min 23 s
```

### Lopullinen tulosviesti (V1)

```
📊 NOKIA (NOKIA.HE) — 24.3.2026
━━━━━━━━━━━━━━━━━━━━━
🟢 SUOSITUS: OSTA
📈 Luottamustaso: Keskisuuri
💰 Kurssi: 4,23 €

📝 Yhteenveto:
[2–3 lausetta salkunhoitajalta]

⚠️ Top riskit:
• Kilpailu 5G-markkinoilla
• USD/EUR-kurssivaihtelut

[📄 Koko raportti]

⚠️ Tämä on AI:n tuottama analyysi, ei sijoitussuositus.
```

**Huom:** `[🔄 Päivitä]` -nappi on poistettu V1:stä. Lisätään myöhemmin kun `/hinta`-komento toteutetaan — semantiikka ja samanaikaisuuslogiikka määritellään silloin.

---

## Virheenkäsittely

| Tilanne | Käyttäjälle | Serverlog |
|---------|------------|-----------|
| Tuntematon ticker | ❌ En löydä osaketta 'X'. Kokeile esim. /analysoi NOKIA | WARNING |
| Käyttäjä ei whitelistillä | (hiljaisuus) | WARNING: unauthorized user {id} |
| Analyysi jo käynnissä | ⏳ Analyysi on jo käynnissä. Odota tulosta. | INFO |
| API-virhe / poikkeus | ❌ Analyysi epäonnistui. Yritä hetken kuluttua. | ERROR + stack trace |
| Timeout (>10 min) | ⏳ Analyysi kestää odotettua kauemmin, lähetan kun valmis. | WARNING |

Whitelist-esto logitetaan aina serverille (tuntematon käyttäjä-ID) vaikka käyttäjä ei saa vastausta.

---

## Ympäristömuuttujat

Lisätään `.env`-tiedostoon:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WHITELIST=123456789,987654321
```

- `TELEGRAM_BOT_TOKEN` — `@BotFather` → `/newbot`
- `TELEGRAM_WHITELIST` — käyttäjä-ID:t pilkulla (`@userinfobot` kertoo oman ID:n)

Botin käynnistyshakemiston tulee olla projektin juuri jotta `FINNISH_CONFIG["results_dir"]` kirjoittaa oikeaan paikkaan.

---

## Testaus

| Taso | Mitä testataan | API-kutsuja? |
|------|---------------|-------------|
| Yksikkötestit | whitelist, formatter, ticker-validointi, progress callback | Ei |
| Integraatiotesti | Yksi oikea ajo NOKIA.HE:llä — koko putki päästä päähän | Kyllä (kehityksessä) |

---

## Migraatiopolku B → C

1. Lisää `celery.py` + `docker-compose.yml` (Redis — jo `pyproject.toml`:ssa `redis>=6.2.0`)
2. Muuta `task_runner.py`: `run_in_executor` → Celery task + `run_in_executor(task.get)`
3. Kaikki muu pysyy muuttumattomana

Arvioitu migraatioaika: ~2–4 tuntia. Redis-client on jo projektiriippuvuuksissa.

---

## Riippuvuudet

```
python-telegram-bot>=20.0   # uusi
python-dotenv               # jo projektissa
yfinance                    # jo projektissa
```
