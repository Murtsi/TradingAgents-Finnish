"""Equity curven suorituskykymittarit."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from statistics import mean, stdev


@dataclass(frozen=True)
class EquityPoint:
    """Yksi equity curve -piste."""

    date: date
    equity: float


@dataclass(frozen=True)
class EquityMetrics:
    """Autotraderin tärkeimmät tulosmittarit."""

    total_return: float
    cagr: float
    max_drawdown: float
    volatility: float
    sharpe: float
    benchmark_return: float | None = None
    excess_return: float | None = None


def _daily_returns(points: list[EquityPoint]) -> list[float]:
    returns: list[float] = []
    for previous, current in zip(points, points[1:]):
        if previous.equity > 0:
            returns.append((current.equity / previous.equity) - 1)
    return returns


def calculate_max_drawdown(points: list[EquityPoint]) -> float:
    """Laske suurin huipusta pohjaan -lasku positiivisena prosenttina."""
    if not points:
        return 0.0
    peak = points[0].equity
    max_dd = 0.0
    for point in points:
        peak = max(peak, point.equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - point.equity) / peak)
    return max_dd


def calculate_metrics(
    points: list[EquityPoint],
    benchmark_prices: list[float] | None = None,
) -> EquityMetrics:
    """Laske tuotto, CAGR, max drawdown, volatiliteetti, Sharpe ja benchmark-ero."""
    if len(points) < 2 or points[0].equity <= 0:
        return EquityMetrics(0.0, 0.0, calculate_max_drawdown(points), 0.0, 0.0)

    total_return = (points[-1].equity / points[0].equity) - 1
    days = max(1, (points[-1].date - points[0].date).days)
    cagr = (1 + total_return) ** (365 / days) - 1 if total_return > -1 else -1.0
    returns = _daily_returns(points)
    volatility = stdev(returns) * math.sqrt(252) if len(returns) > 1 else 0.0
    sharpe = (mean(returns) / stdev(returns) * math.sqrt(252)) if len(returns) > 1 and stdev(returns) else 0.0

    benchmark_return: float | None = None
    excess_return: float | None = None
    if benchmark_prices and len(benchmark_prices) >= 2 and benchmark_prices[0] > 0:
        benchmark_return = (benchmark_prices[-1] / benchmark_prices[0]) - 1
        excess_return = total_return - benchmark_return

    return EquityMetrics(
        total_return=total_return,
        cagr=cagr,
        max_drawdown=calculate_max_drawdown(points),
        volatility=volatility,
        sharpe=sharpe,
        benchmark_return=benchmark_return,
        excess_return=excess_return,
    )
