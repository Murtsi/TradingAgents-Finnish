-- =============================================
-- KauppaAgentit — PostgreSQL-skeema
-- =============================================
-- Versio: 1.1 (korjattu taulunnimet)
-- Kuvaus: Analyysitulosten, päätösten ja
--         portfolion seurantadata

-- =============================================
-- Analyysiajojen metadata
-- =============================================
CREATE TABLE IF NOT EXISTS analyysit (
    id              SERIAL PRIMARY KEY,
    luotu           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ticker          VARCHAR(20)  NOT NULL,   -- esim. "NOKIA.HE"
    yhtion_nimi     VARCHAR(100),            -- esim. "Nokia Oyj"
    analyysi_pvm    DATE        NOT NULL,    -- analysoitava kaupankäyntipäivä
    llm_provider    VARCHAR(50),             -- "anthropic", "openai"
    llm_malli       VARCHAR(100),            -- "claude-sonnet-4-20250514"
    kesto_sek       NUMERIC(8,2),            -- ajon kesto sekunteina
    virhe           TEXT                     -- NULL jos onnistui
);

-- =============================================
-- Agenttien raportit
-- =============================================
CREATE TABLE IF NOT EXISTS agentiraportit (
    id              SERIAL PRIMARY KEY,
    analyysi_id     INTEGER NOT NULL REFERENCES analyysit(id) ON DELETE CASCADE,
    agentti         VARCHAR(50) NOT NULL,    -- "fundamentti", "sentimentti", jne.
    raportti        TEXT        NOT NULL,    -- Agentin tuottama raportti
    luotu           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agentiraportit_analyysi
    ON agentiraportit(analyysi_id);

-- =============================================
-- Kaupankäyntipäätökset
-- =============================================
CREATE TABLE IF NOT EXISTS paatokset (
    id              SERIAL PRIMARY KEY,
    analyysi_id     INTEGER NOT NULL REFERENCES analyysit(id) ON DELETE CASCADE,
    luotu           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Lopullinen suositus
    suositus        VARCHAR(10) NOT NULL     -- 'OSTA', 'PIDÄ', 'MYY'
                    CHECK (suositus IN ('OSTA', 'PIDÄ', 'MYY')),
    luottamustaso   VARCHAR(20)              -- 'Korkea', 'Keskisuuri', 'Matala'
                    CHECK (luottamustaso IN ('Korkea', 'Keskisuuri', 'Matala')),

    -- Hintatiedot analyysipäivänä
    hinta_eur       NUMERIC(12,4),           -- kurssi analyysihetkellä
    hintatavoite_eur NUMERIC(12,4),          -- analyytikon hintatavoite

    -- Raporttisisältö
    yhteenveto      TEXT,                    -- Salkunhoitajan yhteenveto
    perustelut      TEXT,                    -- Täydet perustelut
    riskiarvio      TEXT,                    -- Riskienhallinnan arvio
    vastuuvapautus  TEXT NOT NULL            -- Pakollinen disclaimer
);

CREATE INDEX IF NOT EXISTS idx_paatokset_analyysi ON paatokset(analyysi_id);
CREATE INDEX IF NOT EXISTS idx_paatokset_ticker   ON paatokset(analyysi_id);

-- =============================================
-- Portfolio-seuranta (valinnainen)
-- =============================================
CREATE TABLE IF NOT EXISTS portfolio (
    id              SERIAL PRIMARY KEY,
    luotu           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    muokattu        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    ticker          VARCHAR(20) NOT NULL,
    yhtion_nimi     VARCHAR(100),
    kappaleet       NUMERIC(12,4) NOT NULL,  -- omistettu määrä
    osto_hinta_eur  NUMERIC(12,4) NOT NULL,  -- keskimääräinen ostohinta
    osto_pvm        DATE         NOT NULL,

    muistiinpano    TEXT
);

CREATE INDEX IF NOT EXISTS idx_portfolio_ticker ON portfolio(ticker);

-- =============================================
-- Hintahistoria (cache)
-- =============================================
CREATE TABLE IF NOT EXISTS hintahistoria (
    id              SERIAL PRIMARY KEY,
    ticker          VARCHAR(20)  NOT NULL,
    pvm             DATE        NOT NULL,
    avaus_eur       NUMERIC(12,4),
    korkein_eur     NUMERIC(12,4),
    matalin_eur     NUMERIC(12,4),
    sulkeminen_eur  NUMERIC(12,4),
    volyymi         BIGINT,
    haettu          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (ticker, pvm)
);

CREATE INDEX IF NOT EXISTS idx_hintahistoria_ticker_pvm
    ON hintahistoria(ticker, pvm DESC);

-- =============================================
-- Kommentit
-- =============================================
COMMENT ON TABLE analyysit       IS 'Jokainen agenttiprosessin ajo tallentuu tähän';
COMMENT ON TABLE agentiraportit  IS 'Yksittäisten agenttien tuottamat raportit';
COMMENT ON TABLE paatokset       IS 'Salkunhoitajan lopullinen OSTA/PIDÄ/MYY-päätös';
COMMENT ON TABLE portfolio       IS 'Käyttäjän seurattavat positiot (valinnainen)';
COMMENT ON TABLE hintahistoria   IS 'Yahoo Finance -datan paikallinen välimuisti';
