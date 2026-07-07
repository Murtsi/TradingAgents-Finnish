"""Hintadatan ohut wrapper autotraderille."""

from __future__ import annotations

from typing import Protocol

import pandas as pd
import yfinance as yf

from tradingagents.dataflows.omxh_utils import resolve_ticker


class PriceSource(Protocol):
    """Injektoitava hintalähde testeille ja tuotannolle."""

    def history(self, ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        """Palauta OHLCV-historia."""

    def last_price(self, ticker: str) -> float | None:
        """Palauta viimeisin hinta euroissa."""


def normalize_market_ticker(ticker: str) -> str:
    """Resolvoi osaketicker, mutta päästä indeksitunnukset läpi sellaisenaan."""
    ticker = ticker.strip().upper()
    if ticker.startswith("^"):
        return ticker
    return resolve_ticker(ticker)


class YFinancePriceSource:
    """Yahoo Finance -hintalähde."""

    def history(self, ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        yf_ticker = normalize_market_ticker(ticker)
        return yf.Ticker(yf_ticker).history(period=period, interval=interval)

    def last_price(self, ticker: str) -> float | None:
        yf_ticker = normalize_market_ticker(ticker)
        stock = yf.Ticker(yf_ticker)
        try:
            fast_info = stock.fast_info
            price = getattr(fast_info, "last_price", None)
            if price and price > 0:
                return float(price)
        except Exception:
            pass

        try:
            info = stock.info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price and price > 0:
                return float(price)
        except Exception:
            pass

        return None
