# Design: KauppaAgentit Telegram-botti

**Päivämäärä:** 2026-03-24
**Status:** Hyväksytty
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
    ├── Tarkista whitelist (whitelist.py)
    ├── Validoi ticker (omxh_utils.resolve_ticker)
    ├── Lähetä "⏳ Aloitan analyysin..." -viesti
    │
    ▼
task_runner.py
    └── asyncio.run_in_executor(ThreadPoolExecutor)
            │
            ▼
        TradingAgentsGraph.propagate(ticker, date)
            │  (LangGraph callbacks → progress.py)
            ▼
        progress.py editoi Telegram-viestiä reaaliajassa
            │
            ▼
formatter.py
    ├── Lyhyt yhteenveto (suositus, kurssi, top riskit)
    └── Täysi raportti (callback_data inline-napilla)
            │
            ▼
Telegram: yhteenveto + [📄 Koko raportti] [🔄 Päivitä]
```

---

## Tekninen toteutus

### Kirjasto

`python-telegram-bot >= 20.0` — async-native, tukee inline-nappeja ja viestin editointia.

### Vaihtoehto B (nyt) vs C (myöhemmin)

**task_runner.py** on ainoa tiedosto joka muuttuu:

```python
# Vaihtoehto B — asyncio + ThreadPoolExecutor
async def run_analysis(ticker: str, callback) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _sync_run, ticker, callback)

# Vaihtoehto C — Celery (myöhemmin, sama ulkoinen rajapinta)
async def run_analysis(ticker: str, callback) -> dict:
    task = analyse_ticker.delay(ticker)
    return await asyncio.wrap_future(task)
```

Kaikki muu (handlers, formatter, whitelist, progress) pysyy muuttumattomana.

### Käyttöliittymä — analyysiviestin eteneminen

```
📊 Analysoin: NOKIA (NOKIA.HE)
━━━━━━━━━━━━━━━━━━━━━
✅ Fundamenttianalyysi valmis
✅ Sentimenttianalyysi valmis
🔄 Uutisanalyysi käynnissä...
⏳ Tekninen analyysi
⏳ Väittely (bull vs bear)
⏳ Kaupankäyntipäätös
```

### Lopullinen tulosviesti

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

[📄 Koko raportti]  [🔄 Päivitä]

⚠️ Tämä on AI:n tuottama analyysi, ei sijoitussuositus.
```

---

## Virheenkäsittely

| Tilanne | Viesti käyttäjälle |
|---------|-------------------|
| Tuntematon ticker | ❌ En löydä osaketta 'X'. Kokeile esim. /analysoi NOKIA |
| Käyttäjä ei whitelistillä | (hiljaisuus — ei vastausta) |
| Analyysi jo käynnissä | ⏳ Analyysi on jo käynnissä. Odota tulosta. |
| API-virhe / poikkeus | ❌ Analyysi epäonnistui. Yritä hetken kuluttua uudelleen. |
| Timeout (>10 min) | ⏳ Analyysi kestää odotettua kauemmin, lähetan tuloksen kun valmis. |

---

## Ympäristömuuttujat

Lisätään `.env`-tiedostoon:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WHITELIST=123456789,987654321
```

- `TELEGRAM_BOT_TOKEN` — saadaan `@BotFather`-botilta Telegramissa (`/newbot`)
- `TELEGRAM_WHITELIST` — käyttäjä-ID:t pilkulla erotettuna (saadaan `@userinfobot`-botilta)

---

## Testaus

| Taso | Mitä testataan | API-kutsuja? |
|------|---------------|-------------|
| Yksikkötestit | whitelist, formatter, ticker-validointi | Ei |
| Integraatiotesti | Yksi oikea ajo NOKIA.HE:llä | Kyllä (kehityksessä) |

---

## Migraatiopolku B → C

Kun käyttäjämäärä kasvaa tai tarvitaan rinnakkaisajoja:

1. Lisää `celery.py` + `docker-compose.yml` (Redis)
2. Muuta `task_runner.py` — ainoastaan tämä tiedosto
3. Kaikki muu pysyy muuttumattomana

Arvioitu migraatioaika: ~2–4 tuntia.

---

## Riippuvuudet

```
python-telegram-bot>=20.0
python-dotenv           # jo projektissa
```

Ei uusia infra-riippuvuuksia vaihtoehto B:ssä.
