from __future__ import annotations

import pandas as pd

from autotrader.screener import screen_universe


class FakePriceSource:
    def __init__(self, closes: dict[str, list[float]]):
        self.closes = closes

    def history(self, ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        return pd.DataFrame({"Close": self.closes[ticker]})

    def last_price(self, ticker: str) -> float | None:
        return self.closes[ticker][-1]


def test_screener_ranks_momentum_and_includes_holdings():
    prices = FakePriceSource(
        {
            "A.HE": [10 + i * 0.2 for i in range(70)],
            "B.HE": [30 - i * 0.1 for i in range(70)],
            "C.HE": [15 + i * 0.01 for i in range(70)],
        }
    )

    result = screen_universe(["A.HE", "B.HE"], holdings=["C.HE"], price_source=prices, top_n=1)

    assert result[0].ticker == "A.HE"
    assert "C.HE" in {item.ticker for item in result}
