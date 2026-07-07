# KauppaAgentit

Suomenkielinen forkki [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) -projektista. Repo painottaa OMXH-kayttoa, suomalaisia uutislahteita, suomenkielisia agenttipromptteja, Telegram-kayttoa ja demoautotraderia.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-green.svg)](https://python.org)
[![Upstream: TradingAgents](https://img.shields.io/badge/Upstream-TradingAgents-orange.svg)](https://github.com/TauricResearch/TradingAgents)

## Vastuuvapautus

Tama on AI:n tuottama analyysi, ei sijoitussuositus. Tee sijoituspaatokset oman harkintasi mukaan.

KauppaAgentit on tutkimus- ja oppimiskayttoon tarkoitettu analyysityokalu. Projekti ei ole Finanssivalvonnan valvomaa sijoitusneuvontaa eika sita tule kayttaa henkilokohtaisena sijoitusneuvona.

## Mita tassa forkissa on

- suomenkieliset promptit `fi_prompts/`-hakemistossa
- OMXH- ja pohjoismaatuki `tradingagents/dataflows/omxh_utils.py`-tiedostossa
- suomalaiset uutislahteet ja ticker-resoluutio
- Telegram-botti analyysille, salkulle ja halytyksille
- PostgreSQL/SQLite-pohjainen tallennus analyysi- ja autotrader-ajojen seurantaan
- demoautotrader `autotrader/`-pakettina Saxo SIM -polulle

## Projektirakenne

```text
TradingAgents-Finnish/
|- tradingagents/   # upstream-pohjainen analyysiydin
|- fi_prompts/      # suomenkieliset promptit
|- cli/             # komentoriviliittyma
|- telegram_bot/    # Telegram-botti
|- autotrader/      # demoautotrader ja broker-abstraktiot
|- db/              # skeema ja migraatiot
|- docs/            # kaytto- ja deploy-ohjeet
`- tests/           # testit
```

## Asennus

```bash
git clone https://github.com/Murtsi/TradingAgents-Finnish.git
cd TradingAgents-Finnish
conda create -n tradingagents python=3.13
conda activate tradingagents
pip install -e ".[dev]"
```

Vaihtoehtoisesti voit kayttaa Dockeria:

```bash
cp .env.example .env
docker compose run --rm tradingagents
```

## Ympäristömuuttujat

Kopioi `.env.example` pohjaksi:

```bash
cp .env.example .env
```

Tyypillisimmat avaimet:

```env
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
OPENROUTER_API_KEY=...
ALPHA_VANTAGE_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_WHITELIST=123456789
DATABASE_URL=postgresql://...
```

Autotraderille:

```env
BROKER=saxo
SAXO_ENV=sim
SAXO_TOKEN=...
AUTOTRADER_DRY_RUN=1
```

## Kaytto

Komentorivi:

```bash
python -m cli.main
python -m cli.main fi
```

Telegram-botti:

```bash
python -m telegram_bot.bot
```

Autotrader kerran ajettuna:

```bash
python -m autotrader.engine --once --dry-run --date 2026-07-07
```

Ajastettu worker:

```bash
python -m autotrader.scheduler
```

## Python-esimerkki

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.finnish_config import get_finnish_config

config = get_finnish_config({
    "llm_provider": "anthropic",
    "deep_think_llm": "claude-haiku-4-5-20251001",
    "quick_think_llm": "claude-haiku-4-5-20251001",
})

graph = TradingAgentsGraph(debug=False, config=config)
final_state, decision = graph.propagate("NOKIA", "2026-07-07")
print(decision)
```

## Kehitys ja testaus

```bash
pytest -q
ruff check .
python -m compileall tradingagents telegram_bot autotrader
```

GitHub Actions ajaa testit ja linttauksen automaattisesti `main`-haaralle ja pull requesteille.

## Deploy

Railway-ohjeet:

- [autotrader_railway.md](docs/autotrader_railway.md)
- [saxo_sim_setup.md](docs/saxo_sim_setup.md)

Paikallinen parity-ymparisto loytyy [docker-compose.yml](docker-compose.yml)-tiedostosta.

## Lähtöprojekti

Tama repositorio pohjautuu [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) -projektiin. Tavoite on sailyttaa upstream-yhteensopivuus mahdollisimman pitkalle samalla kun suomispesifinen logiikka pidetaan omissa tiedostoissaan tai rajatuissa fork-muutoksissa.
