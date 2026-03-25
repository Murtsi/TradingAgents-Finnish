"""
Suomalaiset ja pohjoismaiset uutislähteet — RSS-pohjainen datasyöte
====================================================================
Lähteet (testattu 2026-03-25):

  Kotimaiset:
    IS Taloussanomat  — https://www.is.fi/rss/taloussanomat.xml          (toimii)
    HS Talous         — https://www.hs.fi/rss/talous.xml                 (toimii)
    YLE Talous        — feeds.yle.fi/...                                  (toimii)
    Nordnet Blogi     — https://www.nordnet.fi/blog/feed/                 (toimii)
    Kauppalehti       — POISTETTU (401 Unauthorized)

  Pörssitiedotteet (Nasdaq OMX):
    Nasdaq Helsinki   — https://api.news.eu.nasdaq.com/news/rss/mainMarketNotices (toimii)
    Nasdaq First North— https://api.news.eu.nasdaq.com/news/rss/firstNorthNotices (toimii)

  Makro / kansainväliset:
    ECB               — https://www.ecb.europa.eu/rss/press.xml          (toimii)
    Investing.com     — https://fi.investing.com/rss/news_25.rss         (toimii, suomeksi)

  Hylätyt:
    Inderes           — ei RSS-syötettä (404)
    Talouselämä       — ei RSS-syötettä (404)
    Reuters           — DNS-esto tässä ympäristössä
    Suomen Pankki     — RSS-osoitteet muuttuneet (404)

Optimointi: _fetch_rss on LRU-välimuistissa per-prosessi, joten saman analyysin
aikana RSS-syötteitä ei haeta uudelleen. Yhdistetty get_all_stock_news-funktio
mahdollistaa yhden LLM-tool-call-kutsun kolmen sijaan.

FORK: Suomi-lokalisointi — uusi tiedosto
"""
from __future__ import annotations

import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# RSS-syötteet — jaettu kolmeen ryhmään käyttötarkoituksen mukaan

# 1. Kotimaiset talousuutiset (suodatetaan tickerin/yhtiön nimellä)
RSS_FEEDS = {
    "IS Taloussanomat": "https://www.is.fi/rss/taloussanomat.xml",
    "HS Talous":        "https://www.hs.fi/rss/talous.xml",
    "YLE Talous":       "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-35095&limit=30",
    "Nordnet Blogi":    "https://www.nordnet.fi/blog/feed/",
}

# 2. Pörssitiedotteet — Nasdaq OMX Helsinki (kaikki yhtiötiedotteet)
# Ei 30s nopeampaa pollausta (Nasdaq rate limit)
RSS_FEEDS_EXCHANGE = {
    "Nasdaq Helsinki":    "https://api.news.eu.nasdaq.com/news/rss/mainMarketNotices",
    "Nasdaq First North": "https://api.news.eu.nasdaq.com/news/rss/firstNorthNotices",
}

# 3. Makrouutiset — aina mukana (ei ticker-suodatusta)
RSS_FEEDS_MACRO = {
    "ECB":             "https://www.ecb.europa.eu/rss/press.xml",
    "Investing.com":   "https://fi.investing.com/rss/news_25.rss",
}

_TIMEOUT = 8  # sekuntia

# Tunnettujen OMXH-osakkeiden suomenkieliset nimet parempia hakutermejä varten
# Avain = Yahoo Finance ticker, arvo = lista hakutermeistä
OMXH_KEYWORDS: dict[str, list[str]] = {
    "NOKIA.HE":   ["Nokia", "Nokia Oyj"],
    "NDA-FI.HE":  ["Nordea", "Nordea Bank"],
    "NESTE.HE":   ["Neste", "Neste Oyj"],
    "UPM.HE":     ["UPM", "UPM-Kymmene"],
    "KNEBV.HE":   ["KONE", "KONE Oyj"],
    "STERV.HE":   ["Stora Enso"],
    "SAMPO.HE":   ["Sampo", "Sampo Oyj"],
    "KESBV.HE":   ["Kesko", "Kesko Oyj"],
    "METSO.HE":   ["Metso"],
    "WRT1V.HE":   ["Wärtsilä", "Wartsila"],
    "FORTUM.HE":  ["Fortum", "Fortum Oyj"],
    "ORNBV.HE":   ["Orion", "Orion Oyj"],
    "OUT1V.HE":   ["Outokumpu"],
    "SSABAH.HE":  ["SSAB"],
    "TIETO.HE":   ["TietoEVRY", "Tieto"],
    "ELISA.HE":   ["Elisa", "Elisa Oyj"],
    "HUH1V.HE":   ["Huhtamäki", "Huhtamaki"],
    "FIA1S.HE":   ["Finnair", "Finnair Oyj"],
    "OMASP.HE":   ["Oma Säästöpankki", "OmaSp"],
    "KOJAMO.HE":  ["Kojamo", "Lumo"],
    "VALMT.HE":   ["Valmet"],
    "OUT1V.HE":   ["Outokumpu"],
}

