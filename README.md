# KauppaAgentit (TradingAgents-Finnish)

> **Fork of [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents)** — lokalisoitu ja laajennettu suomalaisille markkinoille (OMXH).

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-green.svg)](https://python.org)
[![Upstream: TradingAgents v0.2.2](https://img.shields.io/badge/Upstream-v0.2.2-orange.svg)](https://github.com/TauricResearch/TradingAgents)

---

## Mitä tämä projekti on?

**KauppaAgentit** on suomenkielinen laajennus TradingAgents-kehyksestä. Alkuperäinen projekti on monikansallinen LLM-pohjainen kaupankäyntijarjestelmä — tämä fork tuo sen lähemmäksi Suomea:

- **Suomenkieliset promptit** (`fi_prompts/`) — agentit ajattelevat ja vastaavat suomeksi
- **Telegram-botti** (`telegram_bot/`) — analysoi OMXH-osakkeita suoraan Telegramista
- **Suomalainen uutisvirtaus** — hakee dataa suomalaisista uutisahteista
- **PostgreSQL-tietokanta** (`db/`) — tallentaa analyysit ja tulokset
- **Arviointitulokset** (`eval_results/`) — backtesting-tulokset suomalaisilla osakkeilla

---

## Projektirakenne

```
TradingAgents-Finnish/
|-- tradingagents/        # Ydinjärjestelmä (upstream)
|-- fi_prompts/           # Suomenkieliset promptit agentteille
|-- telegram_bot/         # Telegram-botti (/analysoi NOKIA)
|-- db/                   # PostgreSQL-schema ja migraatiot
|-- eval_results/         # Backtesting-tulokset
|-- docs/superpowers/     # Tekninen dokumentaatio ja suunnitelmat
|-- cli/                  # Komentoriviliittymä
|-- tests/                # Testit
```

---

## Telegram-botti (KauppaAgentit)

Helpoin tapa käyttää tätä projektia on Telegram-botin kautta.

### Käynnistys

1. Hanki bot token: Telegram → `@BotFather` → `/newbot`
2. Hanki oma Telegram-ID: `@userinfobot`
3. Lisää `.env`-tiedostoon:

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_WHITELIST=123456789
ANTHROPIC_API_KEY=sk-ant-...
```

4. Käynnistä:

```bash
python -m telegram_bot.bot
```

### Komennot

| Komento | Kuvaus |
|---|---|
| `/analysoi NOKIA` | Täysi osakeanalyysi (1–5 min) |

### OMXH-esimerkkejä

| Yhtiö | Komento |
|---|---|
| Nokia | `/analysoi NOKIA` |
| Nordea | `/analysoi NORDEA` |
| Neste | `/analysoi NESTE` |
| KONE | `/analysoi KONE` |
| UPM | `/analysoi UPM` |

---

## Asennus (kehitysympäristö)

### 1. Kloonaa repositorio

```bash
git clone https://github.com/Murtsi/TradingAgents-Finnish.git
cd TradingAgents-Finnish
```

### 2. Luo virtuaaliympäristö

```bash
conda create -n tradingagents python=3.13
conda activate tradingagents
```

Tai `uv`-työkalulla:

```bash
uv sync
```

### 3. Asenna riippuvuudet

```bash
pip install -e .
# tai
pip install -r requirements.txt
```

### 4. API-avaimet

Kopioi `.env.example` → `.env` ja täytä avaimesi:

```bash
cp .env.example .env
```

Tuetut LLM-tarjoajat:

```env
OPENAI_API_KEY=...        # OpenAI (GPT)
GOOGLE_API_KEY=...        # Google (Gemini)
ANTHROPIC_API_KEY=...     # Anthropic (Claude)
XAI_API_KEY=...           # xAI (Grok)
OPENROUTER_API_KEY=...    # OpenRouter
ALPHA_VANTAGE_API_KEY=... # Alpha Vantage (markkinadata)
```

---

## CLI-käyttö

```bash
python -m cli.main
```

Valitse ticker, päivämäärä, LLM-tarjoaja ja analyysin syvyys interaktiivisessa valikossa.

---

## Python-käyttö

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "anthropic"   # openai, google, anthropic, xai, openrouter, ollama
config["deep_think_llm"] = "claude-opus-4"
config["quick_think_llm"] = "claude-haiku-4"
config["max_debate_rounds"] = 2

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NOKIA", "2026-03-24")
print(decision)
```

Katso kaikki asetukset: `tradingagents/default_config.py`

---

## Kehys (upstream)

KauppaAgentit perustuu TradingAgents-kehykseen, joka simuloi oikean kauppayhtiön dynamiikkaa useilla erikoistuneilla LLM-agentteilla:

| Agentti | Rooli |
|---|---|
| **Fundamenttianalyyytikko** | Yhtiön taloudellinen analyysi ja sisäinen arvo |
| **Sentimenttianalyytikko** | Sosiaalinen media ja markkinamieliala |
| **Uutisanalyytikko** | Globaalit uutiset ja makrotalous |
| **Tekninen analyytikko** | MACD, RSI ja kaaviokuviot |
| **Tutkijatiimi** | Bullish vs. bearish -väittely |
| **Kaupankävijä-agentti** | Päätöksenteko analyyseistä |
| **Riskienhallinta** | Portfolion riski ja volatiilisuus |
| **Portfoliopäällikkö** | Hyväksy/hylkää transaktiot |

> **Vastuuvapauslauseke:** Tämä järjestelmä on tarkoitettu tutkimuslkäyttöön. Se ei ole sijoitusneuvontaa. Kaupankäyntisuorituskyky vaihtelee mallista, laadusta ja markkinaolosuhteista riippuen.

---

## Testit

```bash
pytest tests/
```

---

## Upstream & lisenssi

Tämä projekti on forkattu [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) -repositoriosta (Apache 2.0).

Alkuperäinen tutkimusjulkaisu:

```bibtex
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
  title={TradingAgents: Multi-Agents LLM Financial Trading Framework},
  author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
  year={2025},
  eprint={2412.20138},
  archivePrefix={arXiv},
  url={https://arxiv.org/abs/2412.20138}
}
```