-- Migraatio 002: Autotrader + Telegram-persistenssi
-- Aja: psql $DATABASE_URL -f db/migrations/002_autotrader.sql

\i db/schema.sql

CREATE TABLE IF NOT EXISTS migraatiot (
    id      SERIAL PRIMARY KEY,
    nimi    VARCHAR(100) UNIQUE NOT NULL,
    ajettu  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO migraatiot (nimi) VALUES ('002_autotrader')
    ON CONFLICT (nimi) DO NOTHING;
