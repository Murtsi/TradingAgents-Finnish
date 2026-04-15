# KauppaAgentit

Fork of [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents), localized for the Helsinki Stock Exchange (OMXH).

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)

**Vastuuvapautus:** Tämä on tutkimus- ja oppimistarkoituksiin tehty työkalu. Se ei ole sijoitusneuvontaa. Sijoittamiseen liittyy aina riski pääoman menettämisestä.

---

## Mitä tämä on

KauppaAgentit ajaa sarjan LLM-pohjaisia agentteja, jotka analysoivat OMXH-osakkeita suomeksi. Upstream-kehys (TradingAgents) hoitaa agenttien orkestroinnin LangGraphin kautta — tämä fork lisää suomalaisen lokalisoinnin.

**Muutokset upstreamiin:**
- `fi_prompts/` — suomenkieliset system-promptit kaikille agentteille
- `tradingagents/dataflows/omxh_utils.py` — OMXH ticker-muunnokset, Yahoo Finance `.HE`-suffiksi
- `tradingagents/dataflows/finnish_news.py` — RSS-syötteet: IS Taloussanomat, HS Talous, YLE Talous, Nasdaq OMX Helsinki
- `tradingagents/finnish_config.py` — Suomi-konfiguraatio (EUR, OMXH, verokonteksti, Haiku oletuksena)
- `telegram_bot/` — Telegram-botti `/analysoi`-komennolla
- `db/` — PostgreSQL-schema analyysihistorialle

---

## Agenttipipeline

Agentit ajetaan järjestyksessä:

1. **Rinnakkain:** fundamenttianalyytikko, tekninen analyytikko, uutisanalyytikko, sentimenttianalyytikko
2. **Väittely:** bull-tutkija vs. bear-tutkija (`max_debate_rounds`, oletus 1)
3. **Päätös:** kauppias → riskienhallinta → salkunhoitaja → OSTA / PIDÄ / MYY

Kukin agentti lataa system-promptin `fi_prompts/`-hakemistosta.

---

## Asennus

```bash
git clone https://github.com/Murtsi/TradingAgents-Finnish.git
cd TradingAgents-Finnish
uv sync        # tai: pip install -e .
cp .env.example .env
# Täytä API-avaimet .env-tiedostoon
```

Vaaditut ympäristömuuttujat:

```env
ANTHROPIC_API_KEY=sk-ant-...       # tai OPENAI_API_KEY / GOOGLE_API_KEY
TELEGRAM_BOT_TOKEN=123456:...      # vain Telegram-bottia varten
TELEGRAM_WHITELIST=123456789       # pilkulla erotettu lista Telegram-käyttäjä-ID:istä
```

Valinnainen:
```env
ALPHA_VANTAGE_API_KEY=...          # vain jos käytät Alpha Vantage -datalähdettä
TEST_MODE=true                     # rajoittaa max_tokens=500, ~0.02–0.05 €/ajo
```

---

## Telegram-botti

```bash
python -m telegram_bot.bot
```

Komennot: `/analysoi NOKIA`

Tuetut tickerit: NOKIA, NORDEA, NESTE, KONE, UPM, SAMPO, KESKO ja muut OMXH-osakkeet.
Täydellinen lista: `tradingagents/dataflows/omxh_utils.py` → `OMXH_TICKERS`

Botti vaatii whitelist-tunnistautumisen (`TELEGRAM_WHITELIST`). Tuntemattomat käyttäjät
ohitetaan hiljaa (ei virheviestiä).

---

## CLI

```bash
python -m cli.main
```

Interaktiivinen valikko: ticker, päivämäärä, LLM-tarjoaja, analyysin syvyys.

---

## Python API

```python
from dotenv import load_dotenv
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.finnish_config import get_finnish_config

load_dotenv()

config = get_finnish_config()
ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NOKIA", "2026-03-24")
print(decision)
```

Kaikki konfiguraatioavaimet: `tradingagents/default_config.py`
Suomi-spesifiset asetukset: `tradingagents/finnish_config.py`

---

## Kustannusarvio

Yksi täysi analyysi (kaikki agentit, 1 väittelykierros):
- Claude Haiku: ~0,05–0,10 €
- Claude Sonnet: ~0,30–0,50 €

`TEST_MODE=true` rajoittaa max_tokens=500, jolloin kustannus on ~0,02–0,05 €/ajo.

---

## Testit

```bash
pytest tests/
```

---

## Rakenne

```
tradingagents/        upstream-ydinkoodi (muokattu minimiin)
fi_prompts/           suomenkieliset system-promptit
telegram_bot/         Telegram-botti
cli/                  komentoriviliittymä
db/                   PostgreSQL-schema ja migraatiot
tests/                testit
```

---

## Upstream-synkronointi

```bash
git fetch upstream
git merge upstream/main
```

Omat muutokset on merkitty `# FORK: Suomi-lokalisointi` upstream-tiedostoissa.
Uudet suomi-spesifiset tiedostot eivät muuta upstream-koodia.

---

## Lisenssi

Apache 2.0. Perustuu [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) -projektiin.

```bibtex
@misc{xiao2025tradingagents,
  title={TradingAgents: Multi-Agents LLM Financial Trading Framework},
  author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
  year={2025},
  eprint={2412.20138},
  archivePrefix={arXiv},
  url={https://arxiv.org/abs/2412.20138}
}
```