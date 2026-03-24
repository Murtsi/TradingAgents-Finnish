"""
Suomalaiset uutislähteet — RSS-pohjainen datasyöte
====================================================
Hakee uutisia Kauppalehti- ja YLE Talous -RSS-syötteistä.
Ei ulkoisia riippuvuuksia: käyttää vain standardikirjaston urllib + xml.etree.

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

# RSS-syötteet
RSS_FEEDS = {
    "Kauppalehti": "https://feeds.kauppalehti.fi/rss/uutiset",
    "YLE Talous":  "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-35095&limit=30",
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
}

# Yleiset suomalaiset markkinaavainsanat (aina mukana)
_MARKET_KEYWORDS = [
    "omxh", "helsingin pörssi", "ekp", "euroopan keskuspankki",
    "korko", "inflaatio", "osakemarkkinat", "pörssi", "helsinki",
    "suomen talous", "talouskasvu",
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
    Hakee viimeisimmät suomalaiset talousuutiset RSS:stä.
    Käyttää LRU-välimuistia — nopea jos kutsutaan useasti saman analyysin aikana.
    """
    company_keywords = _lookup_keywords(ticker, company_name)
    all_keywords = company_keywords + _MARKET_KEYWORDS
    cutoff = datetime.now() - timedelta(days=lookback_days)
    short = ticker.replace(".HE", "").upper()

    results: list[str] = []
    for source, url in RSS_FEEDS.items():
        for art in _fetch_rss_cached(url):
            if art["pub_dt"] and art["pub_dt"] < cutoff:
                continue
            if _is_relevant(art, all_keywords):
                results.append(_format_article(art, source))

    if not results:
        return (
            f"Ei suomenkielisiä uutisia löydetty osakkeelle {short} "
            f"viimeisen {lookback_days} päivän ajalta (Kauppalehti/YLE Talous)."
        )
    header = f"## Suomalaiset talousuutiset — {short} (viimeiset {lookback_days} pv)\n\n"
    return header + "\n\n".join(results[:15])


def get_all_stock_news(ticker: str, trade_date: str, lookback_days: int = 7) -> str:
    """
    Yhdistetty uutishaku: hakee kaikki uutislähteet yhdellä kutsulla.

    Yhdistää:
      1. Yahoo Finance -uutiset tickerille (yfinance)
      2. Suomalaiset RSS-uutiset (Kauppalehti, YLE Talous)
      3. ECB/Nordic-makrouutiset (Yahoo Finance Search)

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
