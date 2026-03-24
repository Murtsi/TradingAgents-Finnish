"""
KauppaAgentit Telegram-botti — entry point.

Käynnistys projektin juuresta:
    python -m telegram_bot.bot

Vaatii .env tai ympäristömuuttujat:
    TELEGRAM_BOT_TOKEN=...
    TELEGRAM_WHITELIST=123456789,...
    ANTHROPIC_API_KEY=...
"""
from __future__ import annotations
import logging
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from telegram_bot.handlers import analysoi_command, full_report_callback
from tradingagents.llm_cache import setup_llm_cache

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN puuttuu .env-tiedostosta!")

    whitelist = os.getenv("TELEGRAM_WHITELIST", "")
    if not whitelist.strip():
        logger.warning("TELEGRAM_WHITELIST on tyhjä — kukaan ei pysty käyttämään bottia!")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("analysoi", analysoi_command))
    app.add_handler(CallbackQueryHandler(full_report_callback, pattern=r"^raportti:"))

    # Aktivoi pysyvä LLM-vastausten välimuisti (SQLite)
    # Samat API-kutsut palautuvat välimuistista ilman uusia kustannuksia
    setup_llm_cache()

    logger.info("🤖 KauppaAgentit-botti käynnistyy...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
