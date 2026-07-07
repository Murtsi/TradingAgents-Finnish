# Autotrader Railway -käyttöönotto

KauppaAgentit-autotrader on tässä vaiheessa vain paper/SIM-käytössä. Live-kaupankäynti ei ole mukana.

## Palvelut

Luo Railwayhin Postgres-plugin ja kaksi serviceä samasta reposta:

- Worker: `python -m autotrader.scheduler`
- Telegram-botti: `python -m telegram_bot.bot`

Docker-kuva lukee palvelukohtaisen komennon ympäristömuuttujasta:

```text
APP_COMMAND=python -m autotrader.scheduler
```

Suositeltu palvelujako:

- `autotrader-worker`: nykyinen SIM/dry-run worker. Käynnistys `python -m autotrader.scheduler`.
- `telegram-bot`: botin oma service. Käynnistys `python -m telegram_bot.bot`.
- `frontend`: erillinen service myöhemmälle web-UI:lle. Ei vielä ajettavaa frontend-koodia tässä repoversiossa.
- `live-trader`: erillinen Phase 3 -service. Ei kytketä ennen OAuth-, täsmäytys- ja julkaisuporttia.

Vaihtoehto Railway Cronille:

```bash
python -m autotrader.scheduler --once
```

## Pakolliset ympäristömuuttujat

```text
DATABASE_URL=<Railway Postgres URL>
BROKER=saxo
SAXO_ENV=sim
SAXO_TOKEN=<24h Saxo SIM one-day token>
AUTOTRADER_DRY_RUN=0
AUTOTRADER_RUN_TIME=09:15
AUTOTRADER_TIMEZONE=Europe/Helsinki
TELEGRAM_BOT_TOKEN=<bot token>
TELEGRAM_CHAT_ID=<daily report chat id>
TELEGRAM_WHITELIST=<comma-separated Telegram user ids>
ANTHROPIC_API_KEY=<server-side key>
```

Live-portti on tarkoituksella suljettu. `SAXO_ENV=live` vaatii `ALLOW_LIVE=1`, mutta tämä vaihe hylkää live-adapterin silti, koska OAuth- ja täsmäytyspolku eivät ole mukana.

## Vaiheet

Phase 1: SIM paper trader, DB-audit trail, Telegram-raportti ja muistibroker-testit.

Phase 2: Saxo SIM -validointi oikeilla tunnuksilla, UIC-kartoituksen tarkistus ja toteutuneiden toimeksiantojen täsmäytys.

Phase 3: Live + OAuth code grant, refresh-token hallinta, broker reconciliation ja erillinen julkaisuportti.

## Vastuuvapautus

Tämä on AI:n tuottama analyysi, ei sijoitussuositus. Tee sijoituspäätökset oman harkintasi mukaan.
