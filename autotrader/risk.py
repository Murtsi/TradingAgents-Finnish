"""Riskirajat ennen toimeksiantojen lähetystä."""

from __future__ import annotations

import math
from dataclasses import dataclass

from autotrader.broker.base import Account, Position, Side
from autotrader.config import TraderConfig
from autotrader.portfolio import ProposedOrder


@dataclass(frozen=True)
class RejectedOrder:
    """Hylätty toimeksianto ja syy."""

    order: ProposedOrder
    reason: str


@dataclass(frozen=True)
class RiskDecision:
    """Riskitarkastuksen tulos."""

    approved: list[ProposedOrder]
    rejected: list[RejectedOrder]


def _position_values(positions: list[Position]) -> dict[str, float]:
    return {position.ticker.upper(): position.market_value for position in positions}


def approve_orders(
    orders: list[ProposedOrder],
    account: Account,
    positions: list[Position],
    config: TraderConfig,
    current_drawdown_pct: float = 0.0,
) -> RiskDecision:
    """Sovella tappio-, kassa-, positio- ja päivärajat toimeksiantoihin."""
    if config.trading_halt:
        return RiskDecision([], [RejectedOrder(order, "TRADING_HALT on päällä") for order in orders])

    approved: list[ProposedOrder] = []
    rejected: list[RejectedOrder] = []
    equity = account.equity or account.cash
    cash_left = account.cash
    position_values = _position_values(positions)
    max_position_value = equity * config.max_position_pct
    min_cash = equity * config.min_cash_buffer_pct
    new_buys = 0

    for order in orders:
        if len(approved) >= config.max_daily_orders:
            rejected.append(RejectedOrder(order, "päivittäinen toimeksiantoraja täynnä"))
            continue

        if current_drawdown_pct >= config.drawdown_halt_pct and order.side == Side.BUY:
            rejected.append(RejectedOrder(order, "drawdown-halt estää uudet ostot"))
            continue

        candidate = order
        if order.side == Side.BUY:
            if new_buys >= config.max_new_buys:
                rejected.append(RejectedOrder(order, "uusien ostojen päiväraja täynnä"))
                continue

            existing_value = position_values.get(order.ticker.upper(), 0.0)
            position_room = max(0.0, max_position_value - existing_value)
            cash_room = max(0.0, cash_left - min_cash)
            allowed_notional = min(position_room, cash_room)
            allowed_amount = math.floor(allowed_notional / order.estimated_price)

            if allowed_amount <= 0:
                rejected.append(RejectedOrder(order, "kassa- tai positiokatto estää oston"))
                continue

            if allowed_amount < order.amount:
                candidate = ProposedOrder(
                    ticker=order.ticker,
                    side=order.side,
                    amount=float(allowed_amount),
                    estimated_price=order.estimated_price,
                    reason=f"{order.reason}; riskiraja trimmasi määrää",
                    target_weight=order.target_weight,
                )

            cash_left -= candidate.notional
            position_values[candidate.ticker.upper()] = existing_value + candidate.notional
            new_buys += 1

        approved.append(candidate)

    return RiskDecision(approved=approved, rejected=rejected)
