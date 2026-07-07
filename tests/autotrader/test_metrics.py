from __future__ import annotations

from datetime import date

import pytest

from autotrader.metrics import EquityPoint, calculate_metrics


def test_metrics_math():
    metrics = calculate_metrics(
        [
            EquityPoint(date(2026, 1, 1), 100),
            EquityPoint(date(2026, 1, 2), 110),
            EquityPoint(date(2026, 1, 3), 105),
        ],
        benchmark_prices=[100, 102],
    )

    assert metrics.total_return == pytest.approx(0.05)
    assert metrics.max_drawdown == pytest.approx(5 / 110)
    assert metrics.benchmark_return == pytest.approx(0.02)
    assert metrics.excess_return == pytest.approx(0.03)
