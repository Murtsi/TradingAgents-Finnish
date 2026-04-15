# KauppaAgentit

Suomenkielinen laajennus TradingAgents-kehyksestä Helsingin pörssin (OMXH) osakkeiden analysointiin.

> Tämä projekti perustuu [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) -kehykseen ja tuo siihen suomenkielisiä prompteja, OMXH-painotuksia sekä paikalliseen käyttöön sovitettuja komponentteja.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-green.svg)](https://python.org)
[![Upstream: TradingAgents](https://img.shields.io/badge/Upstream-TradingAgents-orange.svg)](https://github.com/TauricResearch/TradingAgents)

---

## Yleiskuva

KauppaAgentit on komentoriviltä käytettävä suomenkielinen toteutus TradingAgents-kehyksen ympärille. Projektin tarkoitus on helpottaa monen agentin LLM-pohjaisen analyysiputken käyttöä suomalaisessa markkinaympäristössä, erityisesti OMXH-yhtiöiden tarkastelussa.

Keskeiset painopisteet:

- suomenkieliset promptit ja analyysipolut
- komentorivikäyttö alkuperäisen projektin tapaan
- suomalaisiin lähteisiin sovitettu data- ja uutisvirta
- PostgreSQL-tallennus analyysituloksille
- arviointi- ja backtesting-ajot paikallisiin käyttötapauksiin

---

## Keskeiset ominaisuudet

- **Suomenkieliset promptit** (`fi_prompts/`) agenttien ohjaukseen ja analyysien tuottamiseen
- **Komentorivikäyttöliittymä** (`cli/`) interaktiiviseen käyttöön terminalissa
- **Tietokantakerros** (`db/`) analyysien ja tulosten tallennukseen
- **Arviointitulokset** (`eval_results/`) testiajojen ja vertailujen tueksi
- **Python-rajapinta** kehyksen käyttämiseen myös osana muuta sovellusta

---

## Projektirakenne

```text
TradingAgents-Finnish/
├── tradingagents/        # Ydinjärjestelmä (upstream-pohja)
├── fi_prompts/           # Suomenkieliset promptit
├── db/                   # PostgreSQL-schema ja migraatiot
├── eval_results/         # Arviointi- ja backtesting-tulokset
├── docs/superpowers/     # Tekninen dokumentaatio
├── cli/                  # Komentoriviliittymä
└── tests/                # Testit
```

---

## Asennus

### 1. Kloonaa repositorio

```bash
git clone https://github.com/Murtsi/TradingAgents-Finnish.git
cd TradingAgents-Finnish
```

### 2. Luo ympäristö

```bash
conda create -n tradingagents python=3.13
conda activate tradingagents
```

Vaihtoehtoisesti:

```bash
uv sync
```

### 3. Asenna riippuvuudet

```bash
pip install -e .
```

tai

```bash
pip install -r requirements.txt
```

### 4. Lisää ympäristömuuttujat

Kopioi esimerkkitiedosto ja täydennä omat avaimet:

```bash
cp .env.example .env
```

Tuetut palvelut:

```env
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...
XAI_API_KEY=...
OPENROUTER_API_KEY=...
ALPHA_VANTAGE_API_KEY=...
```

---

## Käyttö komentoriviltä

Ohjelmaa käytetään komentoriviltä alkuperäisen TradingAgents-projektin tavoin.

```bash
python -m cli.main
```

Käynnistyksen jälkeen käyttäjä voi valita interaktiivisesti analysoitavan tickerin, päivämäärän, käytettävän LLM-palvelun sekä analyysin syvyyden.

---

## Python-käyttö

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "anthropic"
config["deep_think_llm"] = "claude-opus-4"
config["quick_think_llm"] = "claude-haiku-4"
config["max_debate_rounds"] = 2

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NOKIA", "2026-03-24")
print(decision)
```

Lisäasetukset löytyvät tiedostosta `tradingagents/default_config.py`.

---

## Arkkitehtuuri

KauppaAgentit hyödyntää useista rooleista koostuvaa analyysiprosessia, jossa eri agentit tarkastelevat markkinaa eri näkökulmista.

| Agentti | Rooli |
|---|---|
| Fundamenttianalyytikko | Yhtiön taloudellinen analyysi |
| Sentimenttianalyytikko | Markkinatunnelman arviointi |
| Uutisanalyytikko | Uutis- ja tapahtumavetoisen tiedon käsittely |
| Tekninen analyytikko | Teknisten indikaattorien tarkastelu |
| Tutkijatiimi | Näkemysten vertailu ja väittely |
| Kaupankäyntiagentti | Päätösehdotuksen muodostaminen |
| Riskienhallinta | Riskitason arviointi |
| Portfoliopäällikkö | Lopullinen hyväksyntä- tai hylkäyspäätös |

---

## Testaus

```bash
pytest tests/
```

---

## Huomioitavaa

Tämä projekti on tarkoitettu tutkimus-, kehitys- ja kokeilukäyttöön. Se ei ole sijoitusneuvontaa eikä takaa kaupankäyntituloksia.

---

## Lähtöprojekti ja lisenssi

Tämä repositorio pohjautuu [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) -projektiin. Alkuperäinen lisenssi ja upstream-viittaukset tulee säilyttää projektissa.
