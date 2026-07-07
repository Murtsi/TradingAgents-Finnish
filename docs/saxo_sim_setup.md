# Saxo SIM -asetukset

Tämä ohje koskee vain Saxo Bank OpenAPI SIM -ympäristöä.

## Perusasetukset

REST base:

```text
https://gateway.saxobank.com/sim/openapi
```

Auth base:

```text
https://sim.logonvalidation.net
```

SIM käyttää Saxo Developer Portalista haettua 24 tunnin one-day tokenia. Aseta se ympäristömuuttujaan:

```text
SAXO_TOKEN=<token>
SAXO_ENV=sim
BROKER=saxo
```

## Tarkistettavat endpointit

```text
GET /port/v1/accounts/me
GET /port/v1/balances/me
GET /port/v1/positions/me
GET /ref/v1/instruments?Keywords=<sym>&AssetTypes=Stock
POST /trade/v2/orders
```

Order body:

```json
{
  "AccountKey": "...",
  "Uic": 12345,
  "AssetType": "Stock",
  "BuySell": "Buy",
  "Amount": 10,
  "OrderType": "Market",
  "ManualOrder": false,
  "OrderDuration": {
    "DurationType": "DayOrder"
  }
}
```

## UIC-kartoitus

Ennen SIM-ajoa tarkista vähintään `NOKIA.HE`, `NDA-FI.HE`, `NESTE.HE`, `UPM.HE` ja `KNEBV.HE` omassa SIM-tilissäsi. Tarvittaessa lisää manuaaliset ohitukset:

```text
SAXO_UIC_OVERRIDES=NOKIA.HE=12345,NDA-FI.HE=67890
```

## Rajaus

Live-OAuth, refresh-tokenit ja live-toimeksiannot ovat ulkona tästä vaiheesta.
