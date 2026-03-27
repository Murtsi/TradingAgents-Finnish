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

# Tunnetut pörssisuffiksit — nämä läpäistään sellaisenaan ilman .HE-lisäystä
# FORK: Pohjoismaiset pörssit + yleiset Yahoo Finance -suffiksit
KNOWN_EXCHANGE_SUFFIXES: frozenset[str] = frozenset({
    ".HE",   # Helsinki (OMXH)
    ".ST",   # Stockholm (OMXS)
    ".OL",   # Oslo (OSLO)
    ".CO",   # Kööpenhamina (OMXC)
    ".IC",   # Reykjavik
    ".L",    # Lontoo
    ".PA",   # Pariisi
    ".F",    # Frankfurt
    ".TO",   # Toronto
    ".AX",   # Australia
    ".SS",   # Shanghai
    ".HK",   # Hongkong
})

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
    # Ruotsalaiset yhtiöt (OMXS) — yleisesti haetut Suomesta
    "SKANSKA": "SKA-B.ST",
    "SKA B": "SKA-B.ST",
    "SKA-B": "SKA-B.ST",
    "VOLVO": "VOLV-B.ST",
    "VOLVO B": "VOLV-B.ST",
    "VOLV-B": "VOLV-B.ST",
    "ATLAS COPCO": "ATCO-B.ST",
    "ATCO B": "ATCO-B.ST",
    "INVESTOR": "INVE-B.ST",
    "INVE B": "INVE-B.ST",
    "H&M": "HM-B.ST",
    "HM B": "HM-B.ST",
    "HENNES": "HM-B.ST",
}

# Virallinen yritysnimi per Yahoo Finance -tunnus (estää uutisagenttia nimeämästä väärän yhtiön)
OMXH_COMPANY_NAMES: dict[str, str] = {
    "NOKIA.HE":   "Nokia Oyj",
    "NDA-FI.HE":  "Nordea Bank Abp",
    "NESTE.HE":   "Neste Oyj",
    "UPM.HE":     "UPM-Kymmene Oyj",
    "KNEBV.HE":   "KONE Oyj",
    "STERV.HE":   "Stora Enso Oyj",
    "SAMPO.HE":   "Sampo Oyj",
    "KESBV.HE":   "Kesko Oyj",
    "METSO.HE":   "Metso Oyj",
    "WRT1V.HE":   "Wärtsilä Oyj",
    "FORTUM.HE":  "Fortum Oyj",
    "ELISA.HE":   "Elisa Oyj",
    "TELIA1.HE":  "Telia Company",
    "ORNBV.HE":   "Orion Oyj",
    "HUH1V.HE":   "Huhtamäki Oyj",
    "OUT1V.HE":   "Outokumpu Oyj",
    "VALMT.HE":   "Valmet Oyj",
    "KOJAMO.HE":  "Kojamo Oyj",
    "TOKMAN.HE":  "Tokmanni Group Oyj",
    "REMEDY.HE":  "Remedy Entertainment Oyj",
    "REG1V.HE":   "Revenio Group Oyj",
    "HARVIA.HE":  "Harvia Oyj",
    "EFECTE.HE":  "Efecte Oyj",
    "FIA1S.HE":   "Finnair Oyj",
    "OMASP.HE":   "Oma Säästöpankki Oyj",
    "CGCBV.HE":   "Cargotec Oyj",
    "TTALO.HE":   "Talenom Oyj",
    "ENDOM.HE":   "Endomines AB",
    "KAMUX.HE":   "Kamux Oyj",
    "TNOM.HE":    "Talenom Oyj",
    "KREATE.HE":  "Kreate Group Oyj",
    "NIXU.HE":    "Nixu Oyj",
    "PUUILO.HE":  "Puuilo Oyj",
    "HKSAV.HE":   "HKScan Oyj",
    "ATG1V.HE":   "Atria Oyj",
    "REKA.HE":    "Reka Industrial Oyj",
    "GOFORE.HE":  "Gofore Oyj",
    "SOLTEQ.HE":  "Solteq Oyj",
    # Ruotsalaiset yhtiöt
    "SKA-B.ST":   "Skanska AB",
    "VOLV-B.ST":  "Volvo AB",
    "ATCO-B.ST":  "Atlas Copco AB",
    "INVE-B.ST":  "Investor AB",
    "HM-B.ST":    "H&M Hennes & Mauritz AB",
}

