from __future__ import annotations

from dataclasses import replace

from autotrader.broker.base import Account, Position, Side
from autotrader.config import TraderConfig
from autotrader.portfolio import ProposedOrder
from autotrader.risk import approve_orders


def order(ticker: str, side: Side = Side.BUY, amount: float = 10, price: float = 10) -> ProposedOrder:
    return ProposedOrder(ticker=ticker, side=side, amount=amount, estimated_price=price, reason="test", target_weight=0.1)


def base_config() -> TraderConfig:
    return TraderConfig(
        broker="memory",
        max_position_pct=0.20,
        min_cash_buffer_pct=0.10,
        max_daily_orders=3,
        max_new_buys=2,
        drawdown_halt_pct=0.15,
    )


def test_risk_kill_switch_rejects_all():
    result = approve_orders([order("A.HE")], Account("x", cash=1_000, equity=1_000), [], replace(base_config(), trading_halt=True))
    assert not result.approved
    assert result.rejected[0].reason.startswith("TRADING_HALT")


def test_risk_drawdown_blocks_buys_allows_sells():
    orders = [order("A.HE", Side.BUY), order("B.HE", Side.SELL)]
    result = approve_orders(orders, Account("x", cash=1_000, equity=1_000), [], base_config(), current_drawdown_pct=0.20)
    assert [item.side for item in result.approved] == [Side.SELL]
    assert "drawdown" in result.rejected[0].reason


def test_risk_trims_to_cash_buffer_and_position_cap():
    cfg = base_config()
    account = Account("x", cash=500, equity=1_000)
    result = approve_orders([order("A.HE", amount=100, price=10)], account, [], cfg)
    assert result.approved[0].amount == 20


def test_risk_rejects_when_cash_buffer_leaves_no_room():
    cfg = base_config()
    account = Account("x", cash=100, equity=1_000)
    result = approve_orders([order("A.HE", amount=1, price=10)], account, [], cfg)
    assert not result.approved
    assert "kassa" in result.rejected[0].reason


def test_risk_daily_order_limit():
    cfg = replace(base_config(), max_daily_orders=1, max_new_buys=3)
    result = approve_orders([order("A.HE"), order("B.HE")], Account("x", cash=1_000, equity=1_000), [], cfg)
    assert len(result.approved) == 1
    assert "päivittäinen" in result.rejected[0].reason


def test_risk_new_buy_limit():
    cfg = replace(base_config(), max_new_buys=1, max_daily_orders=3)
    result = approve_orders([order("A.HE"), order("B.HE")], Account("x", cash=1_000, equity=1_000), [], cfg)
    assert len(result.approved) == 1
    assert "uusien ostojen" in result.rejected[0].reason


def test_risk_existing_position_cap_rejects_extra_buy():
    cfg = base_config()
    positions = [Position(ticker="A.HE", amount=20, market_value=200)]
    result = approve_orders([order("A.HE", amount=1, price=10)], Account("x", cash=1_000, equity=1_000), positions, cfg)
    assert not result.approved
    assert "positiokatto" in result.rejected[0].reason
