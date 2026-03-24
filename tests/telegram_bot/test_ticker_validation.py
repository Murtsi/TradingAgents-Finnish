from unittest.mock import patch, MagicMock
from telegram_bot.omxh import validate_ticker

def test_validate_ticker_known_alias():
    mock_info = MagicMock()
    mock_info.last_price = 4.23
    with patch("telegram_bot.omxh.yf.Ticker") as mock_yf:
        mock_yf.return_value.fast_info = mock_info
        result = validate_ticker("NOKIA")
    assert result == "NOKIA.HE"

def test_validate_ticker_invalid_returns_none():
    mock_info = MagicMock()
    mock_info.last_price = None
    with patch("telegram_bot.omxh.yf.Ticker") as mock_yf:
        mock_yf.return_value.fast_info = mock_info
        result = validate_ticker("HÖLYNPÖLY123")
    assert result is None

def test_validate_ticker_already_has_he_suffix():
    mock_info = MagicMock()
    mock_info.last_price = 4.23
    with patch("telegram_bot.omxh.yf.Ticker") as mock_yf:
        mock_yf.return_value.fast_info = mock_info
        result = validate_ticker("NOKIA.HE")
    assert result == "NOKIA.HE"
