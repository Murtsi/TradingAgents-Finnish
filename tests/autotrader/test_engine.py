from __future__ import annotations

from datetime import date

import pandas as pd

from autotrader.analysis import AnalysisResult
from autotrader.broker.memory import MemoryBroker
from autotrader.config import TraderConfig
from autotrader.engine import AutotraderEngine
from autotrader.storage import Storage


class FakePriceSource:
    def history(self, ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        return pd.DataFrame({"Close": [10 + i * 0.05 for i in range(70)]})

    def last_price(self, ticker: str) -> float | None:
        if ticker == "^OMXHPI":
            return 10_000.0
        return 10.0


class FakeAnalyzer:
    def analyze(self, ticker: str, trade_date: str) -> AnalysisResult:
        return AnalysisResult(ticker=ticker, decision="BUY", final_state={"ticker": ticker, "date": trade_date})


def test_engine_end_to_end_memory_broker(tmp_path):
    config = TraderConfig(
        broker="memory",
        universe=["NOKIA.HE"],
        shortlist_size=1,
        max_analyses_per_run=1,
        max_position_pct=0.10,
        initial_cash=1_000,
        commission_pct=0,
        slippage_pct=0,
    )
    price_source = FakePriceSource()
    broker = MemoryBroker(initial_cash=1_000, commission_pct=0, slippage_pct=0, price_source=price_source)
    storage = Storage(f"sqlite:///{tmp_path / 'engine.sqlite3'}")
    engine = AutotraderEngine(
        config=config,
        storage=storage,
        broker=broker,
        price_source=price_source,
        analyzer=FakeAnalyzer(),
    )

    report = engine.run_once(run_date=date(2026, 6, 9), force=True)

    assert report.status == "completed"
    assert report.decisions == {"NOKIA.HE": "BUY"}
    assert report.approved_orders == 1
    assert broker.get_positions()[0].amount == 10
    assert storage.is_run_completed(date(2026, 6, 9))
