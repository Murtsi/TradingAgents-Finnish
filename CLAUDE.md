#
## Parannusideat Suomen markkinalle ja käyttäjäkunnalle

### Käyttäjäsegmentit (OST vs. AOT vs. Rahastot)
Suomessa on yli 400 000 osakesäästötilin haltijaa. OST:lla voi omistaa
vain pörssilistattuja osakkeita ja First North -yhtiöitä (ei ETF:iä tai
rahastoja). Talletusraja on 100 000€.

Segmentointi UI:ssa:
- "Osakesäästötili (OST)" → agentit tietävät kiellot ja veronlykkäysedun
- "Arvo-osuustili (AOT)" → normaali verotuslogiikka
- "Pääosin rahastosijoittaja" → Rahastoagentti etualalle, ticker-analyysi taustalle

### Rahasto- ja ETF-agentti (vain AOT-käyttäjille)
Rakenna `analysts/funds.py` -agentti joka:
- Vertailee Seligsonin, Nordnetin superrahastojen ja laajojen ETF:ien
  kulurakennetta (TER), hajautusta ja historiallista tuottoa
- Näyttää yksinkertaisen rankingin: "matala kulu / laaja hajautus / Suomi-paino"
- EI koskaan näy OST-profiilisille käyttäjille

### Käsitteiden kansantajuistaminen
- Luo `docs/termit.md` — suomenkieliset selitykset: P/E, P/B, beta,
  volatiliteetti, osinkotuotto, free cash flow
- Web-UI:ssa jokaisen teknisen termin vieressä ❓-ikoni → tooltip
- Telegram-komento `/termi <nimi>` → lyhyt selitys suomeksi

### Hinnoittelun realistiset kustannusrajat
Yksi täysi analyysi maksaa API-kuluissa arviolta 0.10–0.40€.
Hinnoittelu on tarkistettava vastaamaan todellisia kuluja:

| Taso     | Analyysit/kk | Hinta | Marginaali-arvio |
|----------|-------------|-------|-----------------|
| Ilmainen | 3 (ei 30)   | 0€    | -0.60–1.20€/kk  |
| Perus    | 20 (ei 30)  | 19€   | ~11–15€/kk      |
| Pro      | 80 (ei ∞)   | 49€   | ~17–25€/kk      |
| Business | 300         | 149€  | ~20–60€/kk      |

### Luottamus ja tietosuoja ("Pankkitason turvallisuus" -narratiivi)
Lisää etusivulle ja `docs/regulaatio.md`:ään:
- Ei kerätä pankkitunnuksia tai henkilötunnuksia
- Portfolio syötetään manuaalisesti tai Nordnet-integraation kautta
- Kaikki data pysyy EU:ssa (esim. Hetzner Helsinki)
- Käyttäjädata ei myydä eteenpäin
- Käyttäjä voi poistaa kaiken datansa milloin tahansa (GDPR Art. 17)

### Backtesting-vastuuvapautus (pakollinen UI:ssa)
Historialliset backtesting-tulokset eivät ennusta tulevaa.
Backtesting-näkymässä PITÄÄ näkyä aina:
"Historialliset tulokset eivät takaa vastaavia tuottoja tulevaisuudessa.
Tämä on simulaatio, ei lupaus."
# CLAUDE.md — KauppaAgentit (TradingAgents Suomi-fork)

## Projektin yleiskuvaus

