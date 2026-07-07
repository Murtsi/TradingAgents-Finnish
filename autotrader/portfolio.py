"""Päätösten muunto tavoitepainoiksi ja toimeksiannoiksi."""

from __future__ import annotations

import math
from dataclasses import dataclass

from autotrader.broker.base import Account, Position, Side
from autotrader.config import TraderConfig


@dataclass(frozen=True)
class ProposedOrder:
    """Puhdas, brokerista riippumaton toimeksiantoehdotus."""

    ticker: str
    side: Side
    amount: float
    estimated_price: float
    reason: str
    target_weight: float

    @property
    def notional(self) -> float:
        return self.amount * self.estimated_price


def _position_map(positions: list[Position]) -> dict[str, Position]:
    return {pos.ticker.upper(): pos for pos in positions if pos.amount > 0}


def target_weight_for_decision(decision: str, max_position_pct: float) -> float:
    """Päätössignaali -> tavoitepaino."""
    decision = decision.upper()
    if decision in {"BUY", "OVERWEIGHT"}:
        return max_position_pct
    if decision == "UNDERWEIGHT":
        return max_position_pct / 2
    return 0.0


def build_orders(
    decisions: dict[str, str],
    prices: dict[str, float],
    account: Account,
    positions: list[Position],
    config: TraderConfig,
) -> list[ProposedOrder]:
    """Muuta signaalit deterministisiksi toimeksiantoehdotuksiksi."""
    orders: list[ProposedOrder] = []
    held = _position_map(positions)
    equity = account.equity or account.cash

    for ticker, raw_decision in sorted(decisions.items()):
        decision = raw_decision.upper()
        price = prices.get(ticker)
        if not price or price <= 0:
            continue

        position = held.get(ticker.upper())
        target_weight = target_weight_for_decision(decision, config.max_position_pct)

        if decision in {"BUY", "OVERWEIGHT"}:
            if position and position.amount > 0:
                continue
            target_value = equity * target_weight
            amount = math.floor(target_value / price)
            if amount > 0:
                orders.append(
                    ProposedOrder(
                        ticker=ticker,
                        side=Side.BUY,
                        amount=float(amount),
                        estimated_price=price,
                        reason=f"{decision}-signaali avaa position",
                        target_weight=target_weight,
                    )
                )
            continue

        if decision == "SELL" and position and position.amount > 0:
            orders.append(
                ProposedOrder(
                    ticker=ticker,
                    side=Side.SELL,
                    amount=float(position.amount),
                    estimated_price=price,
                    reason="SELL-signaali sulkee position",
                    target_weight=0.0,
                )
            )
            continue

        if decision == "UNDERWEIGHT" and position and position.amount > 0:
            amount = math.ceil(position.amount * config.underweight_trim_pct)
            if amount > 0:
                orders.append(
                    ProposedOrder(
                        ticker=ticker,
                        side=Side.SELL,
                        amount=float(min(amount, position.amount)),
                        estimated_price=price,
                        reason="UNDERWEIGHT-signaali keventää positiota",
                        target_weight=target_weight,
                    )
                )

    return orders
