"""
OMXH-datasyöte — Helsingin pörssi
===================================
Hakee Helsingin pörssin (OMXH) osakedata Yahoo Financen kautta.
Yahoo Finance käyttää .HE-suffiksia OMXH-osakkeille (esim. NOKIA.HE).

FORK: Suomi-lokalisointi — uusi tiedosto
"""

from __future__ import annotations

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

# Tunnetut OMXH-osakkeet ja niiden Yahoo Finance -tunnukset
OMXH_TICKERS: dict[str, str] = {
    # Suuryhtiöt (Large Cap)
    "NOKIA": "NOKIA.HE",
    "NORDEA": "NDA-FI.HE",
    "NESTE": "NESTE.HE",
    "UPM": "UPM.HE",
    "KONE": "KNEBV.HE",
    "STORA ENSO": "STERV.HE",
    "SAMPO": "SAMPO.HE",
    "KESKO": "KESBV.HE",
    "METSO": "METSO.HE",
    "WÄRTSILÄ": "WRT1V.HE",
    "FORTUM": "FORTUM.HE",
    "ELISA": "ELISA.HE",
    "TELIA": "TELIA1.HE",
    "OP RYHMÄ": None,  # Ei pörssinoteerattu
    # Keskisuuret yhtiöt (Mid Cap)
    "ORION": "ORNBV.HE",
    "HUHTAMÄKI": "HUH1V.HE",
    "OUTOKUMPU": "OUT1V.HE",
    "VALMET": "VALMT.HE",
    "KOJAMO": "KOJAMO.HE",
    "TOKMANNI": "TOKMAN.HE",
    "REMEDY": "REMEDY.HE",
    "REVENIO": "REG1V.HE",
    "HARVIA": "HARVIA.HE",
    "EFECTE": "EFECTE.HE",
}

# Kaupankäyntiajat (EET/EEST)
OMXH_OPEN_HOUR = 10    # 10:00
OMXH_CLOSE_HOUR = 18   # 18:30
OMXH_CLOSE_MINUTE = 30


def resolve_ticker(ticker: str) -> str:
    """
    Muuntaa osakkeen tunnuksen Yahoo Finance -muotoon.

    Esimerkkejä:
        "NOKIA" → "NOKIA.HE"
        "NOKIA.HE" → "NOKIA.HE"
        "Nokia" → "NOKIA.HE"
    """
    ticker_upper = ticker.upper().strip()

    # Jo oikeassa muodossa
    if ticker_upper.endswith(".HE"):
        return ticker_upper

    # Tarkista alias-lista
    if ticker_upper in OMXH_TICKERS:
        resolved = OMXH_TICKERS[ticker_upper]
        if resolved is None:
            raise ValueError(f"Osake '{ticker}' ei ole pörssinoteerattu.")
        return resolved

    # Oletus: lisää .HE-suffiksi
    return f"{ticker_upper}.HE"


def get_omxh_stock_data(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Hakee OMXH-osakkeen historiallisen kurssidata.

    Args:
        ticker: Osakkeen tunnus (esim. "NOKIA" tai "NOKIA.HE")
        period:  Aikaperiodi — "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"
        interval: Aikaväli — "1m", "5m", "1h", "1d", "1wk", "1mo"

    Returns:
        DataFrame sarakkeineen: Open, High, Low, Close, Volume (EUR)
    """
    yf_ticker = resolve_ticker(ticker)
    stock = yf.Ticker(yf_ticker)
    df = stock.history(period=period, interval=interval)

    if df.empty:
        raise ValueError(
            f"Ei dataa osakkeelle '{ticker}' (Yahoo: {yf_ticker}). "
            "Tarkista tunnus tai yhteys."
        )

    return df


def get_omxh_info(ticker: str) -> dict:
    """
    Hakee OMXH-osakkeen perustiedot (nimi, markkina-arvo, P/E jne.)

    Returns:
        dict — Yahoo Finance info-kenttä
    """
    yf_ticker = resolve_ticker(ticker)
    stock = yf.Ticker(yf_ticker)
    info = stock.info

    # Lisätään suomalainen konteksti
    info["exchange_fi"] = "Helsingin pörssi (OMXH)"
    info["currency_fi"] = "EUR"

    return info


def get_omxh_current_price(ticker: str) -> Optional[float]:
    """
    Hakee osakkeen viimeisimmän hinnan (EUR).

    Returns:
        float — hinta euroissa, tai None jos ei saatavilla
    """
    try:
        info = get_omxh_info(ticker)
        return info.get("currentPrice") or info.get("regularMarketPrice")
    except Exception:
        return None


def get_omxh_dividends(ticker: str) -> pd.Series:
    """
    Hakee osakkeen osinkohistorian.

    Returns:
        Series — osinkohistoria (päivämäärä → summa EUR)
    """
    yf_ticker = resolve_ticker(ticker)
    stock = yf.Ticker(yf_ticker)
    return stock.dividends


def is_omxh_open() -> bool:
    """
    Tarkistaa, onko Helsingin pörssi auki juuri nyt (EET/EEST).

    Huom: Ei huomioi pörssipyhiä — käytä tuotannossa kalenteri-APIa.
    """
    from datetime import timezone
    import zoneinfo

    try:
        eet = zoneinfo.ZoneInfo("Europe/Helsinki")
        now = datetime.now(eet)
    except Exception:
        # Fallback jos zoneinfo ei ole saatavilla
        now = datetime.utcnow() + timedelta(hours=2)

    # Ma–Pe
    if now.weekday() >= 5:
        return False

    open_time = now.replace(hour=OMXH_OPEN_HOUR, minute=0, second=0)
    close_time = now.replace(hour=OMXH_CLOSE_HOUR, minute=OMXH_CLOSE_MINUTE, second=0)

    return open_time <= now <= close_time


def list_omxh_tickers() -> list[str]:
    """Palauttaa listan tunnetuista OMXH-osakkeista."""
    return [k for k, v in OMXH_TICKERS.items() if v is not None]


def format_finnish_price(price: float) -> str:
    """
    Muotoilee hinnan suomalaiseen tapaan: 1 234,56 €

    Args:
        price: Hinta numeroina

    Returns:
        Muotoiltu merkkijono
    """
    # Suomalainen muotoilu: tuhaterottimena välilyönti, desimaalina pilkku
    formatted = f"{price:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formatted} €"
