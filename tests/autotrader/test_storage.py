from __future__ import annotations

from datetime import date

from autotrader.broker.base import Side
from autotrader.portfolio import ProposedOrder
from autotrader.storage import Storage


def test_storage_round_trip(tmp_path):
    storage = Storage(f"sqlite:///{tmp_path / 'autotrader.sqlite3'}")
    run_id = storage.start_run(date(2026, 6, 9), broker="memory", dry_run=True, metadata={"x": 1})
    storage.save_decision(run_id, "NOKIA.HE", "BUY", 1.2, {"ok": True})
    order_id = storage.log_order(
        run_id,
        ProposedOrder("NOKIA.HE", Side.BUY, 10, 4.2, "test", 0.1),
        status="INTENDED",
    )
    storage.update_order(order_id, "DRY_RUN")
    storage.save_equity(date(2026, 6, 9), equity=1_000, cash=900, benchmark_symbol="^OMXHPI", benchmark_price=10)
    storage.save_uic("NOKIA.HE", 12345)
    storage.add_watchlist_item(42, "NOKIA.HE", "NOKIA", "2026-06-09")
    storage.upsert_alert(
        42,
        {
            "ticker": "NOKIA.HE",
            "nimi": "NOKIA",
            "tyyppi": "lasku",
            "prosentti": 5.0,
            "hinta_luontihetkella": 4.0,
            "luotu": "2026-06-09",
        },
    )
    storage.save_telegram_report(100, "raportti", {"state": True})
    storage.finish_run(run_id, "completed")

    assert storage.is_run_completed(date(2026, 6, 9))
    assert storage.load_equity_curve()[0].equity == 1_000
    assert storage.load_benchmark_prices()[0] == 10
    assert storage.get_uic("NOKIA.HE") == 12345
    assert storage.list_watchlist(42)[0]["ticker"] == "NOKIA.HE"
    assert storage.list_alerts(42)[0]["nimi"] == "NOKIA"
    report, state = storage.get_telegram_report(100)
    assert report == "raportti"
    assert state == {"state": True}
