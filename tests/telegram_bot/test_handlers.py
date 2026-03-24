import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_update(user_id: int, args: list[str]):
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = "testuser"
    reply_mock = MagicMock()
    reply_mock.message_id = 42
    reply_mock.edit_text = AsyncMock()
    reply_mock.delete = AsyncMock()
    update.message.reply_text = AsyncMock(return_value=reply_mock)
    context = MagicMock()
    context.args = args
    return update, context


@pytest.mark.asyncio
async def test_handler_rejects_unknown_user():
    """Tuntematonta käyttäjää ei vastaukseen."""
    with patch("telegram_bot.handlers.is_allowed", return_value=False):
        from telegram_bot.handlers import analysoi_command
        update, context = make_update(user_id=999, args=["NOKIA"])
        await analysoi_command(update, context)
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_handler_missing_args():
    """Ilman argumenttia näytetään käyttöohje."""
    with patch("telegram_bot.handlers.is_allowed", return_value=True):
        from telegram_bot.handlers import analysoi_command
        update, context = make_update(user_id=42, args=[])
        await analysoi_command(update, context)
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args[0][0]
    assert "/analysoi" in call_args


@pytest.mark.asyncio
async def test_handler_invalid_ticker():
    """Tuntematon ticker näyttää virheviestin."""
    with patch("telegram_bot.handlers.is_allowed", return_value=True), \
         patch("telegram_bot.handlers.validate_ticker", return_value=None):
        from telegram_bot.handlers import analysoi_command
        update, context = make_update(user_id=42, args=["HÖLYNPÖLY"])
        await analysoi_command(update, context)
    assert update.message.reply_text.call_count >= 2


@pytest.mark.asyncio
async def test_handler_lock_busy():
    """Jos Lock on varattuna, näytetään 'jo käynnissä' -viesti."""
    # Importataan tuore moduuli jotta lock on alkutilassa
    import importlib
    import telegram_bot.handlers as handlers_mod
    importlib.reload(handlers_mod)

    await handlers_mod.analysis_lock.acquire()
    try:
        with patch("telegram_bot.handlers.is_allowed", return_value=True), \
             patch("telegram_bot.handlers.validate_ticker", return_value="NOKIA.HE"):
            update, context = make_update(user_id=42, args=["NOKIA"])
            await handlers_mod.analysoi_command(update, context)
        last_call = update.message.reply_text.call_args[0][0]
        assert "käynnissä" in last_call
    finally:
        handlers_mod.analysis_lock.release()
