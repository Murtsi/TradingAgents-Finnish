-- Migraatio 001: Alkuperäinen skeema
-- Aja: psql $DATABASE_URL -f db/migrations/001_initial.sql

\i db/schema.sql

-- Merkitse migraatio ajetuksi
CREATE TABLE IF NOT EXISTS migraatiot (
    id      SERIAL PRIMARY KEY,
    nimi    VARCHAR(100) UNIQUE NOT NULL,
    ajettu  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO migraatiot (nimi) VALUES ('001_initial')
    ON CONFLICT (nimi) DO NOTHING;