Tämä on suomalainen fork TauricResearchin TradingAgents-frameworkista (https://github.com/TauricResearch/TradingAgents). Alkuperäinen on Python-pohjainen multi-agent LLM-kaupankäyntiframework joka simuloi oikeaa trading-firmaa erikoistuneilla AI-agenteilla.

Meidän versio kääntää tämän suomalaiselle kuluttajalle: suomenkielinen UI, Helsingin pörssi (OMXH) -tuki, suomalaisten osakkeiden ja rahastojen analyysi, ja helppokäyttöinen käyttöliittymä joka ei vaadi teknistä osaamista.

**Alkuperäinen lisenssi:** Apache-2.0 (TauricResearch/TradingAgents)

## TÄRKEÄ VASTUUVAPAUTUS

Tämä työkalu on tarkoitettu TUTKIMUS- JA OPPIMISTARKOITUKSIIN. Se EI ole sijoitusneuvontaa. Kaupankäyntitulokset vaihtelevat monien tekijöiden perusteella. Käyttäjälle PITÄÄ näyttää selkeä vastuuvapautus ennen käyttöä ja jokaisen päätöksen yhteydessä. Suomen lain mukaan sijoitusneuvonnan antaminen vaatii toimiluvan (Finanssivalvonta). UI:ssa on aina korostettava: "Tämä on AI:n tuottama analyysi, ei sijoitussuositus."

## Upstream-rakenne (TradingAgents)

Alkuperäisen repon rakenne jota forkataan:

```
TradingAgents/
├── tradingagents/
│   ├── agents/              # Agenttien logiikka
│   │   ├── analysts/        # Fundamentti, sentimentti, uutis-, tekninen analyytikko
│   │   ├── researchers/     # Bull & bear tutkijat (väittely)
│   │   ├── trader/          # Kaupankäyntiagentti
│   │   ├── risk_mgmt/       # Riskienhallinta
│   │   └── portfolio_mgr/   # Salkunhoitaja (hyväksyy/hylkää)
│   ├── dataflows/           # Datasyötteet (Yahoo Finance, Alpha Vantage)
│   ├── graph/               # LangGraph-orkestrointi
│   │   └── trading_graph.py # Pää-orkestroija (TradingAgentsGraph)
│   ├── llm_clients/         # LLM-providerien abstraktio
│   └── default_config.py    # Oletuskonfiguraatio
├── cli/                     # CLI-käyttöliittymä (Rich)
├── main.py                  # Entry point
├── requirements.txt
└── pyproject.toml
```

## Meidän muutokset upstreamiin nähden

### 1. Suomenkielinen agenttiprompting

Kaikki agenttien system-promptit käännetään suomeksi ja lokalisoidaan:

- **Fundamenttianalyytikko** → Osaa tulkita suomalaisten yhtiöiden tilinpäätöksiä (IFRS, Suomen verotus)
- **Sentimenttianalyytikko** → Seuraa Kauppalehteä, Taloussanomia, Inderesin foorumia, X/Twitter suomeksi
- **Uutisanalyytikko** → Suomalaiset ja pohjoismaiset uutislähteet, EKP-päätökset, EU-regulaatio
- **Tekninen analyytikko** → Sama kuin upstream (MACD, RSI yms. ovat universaaleja)
- **Tutkijat (bull/bear)** → Väittely suomeksi, suomalaiseen markkinakontekstiin
- **Kauppias** → Ottaa huomioon OMXH:n kaupankäyntiajat, likviditeetti
- **Riskienhallinta** → EUR-denominoitu, suomalainen verotuskonteksti (pääomatulot 30%/34%)
- **Salkunhoitaja** → Lopullinen päätös suomalaiselle sijoittajalle

### 2. Datalähteet

Alkuperäinen käyttää Yahoo Finance + Alpha Vantage. Meidän versio lisää:

- **OMXH-data:** Helsingin pörssin osakkeet (Nordnet API / Kauppalehti scraping varalle)
- **Inderes:** Suomalaisten osakkeiden tavoitehinnat ja analyysit (jos API saatavilla)
- **EKP:** Korkopäätökset, inflaatiodata euroalueelle
- **Suomalaiset rahastot:** Nordnet/Seligson rahastotiedot

### 3. Käyttöliittymä (Suomi-UI)

Upstream tarjoaa CLI:n (Rich-kirjasto). Meidän versio:

**Vaihtoehto A — Web-UI (suositus kuluttajalle):**
- React + Vite + Tailwind
- Suomenkielinen dashboard
- WebSocket agenttien tilan reaaliaikaseuranta
- Visuaaliset raportit (grafiikat, mittarit)

**Vaihtoehto B — Parannettu CLI:**
- Upstream CLI suomennettuna
- Rich-paneelit suomeksi

Päätös toteutuksesta tehdään erikseen. CLAUDE.md kattaa molemmat.

## Tech Stack

- **Kieli:** Python 3.13+ (upstream yhteensopivuus)
- **Agent-orkestrointi:** LangGraph (upstreamista)
- **LLM-providerit:** Anthropic (Claude), OpenAI, Ollama (lokaali) — konffattavissa
- **Datasyötteet:** Yahoo Finance, Alpha Vantage, OMXH-lähteet
- **Frontend (jos web):** React 18 + Vite + Tailwind CSS + WebSocket
- **Paketinhallinta:** uv (upstreamista) tai pip
- **Infrastruktuuri:** Docker + Docker Compose (kaikki palvelut konteissa)
- **Tietokanta:** PostgreSQL 16 (Docker-kontissa) + Redis (LLM-vastausten cache)

## Docker-infrastruktuuri

### Miksi Docker on pakollinen

TradingAgents tekee jokaisella analyysilla kymmeniä LLM-kutsuja, ja jokainen agentti tuottaa väliraportteja, väittelylogeja ja datatuloksia. Ilman hallintaa tietokanta kasvaa nopeasti hallitsemattomaksi. Docker ratkaisee:

1. **Eristys** — PostgreSQL, Redis ja sovellus omissa konteissaan, eivät sotke host-konetta
2. **Toistettavuus** — `docker compose up` ja kaikki toimii, kenen tahansa koneella
3. **Siivous** — `docker compose down -v` nollaa kaiken puhtaaksi
4. **Kehitys vs tuotanto** — eri compose-profiilit eri tarpeisiin

### docker-compose.yml

```yaml
services:
  # ── PostgreSQL ──────────────────────────────────────────
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: kauppa_agentit
      POSTGRES_USER: ${DB_USER:-kauppa}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-dev_salasana}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d  # Ajetaan automaattisesti ekan käynnistyksen yhteydessä
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-kauppa}"]
      interval: 5s
      timeout: 3s
      retries: 5

  # ── Redis (LLM-vastausten cache) ────────────────────────
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

  # ── Sovellus (TradingAgents) ────────────────────────────
  app:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    environment:
      DATABASE_URL: postgresql://${DB_USER:-kauppa}:${DB_PASSWORD:-dev_salasana}@db:5432/kauppa_agentit
      REDIS_URL: redis://redis:6379/0
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      ALPHA_VANTAGE_API_KEY: ${ALPHA_VANTAGE_API_KEY}
    volumes:
      - ./tradingagents:/app/tradingagents    # Live reload kehityksessä
      - ./fi_prompts:/app/fi_prompts
      - ./results:/app/results
    ports:
      - "8000:8000"   # API (jos web-versio)

  # ── Web-UI (vain jos web-versio) ────────────────────────
  # web:
  #   build:
  #     context: ./web
  #     dockerfile: Dockerfile
  #   depends_on:
  #     - app
  #   ports:
  #     - "3000:3000"

  # ── DB-siivous (scheduled cleanup) ─────────────────────
  db-cleanup:
    image: postgres:16-alpine
    depends_on:
      db:
        condition: service_healthy
    environment:
      PGHOST: db
      PGUSER: ${DB_USER:-kauppa}
      PGPASSWORD: ${DB_PASSWORD:-dev_salasana}
      PGDATABASE: kauppa_agentit
    entrypoint: >
      sh -c "while true; do
        echo '[SIIVOUS] Poistetaan yli 30 päivää vanhat välimuistitiedot...'
        psql -c \"DELETE FROM agent_valitulokset WHERE created_at < NOW() - INTERVAL '30 days';\"
        psql -c \"DELETE FROM llm_cache WHERE created_at < NOW() - INTERVAL '14 days';\"
        psql -c \"DELETE FROM vaittely_logit WHERE created_at < NOW() - INTERVAL '30 days';\"
        psql -c \"VACUUM ANALYZE;\"
        echo '[SIIVOUS] Valmis. Seuraava ajo 24h päästä.'
        sleep 86400
      done"
    restart: unless-stopped

volumes:
  pgdata:       # Persistentti tietokanta-data
  redisdata:    # Redis-cache (voi menettää, ei kriittinen)
```

### Dockerfile (sovellus)

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Järjestelmäriippuvuudet
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Python-riippuvuudet
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sovelluskoodi
COPY . .

# CLI oletuksena, voi ylikirjoittaa web-serverillä
CMD ["python", "-m", "cli.main"]
```

### Tietokannan skeema ja siivousstrategia

```sql
-- db/init/001_schema.sql (ajetaan automaattisesti docker-entrypoint-initdb.d:stä)

-- Pääanalyysit (säilytetään pysyvästi)
CREATE TABLE analyysit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(20) NOT NULL,
    paivays DATE NOT NULL,
    paatos VARCHAR(10) NOT NULL CHECK (paatos IN ('OSTA', 'PIDÄ', 'MYY')),
    luottamus DECIMAL(3,2),           -- 0.00-1.00
    yhteenveto TEXT NOT NULL,          -- Suomenkielinen tiivistelmä
    konfiguraatio JSONB,              -- Käytetyt LLM:t, debate rounds jne.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, paivays)
);

-- Agenttien yksittäiset raportit (säilytetään 90 päivää)
CREATE TABLE agentti_raportit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analyysi_id UUID REFERENCES analyysit(id) ON DELETE CASCADE,
    agentti_tyyppi VARCHAR(30) NOT NULL,  -- 'fundamentti', 'sentimentti', 'uutis', 'tekninen', 'kauppias', 'riski', 'salkunhoitaja'
    raportti TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Välimuistituotteet (siivotaan aggressiivisesti, 30 päivää)