# Yleiset suomalaiset markkinaavainsanat (aina mukana kotimaisissa syötteissä)
_MARKET_KEYWORDS = [
    "omxh", "helsingin pörssi", "ekp", "euroopan keskuspankki",
    "korko", "inflaatio", "osakemarkkinat", "pörssi", "helsinki",
    "suomen talous", "talouskasvu", "nordnet", "nasdaq",
]


@lru_cache(maxsize=8)
def _fetch_rss_cached(url: str) -> tuple[dict, ...]:
    """
    Hakee RSS-syötteen ja palauttaa artikkelit tuplena (LRU-välimuistia varten).
    Välimuisti elää prosessin ajan — riittää estämään tupla-haut saman analyysin aikana.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "KauppaAgentit/1.0"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = resp.read()
        root = ET.fromstring(data)
    except Exception as e:
        logger.warning(f"RSS-haku epäonnistui ({url}): {e}")
        return ()

    articles = []
    for item in root.iter("item"):
        title   = (item.findtext("title") or "").strip()
        summary = (item.findtext("description") or "").strip()
        link    = (item.findtext("link") or "").strip()
        pub_raw = (item.findtext("pubDate") or "").strip()

        pub_dt: Optional[datetime] = None
        if pub_raw:
            try:
                pub_dt = parsedate_to_datetime(pub_raw).replace(tzinfo=None)
            except Exception:
                pass

        if title:
            articles.append({"title": title, "summary": summary,
                              "link": link, "pub_dt": pub_dt})
    return tuple(articles)


def _lookup_keywords(ticker: str, extra_name: str = "") -> list[str]:
    """Rakentaa hakutermilistän tickerin ja tunnettujen nimien perusteella."""
    short = ticker.replace(".HE", "").upper()
    known = OMXH_KEYWORDS.get(ticker.upper(), [])
    terms = list({short} | set(known))
    if extra_name:
        terms.append(extra_name)
    return terms


def _is_relevant(article: dict, keywords: list[str]) -> bool:
    text = (article["title"] + " " + article["summary"]).lower()
    return any(kw.lower() in text for kw in keywords)


def _format_article(art: dict, source: str) -> str:
    date_str = art["pub_dt"].strftime("%d.%m.%Y") if art["pub_dt"] else ""
    label = f"{source}, {date_str}" if date_str else source
    summary_short = art["summary"][:250].strip()
    parts = [f"### {art['title']} ({label})"]
    if summary_short:
        parts.append(summary_short)
    if art["link"]:
        parts.append(art["link"])
    return "\n".join(parts)


def get_finnish_market_news(
    ticker: str,
    company_name: str = "",
    lookback_days: int = 7,
) -> str:
    """
    Hakee viimeisimmät suomalaiset ja pohjoismaiset uutiset RSS:stä.

    Lähteet:
      - Kotimaiset (IS, HS, YLE, Nordnet): suodatetaan tickerin nimellä
      - Nasdaq pörssitiedotteet: suodatetaan yhtiön nimellä
      - Makro (ECB, Investing.com): aina mukana ilman suodatusta
    """
    company_keywords = _lookup_keywords(ticker, company_name)
    all_keywords = company_keywords + _MARKET_KEYWORDS
    cutoff = datetime.now() - timedelta(days=lookback_days)
    short = ticker.replace(".HE", "").upper()

    results: list[str] = []

    # 1. Kotimaiset uutiset — suodatetaan yhtiön/markkinan avainsanoilla
    for source, url in RSS_FEEDS.items():
        for art in _fetch_rss_cached(url):
            if art["pub_dt"] and art["pub_dt"] < cutoff:
                continue
            if _is_relevant(art, all_keywords):
                results.append(_format_article(art, source))

    # 2. Nasdaq pörssitiedotteet — suodatetaan yhtiön nimellä (ei markkinasanoilla)
    for source, url in RSS_FEEDS_EXCHANGE.items():
        for art in _fetch_rss_cached(url):
            if art["pub_dt"] and art["pub_dt"] < cutoff:
                continue
            if _is_relevant(art, company_keywords):
                results.append(_format_article(art, source))

    # 3. Makrouutiset — aina mukana (max 3 per lähde, ei suodatusta)
    macro_results: list[str] = []
    for source, url in RSS_FEEDS_MACRO.items():
        count = 0
        for art in _fetch_rss_cached(url):
            if art["pub_dt"] and art["pub_dt"] < cutoff:
                continue
            if count >= 3:
                break
            macro_results.append(_format_article(art, source))
            count += 1

    all_results = results[:12] + macro_results
    if not all_results:
        return (
            f"Ei uutisia löydetty osakkeelle {short} "
            f"viimeisen {lookback_days} päivän ajalta."
        )

    header = f"## Suomalaiset ja pohjoismaiset uutiset — {short} (viimeiset {lookback_days} pv)\n\n"
    return header + "\n\n".join(all_results)


def get_all_stock_news(ticker: str, trade_date: str, lookback_days: int = 7) -> str:
    """
    Yhdistetty uutishaku: hakee kaikki uutislähteet yhdellä kutsulla.

    Yhdistää:
      1. Yahoo Finance -uutiset tickerille (yfinance)
      2. Kotimaiset RSS: IS Taloussanomat, HS Talous, YLE Talous, Nordnet Blogi
      3. Nasdaq pörssitiedotteet (mainMarket + First North)
      4. Makro: ECB, Investing.com (suomeksi)

    Tarkoitus: yksi LLM-tool-call kolmen sijaan → ~50 % vähemmän LLM-pyörähdyksiä
    uutisanalyytikossa → nopeampi ja halvempi ajo.

    Args:
        ticker:       Yahoo Finance -tunnus (esim. "NOKIA.HE")
        trade_date:   Analyysipäivä "yyyy-mm-dd"
        lookback_days: Kuinka monta päivää taaksepäin (oletus 7)

    Returns:
        Yhdistetty merkkijono kaikista uutislähteistä.
    """
    from tradingagents.dataflows.yfinance_news import (
        get_news_yfinance,
        get_global_news_yfinance,
    )

    sections: list[str] = []

    # 1. Yahoo Finance — yhtiökohtaiset uutiset
    try:
        end_date = trade_date
        from datetime import datetime as _dt, timedelta as _td
        start_date = (_dt.strptime(trade_date, "%Y-%m-%d") - _td(days=lookback_days)).strftime("%Y-%m-%d")
        yf_news = get_news_yfinance(ticker, start_date, end_date)
        sections.append(yf_news)
    except Exception as e:
        logger.warning(f"Yahoo Finance -uutishaku epäonnistui: {e}")
        sections.append(f"Yahoo Finance news unavailable: {e}")

    # 2. Suomalaiset RSS-lähteet
    try:
        fi_news = get_finnish_market_news(ticker, lookback_days=lookback_days)
        sections.append(fi_news)
    except Exception as e:
        logger.warning(f"Suomalainen uutishaku epäonnistui: {e}")

    # 3. ECB / Nordic makrouutiset
    try:
        global_news = get_global_news_yfinance(trade_date, look_back_days=lookback_days, limit=8)
        sections.append(global_news)
    except Exception as e:
        logger.warning(f"Globaali uutishaku epäonnistui: {e}")

    return "\n\n" + "─" * 40 + "\n\n".join(sections)
