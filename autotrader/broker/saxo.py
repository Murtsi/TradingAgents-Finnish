"""Saxo Bank OpenAPI SIM -adapteri."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import requests

from autotrader.broker.base import Account, BrokerClient, BrokerError, OrderResult, Position, Quote, Side
from autotrader.config import TraderConfig
from autotrader.prices import PriceSource, YFinancePriceSource

logger = logging.getLogger(__name__)


class SaxoBroker(BrokerClient):
    """Saxo OpenAPI -adapteri SIM-ympäristöön.

    Auth: 24h one-day token Saxo Developer Portalista, lähetetään Bearer-tokenina.
    Live OAuth -polkua ei toteuteta tässä vaiheessa.
    """

    def __init__(
        self,
        config: TraderConfig,
        session: requests.Session | None = None,
        price_source: PriceSource | None = None,
    ):
        self.config = config
        self.base_url = config.saxo_rest_base.rstrip("/")
        self.session = session or requests.Session()
        self.price_source = price_source or YFinancePriceSource()
        self._uic_cache: dict[str, int] = dict(config.uic_overrides)
        if config.saxo_env != "sim":
            raise BrokerError("Saxo live -adapteri ei ole käytössä tässä vaiheessa.")
        if not config.saxo_token and not config.dry_run:
            raise BrokerError("SAXO_TOKEN puuttuu.")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.saxo_token or ''}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, headers=self._headers(), timeout=30, **kwargs)
        if response.status_code == 401:
            raise BrokerError("Saxo token hylättiin tai on vanhentunut (401). Hae uusi 24h SIM-token.")
        if not 200 <= response.status_code < 300:
            body = response.text[:500]
            raise BrokerError(f"Saxo API virhe {response.status_code}: {body}")
        if not response.content:
            return {}
        return response.json()

    def _first_data_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("Data")
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(payload, dict):
            return payload
        return {}

    def get_account(self) -> Account:
        accounts_payload = self._request("GET", "/port/v1/accounts/me")
        balance_payload = self._request("GET", "/port/v1/balances/me")
        account = self._first_data_item(accounts_payload)
        balance = self._first_data_item(balance_payload)
        account_key = account.get("AccountKey") or balance.get("AccountKey") or ""
        cash = float(balance.get("CashBalance") or balance.get("Cash") or 0.0)
        equity = float(balance.get("TotalValue") or balance.get("NetEquity") or cash)
        buying_power = float(balance.get("MarginAvailableForTrading") or balance.get("AvailableForTrading") or cash)
        currency = balance.get("Currency") or account.get("Currency") or "EUR"
        return Account(
            account_key=account_key,
            cash=cash,
            currency=currency,
            equity=equity,
            buying_power=buying_power,
        )

    def get_positions(self) -> list[Position]:
        payload = self._request("GET", "/port/v1/positions/me")
        data = payload.get("Data", [])
        positions: list[Position] = []
        for item in data:
            position = item.get("PositionBase") or item.get("Position") or item
            instrument = item.get("Instrument") or {}
            ticker = (
                instrument.get("Symbol")
                or instrument.get("Identifier")
                or position.get("Symbol")
                or str(position.get("Uic", ""))
            ).upper()
            amount = float(position.get("Amount") or position.get("NetPosition") or 0.0)
            if amount == 0:
                continue
            current_price = position.get("CurrentPrice") or position.get("MarketPrice")
            market_value = position.get("MarketValue") or position.get("Value")
            avg_price = position.get("OpenPrice") or position.get("AveragePrice")
            positions.append(
                Position(
                    ticker=ticker,
                    amount=amount,
                    current_price=float(current_price) if current_price is not None else None,
                    average_price=float(avg_price) if avg_price is not None else None,
                    market_value=float(market_value) if market_value is not None else 0.0,
                    currency=position.get("Currency") or "EUR",
                )
            )
        return positions

    def get_quote(self, ticker: str) -> Quote:
        price = self.price_source.last_price(ticker)
        if price is None or price <= 0:
            raise BrokerError(f"Hinnan haku epäonnistui: {ticker}")
        return Quote(ticker=ticker.upper(), price=float(price), source="yfinance")

    def resolve_uic(self, ticker: str) -> int:
        """Resolvoi ticker Saxon UIC-tunnukseksi ja cacheta tulos."""
        normalized = ticker.upper()
        if normalized in self._uic_cache:
            return self._uic_cache[normalized]

        keyword = normalized.split(".")[0]
        payload = self._request(
            "GET",
            f"/ref/v1/instruments?Keywords={quote(keyword)}&AssetTypes=Stock",
        )
        data = payload.get("Data", [])
        if not data:
            raise BrokerError(f"Saxo UIC -hakutulos tyhjä tickerille {ticker}.")

        chosen = data[0]
        for candidate in data:
            symbol = str(candidate.get("Symbol") or candidate.get("Identifier") or "").upper()
            if symbol == normalized or symbol == keyword:
                chosen = candidate
                break

        uic = chosen.get("Uic") or chosen.get("Identifier")
        if uic is None:
            raise BrokerError(f"Saxo UIC puuttuu hakutuloksesta tickerille {ticker}.")
        self._uic_cache[normalized] = int(uic)
        return int(uic)

    def place_market_order(self, ticker: str, side: Side, amount: float) -> OrderResult:
        account = self.get_account()
        uic = self.resolve_uic(ticker)
        body = {
            "AccountKey": account.account_key,
            "Uic": uic,
            "AssetType": "Stock",
            "BuySell": "Buy" if side == Side.BUY else "Sell",
            "Amount": amount,
            "OrderType": "Market",
            "ManualOrder": False,
            "OrderDuration": {"DurationType": "DayOrder"},
        }
        payload = self._request("POST", "/trade/v2/orders", json=body)
        order_id = payload.get("OrderId") or payload.get("OrderIds", [None])[0]
        return OrderResult(
            broker_order_id=str(order_id) if order_id is not None else None,
            accepted=True,
            message="Saxo SIM hyväksyi toimeksiannon.",
            raw=payload,
        )
