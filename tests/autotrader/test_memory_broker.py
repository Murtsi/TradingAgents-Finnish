from __future__ import annotations

import pytest

from autotrader.broker.base import Side
from autotrader.broker.memory import MemoryBroker


class FixedPriceSource:
    def last_price(self, ticker: str) -> float | None:
        return 10.0


def test_memory_broker_buy_and_sell_cash_math():
    broker = MemoryBroker(initial_cash=1_000, commission_pct=0.01, slippage_pct=0.01, price_source=FixedPriceSource())

    buy = broker.place_market_order("NOKIA.HE", Side.BUY, 10)
    assert buy.accepted
    assert broker.cash == pytest.approx(1_000 - 10 * 10.1 * 1.01)
    assert broker.get_positions()[0].amount == 10

    sell = broker.place_market_order("NOKIA.HE", Side.SELL, 5)
    assert sell.accepted
    assert broker.get_positions()[0].amount == 5
    assert broker.cash == pytest.approx(1_000 - 10 * 10.1 * 1.01 + 5 * 9.9 * 0.99)
