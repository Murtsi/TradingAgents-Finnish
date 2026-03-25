from __future__ import annotations
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from telegram_bot.whitelist import is_allowed
from telegram_bot.omxh import validate_ticker
from telegram_bot.task_runner import run_analysis
from telegram_bot.formatter import format_full_report_parts, _strip_markdown as _strip_markdown_import

logger = logging.getLogger(__name__)


def _split_at_newline(text: str, limit: int) -> list[str]:
    """
    Jakaa pitkän tekstin palasiin enintään `limit` merkin kokoisiin osiin.
    Katkaisee rivinvaihdon kohdalta — ei koskaan sanan tai lauseen keskeltä.
    """
    chunks: list[str] = []
    while len(text) > limit:
        # Etsi viimeisin rivinvaihto enintään `limit` merkin kohdalta
        cut = text.rfind("\n", 0, limit)
        if cut <= 0:
            # Ei rivinvaihtoa — katkaistaan välilyönnistä
            cut = text.rfind(" ", 0, limit)
        if cut <= 0:
            # Viimeinen vaihtoehto — kovakoodattu raja
            cut = limit
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks


# Globaali lukko — estää samanaikaiset analyysit
# Omistetaan handlers.py:ssä: Lock on handler-tason logiikkaa, ei task_runner-tason
analysis_lock = asyncio.Lock()

# Tallennetaan koko raportit ja tilat muistiin inline-nappia varten
# { message_id: full_report_text / state_dict }
# Huom: Kasvaa rajattomasti pitkässä ajossa — riittää suljetulle ryhmälle MVP:ssä
_full_reports: dict[int, str] = {}
_full_states: dict[int, dict] = {}


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

    raw_ticker = " ".join(args).upper().strip()

    # 3. Lock — estä rinnakkainen ajo
    if analysis_lock.locked():
        await update.message.reply_text("[ODOTA] Analyysi on jo käynnissä. Odota tulosta.")
        return

    # 4. Ticker-validointi Yahoo Financesta
    await update.message.reply_text(f"Tarkistetaan osake {raw_ticker}...")
    yf_ticker = validate_ticker(raw_ticker)
    if yf_ticker is None:
        await update.message.reply_text(
            f"[VIRHE] En löydä osaketta *{raw_ticker}*\n"
            f"Kokeile esim. /analysoi NOKIA tai /analysoi NESTE",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # 5. Progress-viesti
    progress_msg = await update.message.reply_text(
        f"Analysoin: *{raw_ticker}*\n━━━━━━━━━━━━━━━━━━━━━\nAloitetaan...",
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
            summary, full_report, final_state = await run_analysis(yf_ticker, edit_progress)
        except asyncio.TimeoutError:
            logger.warning(f"Analyysi timeout: {yf_ticker}")
            await progress_msg.edit_text(
                "[ODOTA] Analyysi kestää odotettua kauemmin — lähetan tuloksen kun valmis."
            )
            return
        except Exception as e:
            logger.error(f"Analyysi epäonnistui {yf_ticker}: {e}", exc_info=True)
            await progress_msg.edit_text(
                "[VIRHE] Analyysi epäonnistui. Yritä hetken kuluttua uudelleen."
            )
            return

    # 7. Lähetä tulos + [Koko raportti] -nappi
    # Kokeile Markdown ensin, fallback plain text jos parse epäonnistuu
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Koko raportti", callback_data=f"raportti:{raw_ticker}")
    ]])
    try:
        result_msg = await update.message.reply_text(
            summary,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
    except Exception:
        result_msg = await update.message.reply_text(
            summary,
            reply_markup=keyboard,
        )
    _full_reports[result_msg.message_id] = full_report
    _full_states[result_msg.message_id] = final_state
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
            "[VIRHE] Raportti ei ole enää saatavilla. Aja /analysoi uudelleen."
        )
        return

    # Hae alkuperäinen state full_report-avaimesta (tallennetaan alla)
    state = _full_states.get(query.message.message_id)
    if state:
        for part in format_full_report_parts(state):
            try:
                await query.message.reply_text(part, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                # Fallback plain text jos Markdown-parseri kaatuu agenttisisällöstä
                await query.message.reply_text(_strip_markdown_import(part))
    else:
        # Fallback vanhalle tekstipohjaiselle jaolle
        for chunk in _split_at_newline(full_report, 4000):
            await query.message.reply_text(chunk)
