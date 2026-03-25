"""
KauppaAgentit — Suomi-konfiguraatio
====================================
Tämä tiedosto sisältää suomalaiselle markkinalle optimoidut asetukset.
Ylikirjoittaa upstream DEFAULT_CONFIG:n tarvittavilta osin.
"""

import os
from tradingagents.default_config import DEFAULT_CONFIG

FINNISH_CONFIG = {
    **DEFAULT_CONFIG,

    # ── LLM-asetukset ──────────────────────────────────────────────
    "llm_provider": "anthropic",
    # Kustannushuomio: Sonnet käyttää research_manager + portfolio_manager -agenteissa
    # Vaihda takaisin "claude-sonnet-4-20250514" kun siirryt tuotantoon
    "deep_think_llm": "claude-haiku-4-5-20251001",  # Testaus: Haiku ~0.05€/ajo vs Sonnet ~0.46€
    "quick_think_llm": "claude-haiku-4-5-20251001", # Nopeat tehtävät
    "backend_url": None,  # Anthropic käyttää omaa SDK:ta

    # ── Väittelykierrokset ─────────────────────────────────────────
    # Enemmän kierroksia = syvempi analyysi, enemmän API-kutsuja
    "max_debate_rounds": 1,        # Tuotannossa: 2–3
    "max_risk_discuss_rounds": 1,

    # ── Tokenirajoitukset (kustannusten hallinta) ──────────────────
    # Rajoittaa jokaisen agentin vastauspituuden.
    # 4096 antaa salkunhoitajalle ja tutkijoille tilaa kirjoittaa täydellinen raportti.
    # TEST_MODE ylikirjoittaa tämän arvolla 500.
    "max_tokens": 8192,  # Claude Haiku max output tokens

    # ── Datalähteet ────────────────────────────────────────────────
    "online_tools": True,
    "data_vendors": {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    },

    # ── Suomi-lokalisointi ─────────────────────────────────────────
    "locale": "fi_FI",
    "currency": "EUR",
    "exchange": "OMXH",           # Helsingin pörssi
    "language": "fi",

    # ── Suomalainen verotuskonteksti ───────────────────────────────
    "tax_context": {
        "capital_gains_rate": 0.30,       # Pääomatulo 30%
        "capital_gains_rate_high": 0.34,  # Yli 30 000 € 34%
        "threshold": 30000,               # Raja EUR
        "currency": "EUR",
    },

    # ── Uutislähteet ───────────────────────────────────────────────
    "news_sources": [
        "kauppalehti",
        "taloussanomat",
        "inderes",
        "reuters_nordic",
        "yle_talous",
    ],

    # ── Seurattavat osakkeet (OMXH) ────────────────────────────────
    # Yahoo Finance käyttää .HE-suffiksia Helsingin pörssille
    "default_tickers": {
        "NOKIA": "NOKIA.HE",
        "NORDEA": "NDA-FI.HE",
        "NESTE": "NESTE.HE",
        "UPM": "UPM.HE",
        "KONE": "KNEBV.HE",
        "STORA_ENSO": "STERV.HE",
        "SAMPO": "SAMPO.HE",
        "KESKO": "KESBV.HE",
    },

    # ── Vastuuvapautus (pakollinen) ────────────────────────────────
    "disclaimer_required": True,
    "disclaimer_text": (
        "[VASTUUVAPAUTUS] Tämä on tekoälyn tuottama analyysi, EI sijoitussuositus. "
        "Työkalu on tarkoitettu tutkimus- ja oppimistarkoituksiin. "
        "Sijoittamiseen liittyy aina riskejä ja arvot voivat laskea. "
        "Finanssivalvonta valvoo sijoitusneuvontaa Suomessa. "
        "Tee aina oma tutkimus ja tarvittaessa konsultoi rekisteröityä sijoitusneuvojaa."
    ),

    # ── Tuloshakemisto ─────────────────────────────────────────────
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
}


# ── TEST-tilan ylikirjoitukset (env TEST_MODE=true) ────────────────────
# Kaikki 4 analyytikkoa ajetaan, mutta tokenit rajoitetaan
# jotta yksittäinen testitestaus maksaa ~0.02–0.05€ eikä 0.50€.
TEST_OVERRIDES = {
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    # max_tokens rajoittaa jokaisen agentin vastauspituuden
    # → lyhyemmät raportit, huomattavasti pienempi API-lasku
    "max_tokens": 500,
}


def get_finnish_config(overrides: dict = None) -> dict:
    """
    Palauttaa Suomi-konfiguraation valinnaisten ylikirjoitusten kanssa.

    Jos ympäristömuuttuja TEST_MODE=true, lisätään TEST_OVERRIDES automaattisesti
    (max_tokens=500, max_debate_rounds=1) — kaikki 4 analyytikkoa ajetaan silti.
    """
    config = FINNISH_CONFIG.copy()

    test_mode = os.getenv("TEST_MODE", "").lower() in ("1", "true", "yes")
    if test_mode:
        config.update(TEST_OVERRIDES)

    if overrides:
        config.update(overrides)
    return config


def resolve_omxh_ticker(ticker: str) -> str:
    """
    Muuntaa suomalaisen osakkeen tunnuksen Yahoo Finance -muotoon.
    Esim. 'NOKIA' → 'NOKIA.HE', 'NOKIA.HE' → 'NOKIA.HE'
    """
    ticker = ticker.upper().strip()
    if ticker.endswith(".HE"):
        return ticker
    # Tarkista tunnetut aliakset
    known = FINNISH_CONFIG["default_tickers"]
    if ticker in known:
        return known[ticker]
    # Oletus: lisää .HE-suffiksi
    return f"{ticker}.HE"
