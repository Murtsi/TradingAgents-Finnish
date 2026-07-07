"""Halpa kvanttipohjainen esiseulonta ennen LLM-analyysiä."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from autotrader.prices import PriceSource


@dataclass(frozen=True)
class ScreeningCandidate:
    """Esiseulotun osakkeen pisteet."""

    ticker: str
    score: float
    latest_price: float
    reasons: list[str] = field(default_factory=list)
    momentum_20d: float | None = None
    rsi_14: float | None = None
    sma_50: float | None = None


def _rsi(close: pd.Series, window: int = 14) -> float | None:
    if len(close) < window + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    last_loss = loss.iloc[-1]
    if pd.isna(last_loss):
        return None
    if last_loss == 0:
        return 100.0
    rs = gain.iloc[-1] / last_loss
    return float(100 - (100 / (1 + rs)))


def score_ticker(ticker: str, price_source: PriceSource) -> ScreeningCandidate | None:
    """Laske momentum/RSI/SMA-pisteet yhdelle tickerille."""
    df = price_source.history(ticker, period="6mo", interval="1d")
    if df is None or df.empty or "Close" not in df:
        return None

    close = df["Close"].dropna()
    if len(close) < 55:
        return None

    latest = float(close.iloc[-1])
    if latest <= 0:
        return None

    momentum_20d = float((latest / close.iloc[-21]) - 1) if len(close) >= 21 else 0.0
    sma_50 = float(close.rolling(50).mean().iloc[-1])
    rsi_14 = _rsi(close)

    score = 0.0
    reasons: list[str] = []

    score += momentum_20d * 100
    if momentum_20d > 0:
        reasons.append(f"20 päivän momentum {momentum_20d:.1%}")

    if latest > sma_50:
        score += 5.0
        reasons.append("hinta yli 50 päivän keskiarvon")
    else:
        score -= 4.0

    if rsi_14 is not None:
        if 45 <= rsi_14 <= 65:
            score += 3.0
            reasons.append(f"RSI neutraali/vahvistuva {rsi_14:.1f}")
        elif rsi_14 > 75:
            score -= 5.0
            reasons.append(f"RSI ylinostettu {rsi_14:.1f}")
        elif rsi_14 < 30:
            score -= 2.0
            reasons.append(f"RSI ylimyyty {rsi_14:.1f}")

    return ScreeningCandidate(
        ticker=ticker,
        score=round(score, 4),
        latest_price=latest,
        reasons=reasons,
        momentum_20d=momentum_20d,
        rsi_14=rsi_14,
        sma_50=sma_50,
    )


def screen_universe(
    universe: list[str],
    holdings: list[str],
    price_source: PriceSource,
    top_n: int,
) -> list[ScreeningCandidate]:
    """Rankkaa universumi ja lisää nykyiset omistukset mukaan."""
    candidates: list[ScreeningCandidate] = []
    for ticker in universe:
        candidate = score_ticker(ticker, price_source)
        if candidate:
            candidates.append(candidate)

    ranked = sorted(candidates, key=lambda item: item.score, reverse=True)
    shortlist = ranked[:top_n]

    included = {item.ticker for item in shortlist}
    for ticker in holdings:
        normalized = ticker.upper()
        if normalized in included:
            continue
        candidate = score_ticker(normalized, price_source)
        if candidate:
            shortlist.append(candidate)
            included.add(normalized)

    return shortlist
