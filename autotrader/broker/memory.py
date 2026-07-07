"""Muistissa toimiva paper-broker offline- ja CI-ajoihin.

Tämä broker tekee idealisoidut täytöt viimeisellä yfinance-hinnalla sekä
konfiguroidulla komissiolla ja slippagella. Se ei ole virallinen
suorituskykylähde; DB:n equity curve on raportoinnin lähde.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from autotrader.broker.base import Account, BrokerClient, BrokerError, OrderResult, Position, Quote, Side
from autotrader.prices import PriceSource, YFinancePriceSource


@dataclass
class _MemoryPosition:
    amount: float
    average_price: float


class MemoryBroker(BrokerClient):
    """Yksinkertainen muistibroker testeihin ja dry run -ajoihin."""

    def __init__(
        self,
        initial_cash: float = 10_000.0,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.001,
        price_source: PriceSource | None = None,
    ):
        self.cash = float(initial_cash)
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.price_source = price_source or YFinancePriceSource()
        self.positions: dict[str, _MemoryPosition] = {}

    def get_account(self) -> Account:
        equity = self.cash
        for ticker, position in self.positions.items():
            quote = self.get_quote(ticker)
            equity += position.amount * quote.price
        return Account(account_key="memory", cash=self.cash, equity=equity, buying_power=self.cash)

    def get_positions(self) -> list[Position]:
        positions: list[Position] = []
        for ticker, position in sorted(self.positions.items()):
            quote = self.get_quote(ticker)
            positions.append(
                Position(
                    ticker=ticker,
                    amount=position.amount,
                    average_price=position.average_price,
                    current_price=quote.price,
                    market_value=position.amount * quote.price,
                )
            )
        return positions

    def get_quote(self, ticker: str) -> Quote:
        price = self.price_source.last_price(ticker)
        if price is None or price <= 0:
            raise BrokerError(f"Hinnan haku epäonnistui muistibrokerissa: {ticker}")
        return Quote(ticker=ticker.upper(), price=float(price), source="memory-yfinance")

    def place_market_order(self, ticker: str, side: Side, amount: float) -> OrderResult:
        if amount <= 0:
            raise BrokerError("Toimeksiannon määrä pitää olla positiivinen.")

        ticker = ticker.upper()
        quote = self.get_quote(ticker)
        if side == Side.BUY:
            fill_price = quote.price * (1 + self.slippage_pct)
            gross = fill_price * amount
            commission = gross * self.commission_pct
            total = gross + commission
            if total > self.cash:
                raise BrokerError("Muistibrokerin kassa ei riitä ostoon.")

            existing = self.positions.get(ticker)
            if existing:
                new_amount = existing.amount + amount
                new_avg = ((existing.amount * existing.average_price) + gross) / new_amount
                self.positions[ticker] = _MemoryPosition(amount=new_amount, average_price=new_avg)
            else:
                self.positions[ticker] = _MemoryPosition(amount=amount, average_price=fill_price)
            self.cash -= total
        else:
            existing = self.positions.get(ticker)
            if not existing or existing.amount < amount:
                raise BrokerError("Muistibrokerissa ei ole riittävää positiota myyntiin.")
            fill_price = quote.price * (1 - self.slippage_pct)
            gross = fill_price * amount
            commission = gross * self.commission_pct
            self.cash += gross - commission
            remaining = existing.amount - amount
            if remaining <= 0:
                del self.positions[ticker]
            else:
                self.positions[ticker] = _MemoryPosition(amount=remaining, average_price=existing.average_price)

        return OrderResult(
            broker_order_id=f"memory-{uuid4()}",
            accepted=True,
            message="Muistibroker täytti toimeksiannon.",
            raw={"ticker": ticker, "side": side.value, "amount": amount, "price": quote.price},
        )