CREATE TABLE agent_valitulokset (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analyysi_id UUID REFERENCES analyysit(id) ON DELETE CASCADE,
    vaihe VARCHAR(50) NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bull vs Bear -väittelylogit (siivotaan 30 päivää)
CREATE TABLE vaittely_logit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analyysi_id UUID REFERENCES analyysit(id) ON DELETE CASCADE,
    kierros INTEGER NOT NULL,
    bull_argumentti TEXT,
    bear_argumentti TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- LLM-vastausten cache (siivotaan aggressiivisesti, 14 päivää)
-- Estää samojen API-kutsujen toistamisen
CREATE TABLE llm_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 promptista
    provider VARCHAR(20) NOT NULL,
    model VARCHAR(50) NOT NULL,
    vastaus TEXT NOT NULL,
    tokenit_in INTEGER,
    tokenit_out INTEGER,
    kustannus_eur DECIMAL(10,6),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Kustannusseuranta (säilytetään pysyvästi)
CREATE TABLE api_kustannukset (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analyysi_id UUID REFERENCES analyysit(id) ON DELETE SET NULL,
    provider VARCHAR(20) NOT NULL,
    model VARCHAR(50) NOT NULL,
    tokenit_in INTEGER NOT NULL,
    tokenit_out INTEGER NOT NULL,
    kustannus_eur DECIMAL(10,6) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indeksit
CREATE INDEX idx_analyysit_ticker ON analyysit(ticker);
CREATE INDEX idx_analyysit_paivays ON analyysit(paivays DESC);
CREATE INDEX idx_analyysit_created ON analyysit(created_at DESC);
CREATE INDEX idx_agentti_raportit_analyysi ON agentti_raportit(analyysi_id);
CREATE INDEX idx_llm_cache_hash ON llm_cache(prompt_hash);
CREATE INDEX idx_llm_cache_created ON llm_cache(created_at);
CREATE INDEX idx_valitulokset_created ON agent_valitulokset(created_at);
CREATE INDEX idx_vaittely_created ON vaittely_logit(created_at);
CREATE INDEX idx_kustannukset_created ON api_kustannukset(created_at DESC);
CREATE INDEX idx_kustannukset_analyysi ON api_kustannukset(analyysi_id);
```

### Datan elinkaaripolitiikka

| Taulu | Säilytysaika | Siivousmenetelmä | Syy |
|-------|-------------|------------------|-----|
| `analyysit` | **Pysyvä** | Ei siivota | Päädata, halpa tallentaa |
| `agentti_raportit` | 90 päivää | Cron (db-cleanup kontti) | Isoja tekstejä, ei tarvita pitkään |
| `agent_valitulokset` | 30 päivää | Cron | Debuggausta varten, paljon dataa |
| `vaittely_logit` | 30 päivää | Cron | Mielenkiintoisia mutta tilaa vieviä |
| `llm_cache` | 14 päivää | Cron | Vanhat vastaukset eivät ole relevantteja |
| `api_kustannukset` | **Pysyvä** | Ei siivota | Budjettiseuranta, pieniä rivejä |

### Redis-cache strategia

Redis toimii nopeana välimuistina LLM-vastauksille ja dataflow-tuloksille:

```python
# Cachen avaimet ja TTL:t
CACHE_CONFIG = {
    "llm_response:{prompt_hash}": 3600 * 24,      # 24h — sama prompti, sama vastaus
    "yahoo_data:{ticker}:{date}": 3600 * 6,        # 6h — markkinadata päivittyy
    "omxh_data:{ticker}": 3600,                    # 1h — reaaliaikainen data
    "sentiment:{ticker}:{date}": 3600 * 12,        # 12h — sentimentti muuttuu hitaasti
    "news:{ticker}:{date}": 3600 * 2,              # 2h — uutiset päivittyvät
}
```

Redis on konfiguroitu `maxmemory-policy allkeys-lru` — kun muisti loppuu, vanhin data poistetaan automaattisesti. Datahävikki ei ole ongelma koska Redis on vain cache, pysyvä data on PostgreSQL:ssä.

### Docker-komennot kehittäjälle

```bash
# Käynnistä kaikki palvelut
docker compose up -d

# Katso logit
docker compose logs -f app

# Nollaa kaikki (tietokanta, cache, kaikki data)
docker compose down -v

# Nollaa vain tietokanta (säilytä Redis-cache)
docker compose down
docker volume rm kauppa-agentit_pgdata
docker compose up -d

# Aja yksittäinen analyysi kontissa
docker compose exec app python main.py

# Avaa psql tietokantaan
docker compose exec db psql -U kauppa kauppa_agentit

# Tarkista tietokannan koko
docker compose exec db psql -U kauppa kauppa_agentit -c \
  "SELECT pg_size_pretty(pg_database_size('kauppa_agentit'));"

# Tarkista taulujen koot
docker compose exec db psql -U kauppa kauppa_agentit -c \
  "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) 
   FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC;"

# Pakota siivous nyt (ei odota 24h)
docker compose restart db-cleanup
```

## MCP-pluginit ja niiden käyttö

### Asennetut MCP-serverit:

| MCP | Rooli tässä projektissa | Milloin käytetään |
|-----|------------------------|-------------------|
| **postgres** (crystaldba) | Kauppahistorian, analyysitulosten ja portfolion tallennus | Tallenna ja hae aiempia analyysejä, seurantadata |
| **context7** (Upstash) | LangGraph, React, Python-kirjastojen docsit | Aina kun koodaat upstream-kirjastojen kanssa |
| **desktop-commander** | Pitkäkestoiset ajokomennot | Agenttien propagate()-ajot kestävät minuutteja |
| **claude-context** (Zilliz) | Koodikannan semanttinen haku | Kun etsit upstreamin logiikkaa muokattavaksi |
| **memory** | Sessiomuisti kehityksen välillä | Muista mihin jäätiin, mitä päätöksiä tehty |

### MCP-käyttösäännöt:

1. **Context7 ENSIN** kun kosket LangGraph-, Rich- tai tradingagents-koodiin — tarkista ajantasainen API
2. **Claude-context** kun etsit upstreamin koodista tiettyä logiikkaa forkkia varten
3. **Postgres-MCP** analyysitulosten persistointiin — jokainen analyysiajo tallennetaan
4. **Desktop-commander** propagate()-ajoihin jotka kestävät yli 30s
5. **Memory** jokaisen kehityssession yhteenvedot

## Agenttiarkkitehtuuri (upstream + meidän lisäykset)

```
                    ┌──────────────────────────┐
                    │    KÄYTTÄJÄ (Suomi-UI)    │
                    │  "Analysoi Nokia (NOKIA)" │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   TradingAgentsGraph      │
                    │   (LangGraph orkestroija) │
                    └────────────┬─────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            ▼                    ▼                     ▼
    ┌───────────────┐  ┌─────────────────┐  ┌────────────────┐
    │ ANALYYTIKOT   │  │   TUTKIJAT      │  │  PÄÄTÖKSENTEKO │
    │               │  │                 │  │                │
    │ • Fundamentti │  │ • Bull-tutkija  │  │ • Kauppias     │
    │ • Sentimentti │  │ • Bear-tutkija  │  │ • Riskienhall. │
    │ • Uutiset     │  │ • (Väittely)    │  │ • Salkunhoitaja│
    │ • Tekninen    │  │                 │  │                │
    └───────┬───────┘  └───────┬─────────┘  └───────┬────────┘
            │                  │                     │
            └──────────────────┼─────────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │   PÄÄTÖS (suomeksi) │
                    │  OSTA / PIDÄ / MYY  │
                    │  + perustelut       │
                    │  + vastuuvapautus   │
                    └─────────────────────┘
```

### Agenttikohtainen flow:

1. **Analyytikot** (rinnakkain) → Kukin tuottaa raportin omasta näkökulmastaan
2. **Tutkijat** → Bull ja bear väittelevät analyytikkojen raporttien pohjalta (max_debate_rounds konfiguroitava)
3. **Kauppias** → Koostaa kaiken ja tekee ehdotuksen
4. **Riskienhallinta** → Arvioi ehdotuksen riskit
5. **Salkunhoitaja** → Hyväksyy tai hylkää

## Konfiguraatio

Upstream DEFAULT_CONFIG jota muokataan:

```python
FINNISH_CONFIG = {
    # LLM-asetukset
    "llm_provider": "anthropic",           # tai "openai", "ollama"
    "deep_think_llm": "claude-sonnet-4-20250514",  # Monimutkainen päättely
    "quick_think_llm": "claude-haiku-4-5-20251001", # Nopeat tehtävät
    "deep_think_provider_params": None,
    "quick_think_provider_params": None,
    
    # Väittelykierrokset (enemmän = syvempi analyysi, enemmän API-kutsuja)
    "max_debate_rounds": 1,                # Oletus 1, tuotanto 2-3
    
    # Datalähteet
    "online_tools": True,                  # Reaaliaikainen data
    
    # Suomi-lisäykset
    "locale": "fi_FI",
    "currency": "EUR",
    "exchange": "OMXH",
    "tax_context": {
        "capital_gains_rate": 0.30,        # Pääomatulo 30%
        "capital_gains_rate_high": 0.34,   # Yli 30 000€
        "threshold": 30000,
    },
    "news_sources": [
        "kauppalehti",
        "taloussanomat", 
        "inderes",
        "reuters_nordic",
        "yle_talous",
    ],
    "disclaimer_required": True,           # Pakollinen vastuuvapautus
}
```

## Projektirakenne (meidän fork)

```
kauppa-agentit/
├── CLAUDE.md                         # Tämä tiedosto
├── .mcp.json                         # MCP-serverien konfiguraatio
├── .env                              # API-avaimet (EI versionhallintaan)
├── .gitignore
├── docker-compose.yml                # Kaikki palvelut yhdellä komennolla
├── Dockerfile                        # Sovelluskontissa
├── pyproject.toml
├── requirements.txt
│
├── tradingagents/                    # Upstream-koodi (fork)
│   ├── agents/                       # Muokatut agentit suomeksi
│   │   ├── analysts/
│   │   │   ├── fundamentals.py       # + Suomen IFRS/verotus
│   │   │   ├── sentiment.py          # + Suomalaiset lähteet
│   │   │   ├── news.py               # + Kauppalehti, YLE jne.
│   │   │   └── technical.py          # Lähes muuttumaton
│   │   ├── researchers/
│   │   │   ├── bull.py               # Promptit suomeksi
│   │   │   └── bear.py               # Promptit suomeksi
│   │   ├── trader/
│   │   │   └── trader.py             # + OMXH-konteksti
│   │   ├── risk_mgmt/
│   │   │   └── risk.py               # + EUR, Suomen verotus
│   │   └── portfolio_mgr/
│   │       └── manager.py            # + Vastuuvapautus mukana
│   ├── dataflows/                    # + OMXH-datalähteet
│   │   ├── finnhub_utils.py          # Upstream
│   │   ├── yahoo_utils.py            # Upstream
│   │   └── omxh_utils.py             # UUSI: Helsingin pörssi
│   ├── graph/
│   │   └── trading_graph.py          # Upstream + locale-tuki
│   ├── llm_clients/                  # Upstream
│   ├── default_config.py             # Upstream
│   └── finnish_config.py             # UUSI: Suomi-konfiguraatio
│
├── fi_prompts/                       # Suomenkieliset agenttipromptit
│   ├── fundamentals_system.md
│   ├── sentiment_system.md
│   ├── news_system.md
│   ├── technical_system.md
│   ├── bull_researcher_system.md
│   ├── bear_researcher_system.md
│   ├── trader_system.md
│   ├── risk_system.md
│   └── portfolio_manager_system.md
│
├── cli/                              # Upstream CLI suomennettuna
│   └── main.py
│
├── web/                              # UUSI: Web-UI (jos valitaan)
│   ├── src/
│   │   ├── components/
│   │   │   ├── AnalyysiNakyma.tsx    # Pää-dashboard
│   │   │   ├── AgenttiStatus.tsx     # Agenttien reaaliaikatila
│   │   │   ├── OsakePicker.tsx       # Osakkeen valitsin (OMXH)
│   │   │   ├── RaporttiNakyma.tsx    # Analyysiraportti
│   │   │   ├── PaatosKortti.tsx      # OSTA/PIDÄ/MYY + perustelut
│   │   │   └── Vastuuvapautus.tsx    # Pakollinen disclaimer
│   │   ├── hooks/
│   │   │   ├── useAnalyysi.ts        # WebSocket-hook agenttien tilaan
│   │   │   └── useOsakkeet.ts        # OMXH-osakelistaus
│   │   ├── i18n/
│   │   │   └── fi.json              # Käännökset
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── api/                              # UUSI: Backend (jos web-versio)
│   ├── server.py                     # FastAPI backend
│   ├── ws_handler.py                 # WebSocket agenttien tilan streamaus
│   └── routes/
│       ├── analysis.py               # POST /api/analysoi
│       └── history.py                # GET /api/historia
│
├── db/                               # PostgreSQL-skeema
│   ├── init/                         # Docker-entrypoint: ajetaan automaattisesti
│   │   └── 001_schema.sql           # Taulut, indeksit, constraints
│   └── migrations/                   # Myöhemmät skeemamuutokset
│
├── bot/                              # Telegram/Discord -botti
│   ├── telegram_bot.py               # python-telegram-bot entry point
│   ├── handlers/
│   │   ├── analysoi.py               # /analysoi NOKIA
│   │   ├── salkku.py                 # /salkku — portfolioseuranta
│   │   ├── halytys.py                # /halytys NOKIA -5% — hälytykset
│   │   └── tilaus.py                 # /tilaus — credit-saldo ja tilaukset
│   └── formatters/
│       └── telegram_report.py        # Agenttirapsa → Telegram-viesti
│
├── credits/                          # Credit-järjestelmä
│   ├── credit_manager.py             # Saldot, kulutus, tarkistukset
│   ├── pricing.py                    # Tilaustasot ja hinnat
│   └── stripe_integration.py         # Maksut (Stripe)
│
├── integrations/                     # Ulkoiset integraatiot
│   ├── nordnet/                      # Nordnet-salkkudata
│   │   └── nordnet_client.py
│   ├── vero/                         # Suomalainen verolaskuri
│   │   └── paaomavero.py
│   └── alerts/                       # Hälytysjärjestelmä
│       ├── monitor.py                # Jatkuva portfoliomonitorointi
│       └── notifier.py               # Email, Telegram, push
│
├── tests/
│   ├── test_agents/
│   ├── test_dataflows/
│   ├── test_credits/
│   ├── test_bot/
│   └── fixtures/
│
└── docs/
    ├── architecture.md
    ├── lokalisointi.md               # Miten suomennos toimii
    ├── kaupallistaminen.md           # Bisnessuunnitelma ja hinnoittelu
    ├── regulaatio.md                 # Finanssivalvonta, MiFID II, disclaimerit
    └── upstream-sync.md              # Miten synkataan upstreamin kanssa
```

## Koodauskäytännöt

### Python (agentit, backend)
- Python 3.13+, type hints kaikkialla
- Upstream-koodia muokataan mahdollisimman vähän — omat lisäykset erillisissä tiedostoissa
- Suomenkieliset promptit erillisessä fi_prompts/ -kansiossa, ei inline-stringeinä
- Async/await dataflowseissa
- Docstringit suomeksi uudelle koodille

### TypeScript/React (web-UI)
- Funktionaaliset komponentit + hooks
- Tailwind CSS, ei erillisiä CSS-tiedostoja
- Kaikki UI-tekstit i18n/fi.json -tiedostosta
- Loading-tilat ja error boundaryt jokaiselle agenttinäkymälle

### Nimeäminen
- Python: snake_case (upstream-yhteensopivuus)
- React-komponentit: PascalCase suomeksi (AnalyysiNakyma, PaatosKortti)
- Tiedostot: snake_case Pythonissa, PascalCase Reactissa
- Git-branchit: `feature/sentimentti-kauppalehti`, `fix/omxh-data`, `ui/dashboard`

### Upstream-synkronointi
- Upstream remote: `git remote add upstream https://github.com/TauricResearch/TradingAgents.git`
- Meidän muutokset AINA omissa tiedostoissa tai selkeästi merkittyinä
- Kommentoi muokatut upstream-rivit: `# FORK: Suomi-lokalisointi`
- Merge upstreamista säännöllisesti: `git fetch upstream && git merge upstream/main`

## Tietoturva

- `.env` EI KOSKAAN versionhallintaan (API-avaimet, DB-yhteys)
- Käyttäjän syöttämä ticker validoidaan (vain OMXH/tunnetut osakkeet)
- Ei tallenneta käyttäjän henkilötietoja
- API-avaimet vain palvelinpuolella (ei frontendiin)
- Rate limiting API-kutsuihin (LLM-kulut voivat karata)
- Vastuuvapautus AINA näkyvissä — ei voi ohittaa

## Suomenkielisen lokalisoinnin periaatteet

### Agenttipromptit
- Jokainen agentti saa system-promptin suomeksi fi_prompts/ -kansiosta
- Prompteissa kerrotaan suomalainen konteksti:
  - "Analysoit Helsingin pörssin (OMXH) osaketta"
  - "Huomioi suomalainen pääomaverotus (30%/34%)"
  - "Sentimenttilähteet: Kauppalehti, Inderes, Taloussanomat"
- Agentti vastaa AINA suomeksi

# TÄRKEÄ OST-RAJOITUS — agenttien on tunnettava tämä
OST_RAJOITTEET = {
    "sallitut_instrumentit": ["OMXH_osakkeet", "First_North_osakkeet"],
    "kielletyt_instrumentit": ["ETF", "indeksirahastot", "joukkovelkakirjat"],
    "talletusraja_eur": 100_000,
    "veron_lykkays": True,  # Vero realisoituu vasta nostohetkellä, ei myyntihetkellä
    "huomio": "Rahastoagentti ja ETF-analyysit eivät koske OST-käyttäjiä"
}
# Salkunhoitaja-agentti EI SAA suositella ETF:iä tai rahastoja
# OST-profiiliselle käyttäjälle — se olisi faktisesti väärä neuvo.

### Käyttöliittymä
- Termit: "Osta" / "Pidä" / "Myy" (ei Buy/Hold/Sell)
- Euromääräiset summat (€, ei $)
- Suomalaiset desimaalierottimet UI:ssa (1 234,56 €)
- Päivämäärät: pp.kk.vvvv

### Raportit
- Analyytikkojen raportit suomeksi
- Väittelyt (bull vs bear) suomeksi
- Kauppiaan perustelut suomeksi
- Riskiarvio suomeksi
- Lopullinen päätös + vastuuvapautus suomeksi

## Kehityksen vaiheet

### Vaihe 1: Fork + perus lokalisointi (MVP)
- [x] Forkkaa TradingAgents, lisää upstream remote
- [x] Luo finnish_config.py Suomi-asetuksilla
- [x] Käännä agenttipromptit suomeksi (fi_prompts/) — kytketty kaikkiin agentteihin prompt_loader.py:n kautta
- [x] Testaa alkuperäinen CLI suomennetuilla prompteilla — kaikki agentit vastaavat nyt suomeksi
- [x] Varmista upstream toimii: Nokia-analyysi tuotti SELL-päätöksen @ €6.87 (2026-03-24)
- [ ] Docker Compose -ympäristö pystyyn (PostgreSQL + Redis + app)

### Vaihe 1.5: AI Act & Compliance-valmistelu (PAKOLLINEN ennen julkaisua)
- [ ] Selvitä onko KauppaAgentit EU:n AI Actin "korkean riskin
  AI-järjestelmä" — Finanssivalvonta on nimetty valvontaviranomaiseksi
  rahoitussektorin AI-järjestelmille (2026).
- [ ] Lisää `docs/regulaatio.md`:ään erillinen AI Act -osio.
- [ ] Varmista, että jokainen ulos lähtevä raportti sisältää
  koneluettavan disclaimerin (ei vain ihmisluettavan).
- [ ] Luo `compliance_log`-taulu PostgreSQL:ään (audit trail kaikista
  raporteista: timestamp, käytetyt mallit, konfiguraatio, hash).
- [ ] Toteuta `COMPLIANCE_MODE`-ympäristömuuttuja (`finnish_config.py`):
  kun päällä, "OSTA/PIDÄ/MYY" → "Positiivinen / Neutraali / Negatiivinen näkymä".

### Vaihe 2: OMXH-data + suomalaiset lähteet
- [x] Lisää omxh_utils.py Helsingin pörssin datalle (.HE-suffiksi, OMXH_TICKERS-kartta)
- [x] Sentimenttiagentille Kauppalehti/Inderes -datasyöte — get_finnish_news lisätty social_media_analyst.py:hyn, Yahoo Finance fallback
- [x] Uutisagentille suomalaiset uutislähteet — Kauppalehti + YLE Talous RSS (finnish_news.py), ECB/Nordic-hakutermit, yhdistetty get_all_stock_news_combined (1 tool call vs 3), LRU-välimuisti RSS-hauille, OMXH_KEYWORDS-kartta yhtiökohtaisille termeille
- [ ] Testaa Nokia, Nordea, Neste, UPM, KONE -osakkeilla — Nokia testattu ✓


### Vaihe 2.5: Laatu- ja regressiotestit analyysille
- [ ] Luo `tests/test_backtests/` -hakemisto.
- [ ] Kirjoita testit jotka ajavat saman tickerin (NOKIA, NESTE, NORDEA,
  KONE) analyysin useaan kertaan eri parametreilla ja tarkistavat
  päätöksen stabiliteetin (ei hypi OSTA↔MYY ilman selkeää syytä).
- [ ] Luo "golden baseline" -fixturet:
  `tests/fixtures/baseline_<ticker>_<pvm>.json`
  — käytetään regressiotesteissä jokaisen iso prompti/mallipäivityksen
  jälkeen.
- [ ] Testaa automaattisesti myös suomen kielen laatu: varmista että
  agentit eivät vastaa englanniksi mallipäivitysten jälkeen.
- [ ] Valvo agenttiraporttien token-pituutta; aseta ylärajat
  liiallisen API-kulutuksen välttämiseksi.

### Vaihe 3: Telegram-botti (nopein tie käyttäjiin)
- [x] python-telegram-bot -pohjainen botti (telegram_bot/ -paketti)
- [x] `/analysoi NOKIA` → agenttien ajo → tiivistelmä chattiin — toimii; korjaukset: callbacks graph.invoke():lle (progress-päivitykset), formatter (parse_decision OVERWEIGHT/UNDERWEIGHT, lausetason katkaisu, markdown-siivous)
- [ ] `/salkku` → käyttäjän seurantalista
- [x] Whitelist-pohjainen pääsynhallinta (TELEGRAM_WHITELIST env var)
- [ ] Suomalaiset sijoitus-Telegram-ryhmät markkinointikanavana

### Vaihe 3.5: Explainable AI -perustelut (kriittinen käyttäjäluottamukselle)
HUOM: Tämä on siirretty aiemmaksi kuin alun perin suunniteltu —
suomalainen käyttäjä ei luota pelkkään "OSTA"-vastaukseen.
- [ ] Pakota jokainen agentti erittelemään vastauksensa loppuun
  rakenteinen "Perustelut"-osio:
  * Fundamenttiagentti: Top 3 fundamenttisignaalia
  * Sentimentti+uutisagentti: Top 3 positiivista ja Top 3 negatiivista
  * Bull/bear-tutkijat: Väittelyn pääargumentti tiivistetysti
- [ ] Telegram-bottiin: lisää analyysin loppuun "📋 Näytä perustelut"
  -inline-nappi (callback query) joka lähettää erillisen viestin.
- [ ] Web-UI:hin: collapsible "Näytä tarkat perustelut" -paneeli,
  oletuksena suljettu.

### Vaihe 4: Web-dashboard + käyttäjätilit
- [ ] React-dashboard + FastAPI-backend + WebSocket
- [ ] Käyttäjärekisteröinti (email tai Suomi.fi-tunnistautuminen)
- [ ] Agenttien etenemisen reaaliaikaseuranta
- [ ] Analyysien historia ja vertailu
- [ ] Vastuuvapautus-komponentti (pakollinen joka näkymässä)

### Vaihe 4.5: Onboarding-flow ja riskiprofilointi
- [ ] Rakenna Web-UI:hin kevyt onboarding-wizard (max 2 kysymystä
  ensimmäisellä kirjautumisella, loput profiilisivulla myöhemmin):
  * Kokemus: "Aloittelija / Kokenut sijoittaja"
  * Riskinsieto: "Matala / Keskitaso / Korkea"
- [ ] Pakota Finanssivalvonta/MiFID II -yhteensopiva vastuuvapautusteksti
  ennen ENSIMMÄISTÄ analyysiä — ei vain kerran rekisteröinnissä.
- [ ] Tallenna `kayttajat`-tauluun: `kokemus_taso`, `riski_profiili`,
  `disclaimer_hyvaksytty_at`, `tili_tyyppi` (OST/AOT/rahastot).
- [ ] `portfolio_mgr`-agentti lukee nämä parametrit ja muotoilee
  analyysin sävyn sen mukaisesti (aloittelijalle korostetaan
  hajautusta, ei mene henkilökohtaiseen neuvontaan).

### Vaihe 5: Credit-järjestelmä + Stripe-maksaminen
- [ ] Credit-saldot ja kulutusseuranta
- [ ] Stripe-integraatio (EU-maksuvälineet, SEPA)
- [ ] Tilaustasot: Ilmainen / Pro / Business
- [ ] API-kustannusten seuranta per käyttäjä

### Vaihe 6: Portfolioseuranta + hälytykset
- [ ] Käyttäjä syöttää salkkunsa (manuaalinen)
- [ ] Nordnet-integraatio (jos API saatavilla)
- [ ] Jatkuva monitorointi: sentimenttimuutokset, tulosjulkistukset, tekniset signaalit
- [ ] Hälytykset: Telegram, email, push
- [ ] Suomalainen verolaskuri: pääomaveroesimerkit myyntitilanteessa

### Vaihe 6.5: Veroskenaario-simulaattori (Suomen tärkein differentiator)
- [ ] Laajenna `integrations/vero/paaomavero.py` skenaarioihin:
  * "Myy nyt" vs "Myy 6kk päästä" eri kurssioletuksilla
  * Todellinen hankintahinta vs. hankintameno-olettama
    (20% jos omistettu < 10v, 40% jos ≥ 10v)
  * OST vs. AOT: verovaikutuksen ero konkreettisilla luvuilla
- [ ] Web-UI:hin erillinen "Verosimulaattori"-näkymä, joka käyttää
  portfolion dataa ja näyttää taulukossa:
  myyntihinta | luovutusvoitto | arvioitu vero | netto
- [ ] Salkunhoitaja-agentti lisää automaattisesti "💰 Verohuomio"-osion
  jos käyttäjällä on kyseistä osaketta salkussa voitollisena.
- [ ] Telegram-komento: `/vero NOKIA 200 3.80` laskee veroskenaarion
  suoraan chatissa.

### Vaihe 7: Backtesting + uskottavuus
- [ ] "Miltä agenttien suositukset olisivat näyttäneet viimeisen vuoden aikana?"
- [ ] Historiallinen trackrecord -näkymä
- [ ] Vertailu OMXH-indeksiin ja Inderesin suosituksiin

### Vaihe 7.5: "Viikon OMXH-signaali" -automaatio
- [ ] Luo viikoittainen cron-job (maanantai klo 08:00 EET) joka:
  * Skannaa OMXH TOP 25 osakkeen sentimenttimuutokset
  * Nostaa yhden mielenkiintoisimman signaalin
  * Lähettää automaattisesti julkiselle Telegram-kanavalle
- [ ] Formaatti: lyhyt, napakka suomeksi — ei täyttä analyysiä,
  vain signaali + linkki "Lue täysi analyysi KauppaAgenteilla"
- [ ] Tämä toimii orgaanisena markkinointikanavana ja pitää
  käyttäjät sitoutuneina vaikka eivät itse aloita analyysejä.

### Vaihe 8: B2B White-label
- [ ] API-pohjainen versio joka integroituu pankkien/varainhoitajien järjestelmiin
- [ ] Brändättävä dashboard
- [ ] SLA ja enterprise-tuki
- [ ] Yhteydenotto: Nordea, OP, Evli, Mandatum

### Vaihe 8.5: Jaettavat raportit & orgaaninen kasvu
- [ ] Lisää backend-endpoint `GET /api/jaa/<analyysi_id>` joka generoi
  anonyymin, jaettavan URL:n (ei sisällä käyttäjän tunnistetietoja).
- [ ] Jaettavassa raportissa CTA-teksti:
  "Analyysi tuotettu KauppaAgentit-työkalulla — kokeile ilmaiseksi: <url>"
- [ ] Telegram-bottiin komento `/jaa` joka lähettää jaettavan linkin
  viimeisimmästä analyysistä.
- [ ] Luo `jaetut_raportit`-taulu DB:hen (analyysi_id, token, luotu,
  katselukerrat) — seuraa orgaanista leviämistä.

## Kaupallistamisstrategia

### Markkina-asemointi

Positio: "Suomen ensimmäinen AI-analyytikko" — Inderesin rinnalle, ei korvaajaksi. Inderes tarjoaa ihmisanalyytikkojen näkemyksiä, KauppaAgentit tarjoaa AI-agenttien analyysin. Käyttäjä saa "toisen mielipiteen" ja voi verrata.

Kilpailuetu suomalaisilla markkinoilla:
- Ainoa suomenkielinen AI-analyysityökalu
- OMXH-fokus (kansainväliset työkalut eivät kata Helsingin pörssiä kunnolla)
- Suomalainen verotuskonteksti integroituna
- Kuluttajaystävällinen (ei vaadi teknistä osaamista)

### Hinnoittelumalli: Freemium + creditit

```
┌─────────────────────────────────────────────────────────────────┐
│                      HINNOITTELUTASOT                           │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│   ILMAINEN   │    PERUS     │     PRO      │    BUSINESS       │
│    0 €/kk    │   19 €/kk    │   49 €/kk    │    149 €/kk       │
├──────────────┼──────────────┼──────────────┼───────────────────┤
│ 1 analyysi/  │ 30 analyysiä │ Rajattomat   │ Rajattomat        │
│ päivä        │ /kk          │ analyysit    │ analyysit         │
│              │              │              │                   │
│ 2 agenttia   │ Kaikki       │ Kaikki       │ Kaikki agentit    │
│ (perus)      │ agentit      │ agentit      │                   │
│              │              │              │                   │
│ Ei historiaa │ 30 päivän    │ Koko         │ Koko historia     │
│              │ historia     │ historia     │                   │
│              │              │              │                   │
│ —            │ —            │ Portfolioseur│ Portfolioseuranta │
│              │              │ + hälytykset │ + hälytykset      │
│              │              │              │                   │
│ —            │ —            │ Verolaskuri  │ Verolaskuri       │
│              │              │              │                   │
│ —            │ —            │ —            │ API-pääsy         │
│              │              │              │ White-label       │
│              │              │              │ Backtesting       │
│              │              │              │                   │
│ Telegram     │ Telegram     │ Telegram +   │ Kaikki kanavat    │
│              │ + Web        │ Web + Email  │ + API             │
└──────────────┴──────────────┴──────────────┴───────────────────┘
```

### Credit-järjestelmän arkkitehtuuri

```python
# credits/pricing.py

CREDIT_COSTS = {
    # Yksi "analyysi" = kaikki agentit yhdelle osakkeelle
    "full_analysis": 1,           # 1 credit = 4 analyytikkoa + tutkijat + kauppias + riski + salkunhoitaja
    
    # Kevyt analyysi = vain tekninen + sentimentti
    "quick_analysis": 0.25,       # 1/4 creditiä
    
    # Portfolioseuranta (per osake per päivä)
    "portfolio_monitor": 0.1,     # Taustalla pyörivä monitorointi
    
    # Backtesting (per osake per kuukausi historiaa)
    "backtest_month": 0.5,
}

SUBSCRIPTION_TIERS = {
    "ilmainen": {
        "credits_per_month": 30,   # ~1/päivä
        "max_agents": 2,           # Vain tekninen + sentimentti
        "features": ["basic_analysis", "telegram"],
        "price_eur": 0,
    },
    "perus": {
        "credits_per_month": 120,
        "max_agents": "all",
        "features": ["full_analysis", "web_dashboard", "telegram", "history_30d"],
        "price_eur": 19,
    },
    "pro": {
        "credits_per_month": 500,
        "max_agents": "all",
        "features": ["full_analysis", "web_dashboard", "telegram", "email_alerts",
                     "portfolio_monitor", "tax_calculator", "full_history"],
        "price_eur": 49,
    },
    "business": {
        "credits_per_month": "unlimited",
        "max_agents": "all",
        "features": ["all", "api_access", "white_label", "backtesting", "priority_support"],
        "price_eur": 149,
    },
}

# Lisäcreditit (pay-as-you-go)
EXTRA_CREDITS = {
    10: 4.90,    # €
    50: 19.90,
    200: 59.90,
}
```

### Credit-kulutuksen DB-skeema

```sql
-- db/init/002_credits.sql

-- Käyttäjät
CREATE TABLE kayttajat (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    nimi VARCHAR(100),
    tilaus_taso VARCHAR(20) DEFAULT 'ilmainen' CHECK (tilaus_taso IN ('ilmainen', 'perus', 'pro', 'business')),
    stripe_customer_id VARCHAR(100),
    telegram_chat_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Credit-saldot
CREATE TABLE credit_saldot (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kayttaja_id UUID REFERENCES kayttajat(id) ON DELETE CASCADE,
    kuukausi DATE NOT NULL,                    -- '2026-03-01' = maaliskuun saldo
    kuukausikreditit DECIMAL(10,2) NOT NULL,   -- Tilaukseen kuuluvat
    lisäkreditit DECIMAL(10,2) DEFAULT 0,      -- Ostetut extra
    kaytetyt DECIMAL(10,2) DEFAULT 0,
    UNIQUE(kayttaja_id, kuukausi)
);

-- Credit-tapahtumat (audit trail)
CREATE TABLE credit_tapahtumat (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kayttaja_id UUID REFERENCES kayttajat(id) ON DELETE CASCADE,
    analyysi_id UUID REFERENCES analyysit(id) ON DELETE SET NULL,
    tyyppi VARCHAR(30) NOT NULL CHECK (tyyppi IN (
        'kuukausilataus', 'lisaosto', 'analyysi', 'quick_analyysi',
        'portfolio_monitor', 'backtest', 'palautus'
    )),
    maara DECIMAL(10,2) NOT NULL,              -- Positiivinen = lisäys, negatiivinen = kulutus
    saldo_jalkeen DECIMAL(10,2) NOT NULL,
    kuvaus TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Stripe-maksutapahtumat
CREATE TABLE maksut (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kayttaja_id UUID REFERENCES kayttajat(id) ON DELETE CASCADE,
    stripe_payment_id VARCHAR(100) UNIQUE NOT NULL,
    summa_eur DECIMAL(10,2) NOT NULL,
    tuote VARCHAR(50) NOT NULL,                -- 'tilaus_perus', 'lisacreditit_50' jne.
    tila VARCHAR(20) DEFAULT 'pending' CHECK (tila IN ('pending', 'completed', 'failed', 'refunded')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Hälytykset
CREATE TABLE halytykset (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kayttaja_id UUID REFERENCES kayttajat(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    ehto_tyyppi VARCHAR(30) NOT NULL CHECK (ehto_tyyppi IN (
        'hinta_yli', 'hinta_ali', 'sentimentti_muutos',
        'tekninen_signaali', 'tulosjulkistus', 'uutis_triggerit'
    )),
    ehto_arvo JSONB,                           -- {"threshold": -5, "unit": "percent"}
    aktiivinen BOOLEAN DEFAULT true,
    viimeksi_lauennut TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Portfoliot
CREATE TABLE portfoliot (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kayttaja_id UUID REFERENCES kayttajat(id) ON DELETE CASCADE,
    nimi VARCHAR(100) DEFAULT 'Oma salkku',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE portfolio_osakkeet (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES portfoliot(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    maara DECIMAL(12,4) NOT NULL,              -- Osakkeiden lukumäärä
    hankintahinta_eur DECIMAL(12,4),           -- Keskihankintahinta per osake
    hankintapaiva DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(portfolio_id, ticker)
);

-- Indeksit
CREATE INDEX idx_kayttajat_email ON kayttajat(email);
CREATE INDEX idx_kayttajat_telegram ON kayttajat(telegram_chat_id);
CREATE INDEX idx_credit_saldot_kayttaja ON credit_saldot(kayttaja_id, kuukausi DESC);
CREATE INDEX idx_credit_tapahtumat_kayttaja ON credit_tapahtumat(kayttaja_id, created_at DESC);
CREATE INDEX idx_halytykset_kayttaja ON halytykset(kayttaja_id, aktiivinen);
CREATE INDEX idx_halytykset_ticker ON halytykset(ticker, aktiivinen);
CREATE INDEX idx_portfolio_osakkeet_portfolio ON portfolio_osakkeet(portfolio_id);
```

### Telegram-botin arkkitehtuuri

```python
# bot/telegram_bot.py — karkea arkkitehtuuri

"""
Komennot:
  /analysoi NOKIA        → Aja täysi multi-agent analyysi
  /pika NOKIA            → Kevyt analyysi (tekninen + sentimentti)
  /salkku                → Näytä oma portfolio ja sen tila
  /lisaa NOKIA 100 4.50  → Lisää 100 Nokiaa hintaan 4.50€
  /poista NOKIA          → Poista osake salkusta
  /halytys NOKIA -5%     → Ilmoita kun Nokia laskee 5%
  /saldo                 → Näytä credit-saldo
  /tilaus                → Päivitä tilaus (linkki web-dashboardiin)
  /apu                   → Ohjeteksti
  
Flow:
  1. Käyttäjä lähettää /analysoi NOKIA
  2. Botti tarkistaa credit-saldon
  3. Jos saldo riittää → käynnistä TradingAgentsGraph.propagate()
  4. Lähetä "Agentit analysoivat Nokiaa..." -viesti
  5. Päivitä viesti agentti kerrallaan:
     "✅ Fundamenttianalyysi valmis"
     "✅ Sentimenttianalyysi valmis"
     "⏳ Tutkijat väittelevät..."
     "✅ Kauppias on tehnyt ehdotuksen"
     "✅ Riskianalyysi valmis"
  6. Lähetä lopullinen päätös formatoituna:
  
     ┌─────────────────────────────┐
     │  📊 NOKIA — AI-analyysi     │
     │  24.3.2026                  │
     │                             │
     │  🟢 OSTA                    │
     │  Luottamus: 72%             │
     │                             │
     │  📋 Tiivistelmä:            │
     │  Fundamentit vahvat...      │
     │  Sentimentti nouseva...     │
     │                             │
     │  ⚠️ Riskit:                 │
     │  Valuuttariski (USD/EUR)    │
     │                             │
     │  💰 Verohuomio:             │
     │  Jos myyt 100 kpl @ 4.80€, │
     │  pääomavero ~X€             │
     │                             │
     │  ⚖️ Tämä EI ole sijoitus-  │
     │  neuvontaa. Tee omat       │
     │  päätöksesi.                │
     └─────────────────────────────┘
  
  7. Vähennä 1 credit saldosta
"""
```

### Suomalainen verolaskuri

```python
# integrations/vero/paaomavero.py

"""
Suomalainen pääomaverolaskuri osakekauppoihin.

Säännöt (2026):
  - Pääomatulo ≤ 30 000€/vuosi → 30% vero
  - Pääomatulo > 30 000€/vuosi → 34% ylimenevältä osalta
  - Luovutusvoitto = myyntihinta - hankintahinta - kulut
  - Hankintameno-olettama: 20% (omistettu < 10v) tai 40% (≥ 10v)
    → käytetään jos edullisempi kuin todellinen hankintahinta
  - Pienet luovutukset: verovapaita jos vuoden myyntihinnat yhteensä ≤ 1000€

Integraatio agenttianalyysiin:
  - Salkunhoitaja-agentti sisällyttää verovaikutuksen päätökseen
  - "Jos myyt nyt → vero X€. Jos odotat 3kk → tilanne voi muuttua näin."
  - Portfolionäkymässä: unrealized gains/losses + veroarvio
"""

def laske_paaomavero(
    myyntihinta: float,
    hankintahinta: float,
    kulut: float,
    omistusaika_vuosia: float,
    muut_paaomatulot_vuonna: float = 0,
) -> dict:
    """
    Palauttaa:
      {
        "luovutusvoitto": float,
        "vero_todellinen": float,      # Todellisilla hankintahinnoilla
        "vero_olettama": float,        # Hankintameno-olettamalla
        "edullisempi": str,            # "todellinen" tai "olettama"
        "maksettava_vero": float,      # Edullisempi vaihtoehto
        "efektiivinen_veroprosentti": float,
        "selitys": str,                # Suomenkielinen selitys
      }
    """
    pass  # Toteutetaan vaiheessa 6
```

### Hälytysjärjestelmän arkkitehtuuri

```python
# integrations/alerts/monitor.py

"""
Portfoliomonitori pyörii Docker-kontissa taustaprosessina.

Seurattavat tapahtumat:
  1. Hintamuutokset (käyttäjän asettamat rajat)
  2. Sentimenttimuutokset (kun Kauppalehti/Inderes julkaisee uutta)
  3. Tekniset signaalit (RSI, MACD crossover jne.)
  4. Tulosjulkistuspäivät (automaattinen ilmoitus 1 päivä ennen)
  5. Agenttien suosituksen muutos (edellinen OSTA → nyt MYY)

Flow:
  1. Cron joka 15min: hae portfolioiden osakkeiden hinnat
  2. Vertaa käyttäjien hälytyksiin
  3. Jos hälytys laukeaa → notifier.py → Telegram/email/push
  4. Kerran päivässä: kevyt sentimenttiskannaus portfolio-osakkeille
  5. Credit-kulutus: 0.1 credit/osake/päivä portfolioseurannasta
"""
```

### Docker Compose -laajennus kaupallistamiseen

```yaml
# Lisättävä docker-compose.yml:ään:

  # ── Telegram-botti ──────────────────────────────────
  telegram-bot:
    build:
      context: .
      dockerfile: Dockerfile
    command: python -m bot.telegram_bot
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    environment:
      DATABASE_URL: postgresql://${DB_USER:-kauppa}:${DB_PASSWORD:-dev_salasana}@db:5432/kauppa_agentit
      REDIS_URL: redis://redis:6379/0
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      ALPHA_VANTAGE_API_KEY: ${ALPHA_VANTAGE_API_KEY}
    restart: unless-stopped

  # ── Portfolio-monitori (hälytykset) ─────────────────
  monitor:
    build:
      context: .
      dockerfile: Dockerfile
    command: python -m integrations.alerts.monitor
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    environment:
      DATABASE_URL: postgresql://${DB_USER:-kauppa}:${DB_PASSWORD:-dev_salasana}@db:5432/kauppa_agentit
      REDIS_URL: redis://redis:6379/0
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    restart: unless-stopped

  # ── Stripe webhook -vastaanotin ─────────────────────
  stripe-webhook:
    build:
      context: .
      dockerfile: Dockerfile
    command: python -m credits.stripe_webhook_server
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://${DB_USER:-kauppa}:${DB_PASSWORD:-dev_salasana}@db:5432/kauppa_agentit
      STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
      STRIPE_WEBHOOK_SECRET: ${STRIPE_WEBHOOK_SECRET}
    ports:
      - "8001:8001"
    restart: unless-stopped
```

## Regulaatio ja Finanssivalvonta

### Juridinen status

Työkalu myydään **analyysityökaluna** (kuten Bloomberg Terminal, TrendSpider, Inderesin analyysit), EI sijoitusneuvontana. Tämä tarkoittaa:

1. **Ei tarvita Fiva-toimilupaa** kunhan:
   - Ei anneta yksilöllistä sijoitussuositusta ("sinun kannattaa ostaa")
   - Käytetään aina yleisluontoista muotoa ("agentit analysoivat, käyttäjä päättää")
   - Vastuuvapautus AINA näkyvissä
   - Ei luvata tuottoja

2. **MiFID II -vaatimukset** eivät koske jos:
   - Ei välitetä toimeksiantoja
   - Ei hallinnoida varoja
   - Ei anneta henkilökohtaista suositusta

3. **Ennen lanseerausta:**
   - Ota yhteyttä Finanssivalvonnan Innovation Help Deskiin (maksuton)
   - Pyydä ennakollinen arvio toimintamallista
   - Dokumentoi miten työkalu eroaa sijoitusneuvonnasta

### Pakolliset vastuuvapautukset

```
LYHYT (joka analyysiraportti):
"⚖️ Tämä on AI:n tuottama analyysi, ei sijoitussuositus. 
Tee sijoituspäätökset oman harkintasi mukaan."

PITKÄ (rekisteröityminen + asetukset):
"KauppaAgentit on tekoälyyn perustuva analyysityökalu tutkimus- ja 
oppimistarkoituksiin. Palvelu EI ole Finanssivalvonnan valvomaa 
sijoitusneuvontaa eikä -suositusta. AI-analyysin tulokset voivat 
olla virheellisiä tai vanhentuneita. Tekoälymallit eivät ennusta 
tulevaisuutta. Sijoittamiseen liittyy aina riski pääoman menettämisestä. 
Tee sijoituspäätöksesi oman harkintasi ja tarvittaessa 
toimiluvan saaneen sijoitusneuvojan avustuksella."
```

## API-kustannusten hallinta

### Kustannusarvio per analyysi

```
Yksi täysi analyysi (kaikki agentit, 1 väittelykierros):
  - 4 analyytikkoa × ~2000 tokenia kukin     = ~8 000 tokenia
  - 2 tutkijaa × 1 väittelykierros × ~3000   = ~6 000 tokenia
  - Kauppias                                   = ~2 000 tokenia
  - Riskienhallinta                            = ~2 000 tokenia
  - Salkunhoitaja                              = ~1 500 tokenia
  - Yhteensä: ~20 000 tokenia (input + output)
  
  Claude Sonnet: ~$0.015 per analyysi
  Claude Haiku (quick tasks): ~$0.003 per analyysi
  Yhdistettynä: ~$0.01-0.02 per analyysi = ~0.01-0.02 €

  → 19€/kk tilauksella (120 analyysiä): kustannus ~1.20-2.40€ → marginaali 87-94%
  → Ilmainen taso (30 analyysiä): kustannus ~0.30-0.60€/käyttäjä/kk
```

### Budjettisäännöt

- Redis-cache estää saman analyysin toistamisen (24h TTL)
- Ilmaiset käyttäjät: Haiku-malli oletuksena (halvempi)
- Pro-käyttäjät: Sonnet-malli (parempi laatu)
- Business: Opus saatavilla (paras laatu, kallis)
- Kuukausittainen API-budjettikatto per käyttäjä + globaali katto

## Muistiinpanoja Claudelle

### TÄRKEÄ: Session aloitus ja lopetus
- **AINA** lue CLAUDE.md ennen kuin teet mitään — se on projektin ainoa totuuslähde
- **AINA** päivitä Kehityksen vaiheet -checkboxit kun tehtävä valmistuu
- Jos teet muutoksen joka vaikuttaa arkkitehtuuriin, päivitä myös relevantti kohta CLAUDE.md:ssä

### Yleinen
- Tämä on FORK — muokkaa upstreamia mahdollisimman vähän, lisää omat tiedostot
- Käytä context7-MCP:tä LangGraph-dokumentaatioon ennen kuin muokkaat graph-koodia
- Käytä claude-context MCP:tä kun etsit upstreamin koodista tiettyä logiikkaa
- Kohderyhmä on suomalainen peruskäyttäjä — ei DBA, ei quant, ei devaaja

### Regulaatio
- AINA vastuuvapautus mukana — tämä EI OLE sijoitusneuvontaa
- Älä käytä sanoja "suosittelen", "kannattaa ostaa/myydä" — käytä "agentit analysoivat", "analyysin tulos"
- Jokainen päätös on "OSTA-signaali / PIDÄ-signaali / MYY-signaali", ei "suositus"

### Tekninen
- Suosi Anthropic-malleja (Claude) LLM-providerina koska se on meidän ympäristö
- `deep_think_llm` = "claude-haiku-4-5-20251001" (testaus, ~€0.05/ajo) — vaihda Sonnetiin tuotannossa
- Älä tee turhia muutoksia upstream-tiedostoihin — helpompi synkata myöhemmin
- Testaa aina suomalaisilla osakkeilla (NOKIA, NORDEA, NESTE, UPM, KONE)
- EUR-denominaatio kaikkialla, ei dollareita
- Docker-ympäristö AINA — ei asenneta suoraan host-koneelle
- Uutisanalyytikko: käytä `get_all_stock_news_combined` (1 tool call) eikä 3 erillistä kutsua

### Kustannushallinta
- Haiku: ~€0.50/ajo (4 analyytikkoa), Sonnet: ~€1.50+/ajo — kustannus tulee akkumuloituneesta viestihistoriasta
- **TEST_MODE=true** (.env) → kaikki 4 analyytikkoa + max_tokens=500 per agentti → halvemmat, lyhyemmät raportit
- SQLite LLM-cache (.llm_cache.db) — samat API-kutsut palauttavat välimuistista, ei uusia kustannuksia
- Tuotannossa: TEST_MODE=false tai poista → täydet tokenirajat (oletusarvot)
- `get_all_stock_news_combined` säästää ~50 % LLM-pyörähdyksistä uutisanalyytikossa
- Jokainen tool call = yksi LLM-pyörähdys = kuluja → minimoi tool callien määrä
- `deep_think_llm` = Haiku testauksessa, vaihda Sonnetiin kun analysointitarkkuus tärkeää

### Priorisointi
- Toimiva fork ensin → lokalisointi → Telegram-botti → Web-UI → creditit → portfolio → B2B
- Jokainen vaihe pitää olla itsenäisesti julkaistavissa
- Telegram-botti on nopein tie käyttäjiin ja palautteeseen

