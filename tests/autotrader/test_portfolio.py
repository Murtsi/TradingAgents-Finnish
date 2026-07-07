from __future__ import annotations

from autotrader.broker.base import Account, Position, Side
from autotrader.config import TraderConfig
from autotrader.portfolio import build_orders


def test_portfolio_maps_decisions_to_orders():
    config = TraderConfig(broker="memory", max_position_pct=0.10, underweight_trim_pct=0.50)
    account = Account(account_key="test", cash=1_000, equity=1_000)
    positions = [
        Position(ticker="SELL.HE", amount=10, market_value=100, current_price=10),
        Position(ticker="TRIM.HE", amount=8, market_value=80, current_price=10),
        Position(ticker="HELD.HE", amount=5, market_value=50, current_price=10),
    ]
    decisions = {
        "BUY.HE": "BUY",
        "SELL.HE": "SELL",
        "TRIM.HE": "UNDERWEIGHT",
        "HELD.HE": "BUY",
        "HOLD.HE": "HOLD",
    }
    prices = {ticker: 10.0 for ticker in decisions}

    orders = build_orders(decisions, prices, account, positions, config)

    by_ticker = {order.ticker: order for order in orders}
    assert by_ticker["BUY.HE"].side == Side.BUY
    assert by_ticker["BUY.HE"].amount == 10
    assert by_ticker["SELL.HE"].side == Side.SELL
    assert by_ticker["SELL.HE"].amount == 10
    assert by_ticker["TRIM.HE"].amount == 4
    assert "HELD.HE" not in by_ticker
    assert "HOLD.HE" not in by_ticker
