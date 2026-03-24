# KauppaAgentit Telegram-botti

## Käynnistys

1. Hanki bot token: Telegram → @BotFather → /newbot
2. Hanki oma Telegram-ID: Telegram → @userinfobot
3. Lisää .env-tiedostoon:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
   TELEGRAM_WHITELIST=123456789
   ANTHROPIC_API_KEY=sk-ant-...
   ```
4. Käynnistä projektin juuresta:
   ```bash
   python -m telegram_bot.bot
   ```

## Komennot

| Komento | Kuvaus |
|---------|--------|
| `/analysoi NOKIA` | Täysi osakeanalyysi (kestää 1–5 min) |

## Osakeesimerkkejä (OMXH)

| Nimi | Komento |
|------|---------|
| Nokia | `/analysoi NOKIA` |
| Nordea | `/analysoi NORDEA` |
| Neste | `/analysoi NESTE` |
| KONE | `/analysoi KONE` |
| UPM | `/analysoi UPM` |