# FORK: Suomi-lokalisointi — ISIN + toimiala yrityskohtaisesti, estää nimitunnistusvirheet (esim. Neste vs Nestlé)
OMXH_COMPANY_META: dict[str, dict] = {
    "NOKIA.HE":   {"name": "Nokia Oyj",           "isin": "FI0009000681", "sector": "Technology / Telecom Equipment"},
    "NDA-FI.HE":  {"name": "Nordea Bank Abp",     "isin": "FI4000297767", "sector": "Financials / Banking"},
    "NESTE.HE":   {"name": "Neste Oyj",            "isin": "FI0009013296", "sector": "Energy / Oil Refining & Renewables"},
    "UPM.HE":     {"name": "UPM-Kymmene Oyj",     "isin": "FI0009005987", "sector": "Materials / Forestry & Paper"},
    "KNEBV.HE":   {"name": "KONE Oyj",             "isin": "FI0009013403", "sector": "Industrials / Elevators & Escalators"},
    "STERV.HE":   {"name": "Stora Enso Oyj",       "isin": "FI0009005961", "sector": "Materials / Paper & Packaging"},
    "SAMPO.HE":   {"name": "Sampo Oyj",            "isin": "FI0009003305", "sector": "Financials / Insurance"},
    "KESBV.HE":   {"name": "Kesko Oyj",            "isin": "FI0009000202", "sector": "Consumer Staples / Retail"},
    "METSO.HE":   {"name": "Metso Oyj",            "isin": "FI4000397905", "sector": "Industrials / Mining Equipment"},
    "WRT1V.HE":   {"name": "Wärtsilä Oyj",         "isin": "FI0009003727", "sector": "Industrials / Marine & Energy Systems"},
    "FORTUM.HE":  {"name": "Fortum Oyj",           "isin": "FI0009007132", "sector": "Utilities / Electric Power"},
    "ELISA.HE":   {"name": "Elisa Oyj",            "isin": "FI0009007884", "sector": "Communication Services / Telecom"},
    "ORNBV.HE":   {"name": "Orion Oyj",            "isin": "FI0009014377", "sector": "Healthcare / Pharmaceuticals"},
    "HUH1V.HE":   {"name": "Huhtamäki Oyj",        "isin": "FI0009000459", "sector": "Materials / Packaging"},
    "OUT1V.HE":   {"name": "Outokumpu Oyj",        "isin": "FI0009002422", "sector": "Materials / Steel"},
    "VALMT.HE":   {"name": "Valmet Oyj",           "isin": "FI4000074984", "sector": "Industrials / Process Equipment"},
    "FIA1S.HE":   {"name": "Finnair Oyj",          "isin": "FI0009003230", "sector": "Industrials / Airlines"},
    "SAMPO.HE":   {"name": "Sampo Oyj",            "isin": "FI0009003305", "sector": "Financials / Insurance"},
    "CGCBV.HE":   {"name": "Cargotec Oyj",         "isin": "FI0009013429", "sector": "Industrials / Cargo Handling Equipment"},
    "GOFORE.HE":  {"name": "Gofore Oyj",           "isin": "FI4000198767", "sector": "Technology / IT Consulting"},
    "REMEDY.HE":  {"name": "Remedy Entertainment Oyj", "isin": "FI4000153580", "sector": "Technology / Video Games"},
    "HARVIA.HE":  {"name": "Harvia Oyj",           "isin": "FI4000297360", "sector": "Consumer Discretionary / Sauna Equipment"},
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

    # Jo validissa muodossa — tunnettu pörssisuffiksi, palautetaan sellaisenaan
    if any(ticker_upper.endswith(s) for s in KNOWN_EXCHANGE_SUFFIXES):
        return ticker_upper

    # Tarkista alias-lista (tukee myös välilyönnilliset nimet kuten "STORA ENSO", "SKA B")
    if ticker_upper in OMXH_TICKERS:
        resolved = OMXH_TICKERS[ticker_upper]
        if resolved is None:
            raise ValueError(f"Osake '{ticker}' ei ole pörssinoteerattu.")
        return resolved

    # Kokeile välilyönti→viiva-muunnos (esim. "NDA FI" → "NDA-FI.HE", "SKA B" → "SKA-B" tarkistetaan ensin)
    dashed = ticker_upper.replace(" ", "-")
    if dashed != ticker_upper:
        if dashed in OMXH_TICKERS:
            resolved = OMXH_TICKERS[dashed]
            if resolved is None:
                raise ValueError(f"Osake '{ticker}' ei ole pörssinoteerattu.")
            return resolved
        # Tarkista onko viiva-muoto jo validi suffiksi (esim. "SKA-B.ST" käyttäjältä ilman suffiksia)
        return f"{dashed}.HE"

    # Oletus: lisää .HE-suffiksi
    return f"{ticker_upper}.HE"


def resolve_company_name(ticker: str) -> str:
    """
    Palauttaa yhtiön virallisen nimen tickerille.

    Käytetään agenttikontekstissa estämään uutisagentin virheelliset nimitunnistukset
    (esim. FIA1S.HE → "Finnair Oyj", ei "Finavia" tai "Embraer").

    Ensin tarkistetaan staattinen kartta, sitten yfinance-fallback.
    """
    yf_ticker = resolve_ticker(ticker)

    # Staattinen kartta — nopea, luotettava, ei API-kutsua
    if yf_ticker in OMXH_COMPANY_NAMES:
        return OMXH_COMPANY_NAMES[yf_ticker]

    # Fallback: yfinance longName
    try:
        info = yf.Ticker(yf_ticker).info
        name = info.get("longName") or info.get("shortName")
        if name:
            return name
    except Exception:
        pass

    return yf_ticker  # Viimeinen vaihtoehto: palauta ticker sellaisenaan


def resolve_company_meta(ticker: str) -> dict:
    """
    Palauttaa yhtiön nimen, ISIN-tunnuksen ja toimialan tickerille.

    Käytetään agenttikontekstissa estämään nimitunnistusvirheet uutisanalyysissä
    (esim. NESTE.HE → Neste Oyj / FI0009013296 / Energy, EI Nestlé).

    Palauttaa dict-muodossa: {"name": str, "isin": str | None, "sector": str | None}
    """
    yf_ticker = resolve_ticker(ticker)
    if yf_ticker in OMXH_COMPANY_META:
        return OMXH_COMPANY_META[yf_ticker]
    # Fallback: name only
    return {"name": resolve_company_name(ticker), "isin": None, "sector": None}


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


def get_omxh_price_snapshot(ticker: str) -> dict:
    """
    Hakee kurssin, volyymin ja bid/ask analyysihetkellä.
    Tallennetaan stateen backtestingiä ja signaalien tarkkuuden seurantaa varten.

    Returns:
        dict — {price, volume, bid, ask, timestamp} tai tyhjät arvot virhetilanteessa
    """
    from datetime import timezone
    try:
        info = get_omxh_info(ticker)
        return {
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "volume": info.get("regularMarketVolume"),
            "bid": info.get("bid"),
            "ask": info.get("ask"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        return {"price": None, "volume": None, "bid": None, "ask": None, "timestamp": None}


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
