"""Broker-abstraktio.

BrokerClient piilottaa Saxo- ja muistibrokerien yksityiskohdat. Muut autotrader-
moduulit käyttävät vain näitä dataluokkia, jotta SIM -> live -siirtymä ei vuoda
portfolio-, riski- tai engine-logiikkaan.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Side(str, Enum):
    """Kaupankäynnin puoli."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Account:
    """Tilin kassaan ja arvoon liittyvä yhteenveto euroissa."""

    account_key: str
    cash: float
    currency: str = "EUR"
    equity: float | None = None
    buying_power: float | None = None


@dataclass(frozen=True)
class Position:
    """Yksittäinen positio."""

    ticker: str
    amount: float
    market_value: float
    average_price: float | None = None
    current_price: float | None = None
    currency: str = "EUR"


@dataclass(frozen=True)
class Quote:
    """Viimeisin noteeraus tai arvioitu täyttöhinta."""

    ticker: str
    price: float
    currency: str = "EUR"
    source: str = "unknown"


@dataclass(frozen=True)
class OrderResult:
    """Brokerin palauttama toimeksiannon lopputulos."""

    broker_order_id: str | None
    accepted: bool
    message: str
    raw: dict[str, Any] = field(default_factory=dict)


class BrokerError(RuntimeError):
    """Broker-kutsun virhe, joka voidaan raportoida käyttäjälle selkeästi."""


class BrokerClient(ABC):
    """Yhteinen broker-rajapinta SIM- ja muistibrokereille."""

    @abstractmethod
    def get_account(self) -> Account:
        """Palauta tilin kassatilanne."""

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Palauta avoimet positiot."""

    @abstractmethod
    def get_quote(self, ticker: str) -> Quote:
        """Palauta viimeisin hinta tickerille."""

    @abstractmethod
    def place_market_order(self, ticker: str, side: Side, amount: float) -> OrderResult:
        """Lähetä markkinatoimeksianto brokerille."""
