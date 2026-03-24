from telegram_bot.progress import _build_progress_message, ALL_STAGES

def test_build_progress_empty():
    msg = _build_progress_message("NOKIA", completed=[], current=None)
    assert "NOKIA" in msg
    for stage in ALL_STAGES:
        assert f"⏳ {stage}" in msg

def test_build_progress_one_completed():
    msg = _build_progress_message("NOKIA", completed=["Fundamenttianalyysi"], current=None)
    assert "✅ Fundamenttianalyysi" in msg
    assert "⏳ Tekninen analyysi" in msg

def test_build_progress_current_stage():
    msg = _build_progress_message("NOKIA", completed=[], current="Sentimenttianalyysi")
    assert "🔄 Sentimenttianalyysi käynnissä..." in msg

def test_build_progress_mixed():
    msg = _build_progress_message(
        "NOKIA",
        completed=["Fundamenttianalyysi", "Sentimenttianalyysi"],
        current="Uutisanalyysi",
    )
    assert "✅ Fundamenttianalyysi" in msg
    assert "✅ Sentimenttianalyysi" in msg
    assert "🔄 Uutisanalyysi käynnissä..." in msg
    assert "⏳ Tekninen analyysi" in msg
