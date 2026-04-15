# KauppaAgentit

Suomenkielinen sovellus- ja integraatiokerros TradingAgents-kehyksen ympärille, painottuen Helsingin pörssin (OMXH) osakkeiden analysointiin.

> Tämä projekti perustuu [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) -kehykseen ja laajentaa sitä suomenkielisellä käyttöliittymällä, Telegram-integraatiolla sekä paikalliseen käyttöön sovitetuilla komponenteilla.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-green.svg)](https://python.org)
[![Upstream: TradingAgents](https://img.shields.io/badge/Upstream-TradingAgents-orange.svg)](https://github.com/TauricResearch/TradingAgents)

---

## Yleiskuva

KauppaAgentit on suomenkielinen toteutus ja jatkokehitys TradingAgents-kehyksestä. Projektin tavoitteena on tehdä monen agentin LLM-pohjaisesta analyysiputkesta helpommin käytettävä suomalaisessa ympäristössä, erityisesti OMXH-yhtiöiden tarkastelussa.

Projektissa on painotettu seuraavia osa-alueita:

- suomenkieliset promptit ja käyttöpolut
- Telegram-botti osakeanalyysien ajamiseen
- suomalaisiin lähteisiin sovitettu uutis- ja datavirta
- PostgreSQL-pohjainen tallennus analyysituloksille
- arviointi- ja backtesting-ajot paikallisiin käyttötapauksiin

---

## Keskeiset ominaisuudet

- **Suomenkieliset promptit** (`fi_prompts/`) agenttien ohjaukseen ja analyysien tuottamiseen
- **Telegram-botti** (`telegram_bot/`) nopeaan käyttöön ilman erillistä käyttöliittymää
- **Tietokantakerros** (`db/`) analyysien ja tulosten tallennukseen
- **Arviointiaineistot** (`eval_results/`) testiajojen ja vertailujen tueksi
- **Komentorivikäyttöliittymä** (`cli/`) paikalliseen käyttöön ja kehitykseen

---

## Projektirakenne

```text
TradingAgents-Finnish/
├── tradingagents/        # Ydinjärjestelmä (upstream-pohja)
├── fi_prompts/           # Suomenkieliset promptit
├── telegram_bot/         # Telegram-botti
├── db/                   # PostgreSQL-schema ja migraatiot
├── eval_results/         # Arviointi- ja backtesting-tulokset
├── docs/superpowers/     # Tekninen dokumentaatio
├── cli/                  # Komentoriviliittymä
└── tests/                # Testit
```

---

## Käyttö Telegramin kautta

Telegram-botti tarjoaa suoraviivaisen tavan käynnistää analyysi ilman paikallista käyttöliittymää.

### Käynnistys

1. Luo botti Telegramissa `@BotFather`-palvelun kautta.
2. Selvitä oma Telegram-ID esimerkiksi `@userinfobot`-botilla.
3. Lisää tarvittavat muuttujat `.env`-tiedostoon.
4. Käynnistä botti paikallisesti.

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_WHITELIST=your_telegram_id
ANTHROPIC_API_KEY=your_api_key
```

```bash
python -m telegram_bot.bot
```

### Komennot

| Komento | Kuvaus |
|---|---|
| `/analysoi NOKIA` | Suorittaa osakeanalyysin annetulle tickerille |

### Esimerkkejä OMXH-yhtiöistä

| Yhtiö | Komento |
|---|---|
| Nokia | `/analysoi NOKIA` |
| Nordea | `/analysoi NORDEA` |
| Neste | `/analysoi NESTE` |
| KONE | `/analysoi KONE` |
| UPM | `/analysoi UPM` |

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

## CLI-käyttö

```bash
python -m cli.main
```

Komentorivikäyttöliittymässä voidaan valita ticker, päivämäärä, LLM-palvelu ja analyysin asetukset interaktiivisesti.

---

## Python-esimerkki

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

Alkuperäinen julkaisu:

```bibtex
@article{xiao2024tradingagents,
  title={TradingAgents: Multi-Agents LLM Financial Trading Framework},
  author={Xiao, Yijia and Sun, Edward and Luo, Di and Wang, Wei},
  journal={arXiv preprint arXiv:2412.20138},
  year={2024}
}
```
