from __future__ import annotations
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from telegram_bot.whitelist import is_allowed
from telegram_bot.omxh import validate_ticker
from telegram_bot.task_runner import run_analysis

logger = logging.getLogger(__name__)

# Globaali lukko — estää samanaikaiset analyysit
# Omistetaan handlers.py:ssä: Lock on handler-tason logiikkaa, ei task_runner-tason
analysis_lock = asyncio.Lock()

# Tallennetaan koko raportit muistiin inline-nappia varten
# { message_id: full_report_text }
# Huom: Kasvaa rajattomasti pitkässä ajossa — riittää suljetulle ryhmälle MVP:ssä
_full_reports: dict[int, str] = {}


async def analysoi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/analysoi [TICKER] -komennon käsittelijä."""
    user_id = update.effective_user.id

    # 1. Whitelist — hiljaisuus tuntemattomille, loki serverille
    if not is_allowed(user_id):
        logger.warning(f"Whitelist-esto: {user_id} (@{update.effective_user.username})")
        return

    # 2. Argumenttitarkistus
    args = context.args
    if not args:
        await update.message.reply_text("Käyttö: /analysoi [OSAKE]\nEsim: /analysoi NOKIA")
        return

    raw_ticker = args[0].upper().strip()

    # 3. Lock — estä rinnakkainen ajo
    if analysis_lock.locked():
        await update.message.reply_text("⏳ Analyysi on jo käynnissä. Odota tulosta.")
        return

    # 4. Ticker-validointi Yahoo Financesta
    await update.message.reply_text(f"🔍 Tarkistetaan osake {raw_ticker}...")
    yf_ticker = validate_ticker(raw_ticker)
    if yf_ticker is None:
        await update.message.reply_text(
            f"❌ En löydä osaketta *{raw_ticker}*\n"
            f"Kokeile esim. /analysoi NOKIA tai /analysoi NESTE",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # 5. Progress-viesti
    progress_msg = await update.message.reply_text(
        f"📊 Analysoin: *{raw_ticker}*\n━━━━━━━━━━━━━━━━━━━━━\n⏳ Aloitetaan...",
        parse_mode=ParseMode.MARKDOWN,
    )

    async def edit_progress(text: str) -> None:
        try:
            await progress_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass  # Ignoroidaan "message not modified" -virhe

    # 6. Aja analyysi lukolla — timeout ja muut virheet käsitellään erikseen
    async with analysis_lock:
        try:
            summary, full_report = await run_analysis(yf_ticker, edit_progress)
        except asyncio.TimeoutError:
            logger.warning(f"Analyysi timeout: {yf_ticker}")
            await progress_msg.edit_text(
                "⏳ Analyysi kestää odotettua kauemmin — lähetan tuloksen kun valmis."
            )
            return
        except Exception as e:
            logger.error(f"Analyysi epäonnistui {yf_ticker}: {e}", exc_info=True)
            await progress_msg.edit_text(
                "❌ Analyysi epäonnistui. Yritä hetken kuluttua uudelleen."
            )
            return

    # 7. Lähetä tulos + [📄 Koko raportti] -nappi
    result_msg = await update.message.reply_text(
        summary,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📄 Koko raportti", callback_data=f"raportti:{raw_ticker}")
        ]]),
    )
    _full_reports[result_msg.message_id] = full_report
    await progress_msg.delete()


async def full_report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """[📄 Koko raportti] -napin käsittelijä."""
    query = update.callback_query
    await query.answer()

    if not is_allowed(query.from_user.id):
        return

    full_report = _full_reports.get(query.message.message_id)
    if not full_report:
        await query.message.reply_text(
            "❌ Raportti ei ole enää saatavilla. Aja /analysoi uudelleen."
        )
        return

    # Jaa 4000 merkin palasiin (Telegram max 4096)
    LIMIT = 4000
    for chunk in [full_report[i:i+LIMIT] for i in range(0, len(full_report), LIMIT)]:
        await query.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
