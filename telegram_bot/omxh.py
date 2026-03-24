"""Ohut wrapper ticker-validoinnille ja hinnan haulle."""
import logging
import yfinance as yf
from tradingagents.dataflows.omxh_utils import get_omxh_current_price, resolve_ticker

logger = logging.getLogger(__name__)


def get_current_price(ticker: str) -> float | None:
    """Hakee viimeisimmän kurssin EUR. Palauttaa None virhetilanteessa."""
    try:
        return get_omxh_current_price(ticker)
    except Exception as e:
        logger.warning(f"Hinnan haku epäonnistui {ticker}: {e}")
        return None


def validate_ticker(ticker: str) -> str | None:
    """
    Validoi ticker Yahoo Financesta ennen analyysin käynnistystä.
    Palauttaa Yahoo Finance -tunnuksen (esim. NOKIA.HE) tai None jos ei löydy.
    """
    try:
        yf_ticker = resolve_ticker(ticker)
        info = yf.Ticker(yf_ticker).fast_info
        if info.last_price and info.last_price > 0:
            return yf_ticker
        return None
    except Exception as e:
        logger.warning(f"Ticker-validointi epäonnistui {ticker}: {e}")
        return None
