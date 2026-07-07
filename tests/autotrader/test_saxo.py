from __future__ import annotations

import pytest

from autotrader.broker.base import BrokerError, Side
from autotrader.broker.saxo import SaxoBroker
from autotrader.config import TraderConfig


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.content = b"{}"

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = responses
        self.calls: list[dict] = []

    def request(self, method: str, url: str, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


def config() -> TraderConfig:
    return TraderConfig(broker="saxo", saxo_env="sim", saxo_token="token")


def test_saxo_balances_resolve_uic_and_order_body():
    session = FakeSession(
        [
            FakeResponse(200, {"Data": [{"AccountKey": "acc", "Currency": "EUR"}]}),
            FakeResponse(200, {"CashBalance": 1_000, "TotalValue": 1_200, "MarginAvailableForTrading": 900, "Currency": "EUR"}),
            FakeResponse(200, {"Data": [{"Symbol": "NOKIA", "Uic": 12345}]}),
            FakeResponse(200, {"OrderId": "order-1"}),
        ]
    )
    broker = SaxoBroker(config(), session=session)

    result = broker.place_market_order("NOKIA.HE", Side.BUY, 10)

    assert result.broker_order_id == "order-1"
    assert session.calls[0]["url"].endswith("/port/v1/accounts/me")
    assert session.calls[2]["url"].endswith("/ref/v1/instruments?Keywords=NOKIA&AssetTypes=Stock")
    body = session.calls[3]["json"]
    assert body == {
        "AccountKey": "acc",
        "Uic": 12345,
        "AssetType": "Stock",
        "BuySell": "Buy",
        "Amount": 10,
        "OrderType": "Market",
        "ManualOrder": False,
        "OrderDuration": {"DurationType": "DayOrder"},
    }


def test_saxo_401_is_clear_error():
    broker = SaxoBroker(config(), session=FakeSession([FakeResponse(401, text="expired")]))
    with pytest.raises(BrokerError, match="401"):
        broker.get_account()
