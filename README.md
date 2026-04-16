# KauppaAgentit

Suomenkielinen TradingAgents-haara Helsingin pörssin (OMXH) osakkeiden analysointiin.

> Projekti pohjautuu [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents)-kehykseen ja tuo siihen suomenkielisiä promptteja, OMXH-käyttöön sovitettuja muutoksia sekä paikallisia integraatioita.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-green.svg)](https://python.org)
[![Upstream: TradingAgents](https://img.shields.io/badge/Upstream-TradingAgents-orange.svg)](https://github.com/TauricResearch/TradingAgents)

---

## Yleiskuva

KauppaAgentit on suomenkielinen toteutus TradingAgents-kehyksestä. Sen tarkoitus on helpottaa monen agentin LLM-pohjaisen analyysiputken käyttöä suomalaisessa markkinaympäristössä, erityisesti OMXH-yhtiöiden tarkastelussa.

Projekti säilyttää upstream-rakenteen ytimen, mutta lisää suomenkielisiä prompteja, paikallisia asetuksia sekä käyttöä tukevia komponentteja. Käyttö tapahtuu pääasiassa komentoriviltä.

Keskeiset painopisteet:
- suomenkieliset promptit ja analyysipolut
- OMXH-painotteinen käyttö
- komentorivikäyttö alkuperäisen projektin tapaan
- paikalliset laajennukset ja integraatiot
- Docker- ja ympäristömuuttujapohjainen käyttöönotto

---

## Keskeiset ominaisuudet

- **Suomenkieliset promptit** (`fi_prompts/`) agenttien ohjaukseen
- **Komentorivikäyttö** (`cli/`) interaktiiviseen ajamiseen
- **Upstream-yhteensopiva ydin** (`tradingagents/`) säilytettynä pohjana
- **Tietokantakomponentit** (`db/`) paikallista tallennusta ja skeemaa varten
- **Telegram-botti** (`telegram_bot/`) vaihtoehtoisena käyttörajapintana
- **Testit** (`tests/`) kehityksen ja regressioiden tueksi
- **Docker-tuki** (`Dockerfile`, `docker-compose.yml`) käyttöönottoon eri ympäristöissä

---

## Projektirakenne

```text
TradingAgents-Finnish/
├── assets/               # Projektin resurssit
├── cli/                  # Komentoriviliittymä
├── db/                   # Tietokantaskeema ja siihen liittyvät tiedostot
├── fi_prompts/           # Suomenkieliset promptit
├── telegram_bot/         # Telegram-käyttöliittymä
├── tests/                # Testit
├── tradingagents/        # Upstream-pohjainen ydin
├── Dockerfile
├── docker-compose.yml
├── main.py
├── pyproject.toml
├── requirements.txt
└── README.md
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

Vaihtoehtoisesti voit käyttää `uv`:ta:

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

```bash
cp .env.example .env
```

Täytä sen jälkeen tarvittavat API-avaimet omaan ympäristöösi.

Mahdollisia palveluita ovat esimerkiksi:
- OpenAI
- Google
- Anthropic
- xAI
- OpenRouter
- Alpha Vantage

---

## Käyttö komentoriviltä

Projektia käytetään ensisijaisesti komentoriviltä upstream-projektin toimintamallin mukaisesti.

```bash
python main.py
```

tai tarvittaessa CLI-rakenteen kautta projektin omien asetusten mukaan.

Käynnistyksen jälkeen käyttäjä voi valita analysoitavan tickerin, päivämäärän, käytettävän mallipalvelun sekä analyysin asetuksia.

---

## Python-käyttö

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "anthropic"
config["deep_think_llm"] = "claude-opus-4"
config["quick_think_llm"] = "claude-haiku-4"

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NOKIA", "2026-03-24")
print(decision)
```

Tarkemmat asetukset löytyvät projektin konfiguraatiosta ja upstream-ydintä vastaavista tiedostoista.

---

## Arkkitehtuuri

KauppaAgentit hyödyntää usean agentin analyysiprosessia, jossa eri roolit tarkastelevat markkinaa eri näkökulmista. Suomenkielinen haara painottaa erityisesti prompttien lokalisointia, OMXH-käyttöä ja käyttöympäristön mukauttamista.

Tyypillisiä analyysirooleja ovat:
- fundamenttianalyysi
- sentimenttianalyysi
- uutisanalyysi
- tekninen analyysi
- riskienhallinta
- lopullisen päätösehdotuksen muodostus

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

Tämä repositorio pohjautuu [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) -projektiin. Upstream-viittaukset ja alkuperäinen lisenssi tulee säilyttää projektissa.
