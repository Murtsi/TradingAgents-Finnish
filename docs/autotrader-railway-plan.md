# KauppaAgentit → Railway Autotrader — Plan & Codex Build Spec

> **Status:** planning / handoff document. The implementation is to be built by Codex from the
> build prompt at the end of this document. This file is the spec, not the code.
>
> **Disclaimer:** Research/experimentation tool. Not investment advice. Real automated trading is
> the operator's own risk. Start in paper/simulation.

---

## 1. Goal

Turn KauppaAgentit (this repo — a Finnish fork of TradingAgents, today an *analysis-only* multi-agent
LLM pipeline) into a **daily autonomous trader** for Finnish/European equities that:

- funnels the stock universe through the **existing** multi-agent pipeline,
- executes into a **Saxo Bank OpenAPI SIM** (simulation) wallet for realistic, broker-grade fills,
- is built behind a **broker-abstraction interface** so going live is a credential swap, not a rewrite,
- runs **daily and unattended** on **Railway**,
- and reports an **equity curve + performance metrics** so the strategy can be evaluated and tuned.

Sequencing: **paper/SIM now → guardrailed live later.** No live trading in the first PR.

---

## 2. Current state (codebase scan)

- **Pipeline:** `TradingAgentsGraph.propagate(ticker, date)` → rating ∈ `BUY/OVERWEIGHT/HOLD/UNDERWEIGHT/SELL`
  (`tradingagents/graph/`). Reused as-is.
- **Interfaces:** interactive CLI (`cli/main.py`), minimal `main.py`, Telegram bot
  (`telegram_bot/`, long-poll: `/analysoi`, `/salkku` watchlist, `/halytys` alerts, whitelist).
- **Data:** yfinance (`.HE` suffix), Alpha Vantage, Finnish news scrapers.
- **Gaps for autonomous trading:**
  - **No scheduler** — everything is on-demand.
  - **No broker / execution layer** — analysis only.
  - **`db/schema.sql` exists but is unused** — runtime state lives in JSON under `~/.kauppaagentit/`
    (lost on every Railway redeploy).
  - **`telegram_bot/task_runner.py`** is `max_workers=1` + a global `asyncio.Lock` (documented "B→C"
    Celery migration point) — strictly one analysis at a time.
  - **No Railway/Procfile/nixpacks config**; Dockerfile entrypoint is hard-wired to the CLI.

---

## 3. Decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| Execution end-goal | Fully automated live | Operator's own account |
| Start mode | Paper → **Saxo SIM** → live | Realistic fills, de-risked ramp |
| Wallet (Phase 1) | Saxo Bank OpenAPI **SIM** | Real broker matching engine, official REST, Railway-friendly, same code → live |
| Architecture | One `BrokerClient` interface | Swap SIM→live by credentials |
| Universe | Finnish + European equities | Broad coverage via yfinance |
| Throughput | Cheap screener → deep LLM on a shortlist | Makes "all stocks" affordable |
| Persistence | SQLite (local) / Postgres (Railway) | Wire the existing `db/schema.sql` |
| Evaluation | Equity-curve + metrics vs OMXH benchmark | The "how good is it" dial |
| Safety | Guardrails + kill-switch, paper-first | Live impossible without explicit flag |

---

## 4. Tool evaluation (why Saxo SIM)

Verified against current docs:

- **TradingView paper** — ❌ as an execution backend. No external order API; automation flows *out*
  (Pine Script → webhook), and the LLM agents can't live in Pine. Manual simulator only.
- **Nordnet External API** — ❌ for a Finnish user. Order API exists and a test env
  (`api.test.nordnet.se`) exists, **but production access is Swedish-customers-only**, certification-
  gated, "not for 3rd party," and there is **no personal paper/demo account** — the test env is a
  shared integration sandbox, not a performance wallet.
- **Saxo Bank OpenAPI SIM** — ✅ chosen. Real broker simulation with realistic fills, official REST,
  free ~$100k sim account, Helsinki + European coverage, no desktop gateway (Railway-clean), and the
  **same code path goes live**.
- **Interactive Brokers paper** — ✅ viable alternative (persistent paper account, very capable) but
  needs a TWS/IB Gateway sidecar — heavier on Railway. Kept as a future adapter option.

Sources: Saxo developer portal (environments, order-placement), Nordnet externalapi docs/FAQ,
TradingView automation docs, IBKR API.

---

## 5. Architecture

### New `autotrader/` package

```
config.py          env-driven config + live-trading safety gate
broker/base.py     BrokerClient ABC + Account/Position/Quote/OrderResult dataclasses
broker/saxo.py     Saxo SIM adapter (auth, UIC lookup, balances/positions, order placement)
broker/memory.py   offline/CI wallet (idealized fills — NOT a performance source)
prices.py          yfinance wrapper (injectable for tests)
universe.py        FI + European universe (from omxh_utils OMXH_COMPANY_NAMES + extras)
screener.py        cheap quant funnel (momentum / RSI / SMA) → shortlist, no LLM
analysis.py        bridge to TradingAgentsGraph.propagate()
portfolio.py       decisions → target weights → orders + sizing
risk.py            caps, kill-switch, drawdown halt (applied BEFORE execution)
metrics.py         equity curve + CAGR/maxDD/Sharpe vs OMXH benchmark
storage.py         SQLite/Postgres; wires the unused db/schema.sql; idempotency
engine.py          daily orchestrator + `--once` CLI
scheduler.py       APScheduler (Europe/Helsinki) + /health for Railway
notify.py          Telegram daily report
market_calendar.py is_trading_day() with Nasdaq Helsinki holidays
```

### Broker ladder

```
PaperBroker/memory (offline+CI) → Saxo SIM (realistic paper) → Saxo live (guardrails on)
```

### Railway topology

```
Postgres (managed plugin)  ── wallet, positions, orders, fills, runs, decisions, equity_curve
trader-worker              ── APScheduler @ Europe/Helsinki, OMXH calendar gate, /health
                              daily: universe → screen → deep-analyze → risk → orders → persist → notify
telegram-bot               ── always-on: daily report, status, kill-switch, /analysoi
```

### Daily funnel (makes "all stocks" tractable)

1. **Cheap screen** (no LLM) over the whole universe → rank → top-N candidates + current holdings.
2. **Deep pipeline** (expensive) only on that shortlist → `OSTA/PIDÄ/MYY`.
3. Portfolio → risk caps → execute → persist → metrics → Telegram.

---

## 6. Phased roadmap

- **Phase 0 — Foundations:** Postgres wiring + migrations, trader config + `TRADING_MODE`, multi-service
  entrypoints, budgeted concurrency (lift the `max_workers=1` lock), OMXH calendar + Helsinki schedule.
- **Phase 1 — Saxo SIM paper auto-trader (this PR's target):** universe + screener funnel, broker
  interface + Saxo SIM adapter + memory broker, portfolio/risk engine, daily scheduler, metrics harness,
  Telegram report, Railway deploy. Runs offline (`memory`) for tests/CI until a Saxo token is added.
- **Phase 2 — Validate Saxo SIM:** real 24h token, ticker→UIC symbology verification, order lifecycle +
  reconciliation against the SIM account.
- **Phase 3 — Guardrailed live:** Saxo live creds + OAuth refresh, enable hard caps + kill-switch, ramp
  from tiny size. Optional approve-first intermediate.

---

## 7. What's left (Phase 1 build checklist)

- [ ] `autotrader/` package (modules in §5)
- [ ] Saxo SIM adapter: 24h token auth, UIC mapping + cache, balances/positions, market orders
- [ ] Memory broker for offline/CI
- [ ] Cheap screener funnel + FI/EU universe
- [ ] Portfolio sizing + risk caps + kill-switch + drawdown halt
- [ ] Metrics / equity-curve harness vs `^OMXHPI`
- [ ] Storage: wire `db/schema.sql`, SQLite + Postgres, migration runner, idempotency
- [ ] Move Telegram `salkku`/`halytys` + handlers' in-memory state into the DB
- [ ] Engine orchestrator + `--once`; APScheduler service + `/health`
- [ ] Parametrize Dockerfile entrypoint; `railway.json/toml`; deps `apscheduler`, `psycopg[binary]`
- [ ] Tests (mock LLM + yfinance + Saxo HTTP): screener, portfolio, every risk cap, memory fills,
      metrics, storage, Saxo adapter, engine e2e — existing suite stays green
- [ ] Docs: Saxo SIM setup guide, env vars, Railway deploy/runbook

---

## 8. Open items / defaults

| Item | Default | Notes |
|---|---|---|
| Starting wallet | €100,000 | Saxo SIM seeds ~$100k; memory broker uses this |
| Max position | 10% of equity | per-name cap |
| Cash buffer | 20% | minimum cash held |
| Drawdown halt | 25% | auto-stop new buys |
| Screener shortlist | top 15 + holdings | hard cap ~25 LLM analyses/day |
| LLM tier | Haiku | cheap for training; Sonnet for production |
| Universe breadth | OMXH (curated ~40) | optional +Nordics/+Europe via config |
| Run time | 10:15 Europe/Helsinki | after OMXH open |
| Benchmark | `^OMXHPI` | OMX Helsinki PI |

**Symbology caveat:** ticker→UIC mapping must be verified against a real Saxo SIM account (Codex can't
test without a token). Needs a manual-override map + an operator spot-check.

**Token caveat:** Saxo SIM issues **24h tokens only** (no refresh) — fine for a once-daily bot; decide
manual paste vs. a refresh helper. Live OAuth refresh is Phase 3.

---

## 9. Saxo SIM API reference (grounded — use as-is)

- SIM REST base: `https://gateway.saxobank.com/sim/openapi` · auth base: `https://sim.logonvalidation.net`
- Auth: 24h "one-day token" from the Developer Portal (no app creds for SIM); send as `Bearer`.
- Place order: `POST /trade/v2/orders`
  ```json
  {
    "AccountKey": "...", "Uic": 1234, "AssetType": "Stock",
    "BuySell": "Buy", "Amount": 100, "OrderType": "Market",
    "ManualOrder": false, "OrderDuration": {"DurationType": "DayOrder"}
  }
  ```
- UIC lookup: `GET /ref/v1/instruments?Keywords=<sym>&AssetTypes=Stock`
- Account/cash: `GET /port/v1/accounts/me`, `GET /port/v1/balances/me` · positions: `GET /port/v1/positions/me`

## 10. Pipeline integration facts

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.finnish_config import get_finnish_config

graph = TradingAgentsGraph(
    config=get_finnish_config(overrides),
    selected_analysts=["market", "social", "news", "fundamentals"],
    debug=False,
)
final_state, decision = graph.propagate(ticker, "YYYY-MM-DD")
# decision ∈ {BUY, OVERWEIGHT, HOLD, UNDERWEIGHT, SELL}
```

- `tradingagents/dataflows/omxh_utils.py`: `resolve_ticker()` (names → yfinance), `OMXH_COMPANY_NAMES`
  (curated ~40-ticker dict).
- `db/schema.sql`: existing Postgres schema (`analyysit`, `paatokset`, `portfolio`, `hintahistoria`) —
  currently unused; wire it in.

---

## 11. Codex build prompt

> Paste this into Codex to build Phase 0 + Phase 1.

```
Repo: KauppaAgentit (Finnish fork of TradingAgents). A multi-agent LangGraph pipeline that
outputs a per-stock rating (BUY/OVERWEIGHT/HOLD/UNDERWEIGHT/SELL). Today it's analysis-only
(interactive CLI + a Telegram bot). No scheduler, no broker, no live persistence.

GOAL: Build a new `autotrader/` package — a daily AUTONOMOUS trader for Finnish/European
equities that funnels the stock universe through the EXISTING LLM pipeline and executes into a
Saxo Bank OpenAPI SIM (simulation) account, behind a broker-abstraction interface so live is a
later credential swap. Deployable on Railway. PAPER/SIM ONLY in this PR — no live trading.

READ FIRST: tradingagents/finnish_config.py, tradingagents/graph/trading_graph.py (propagate),
tradingagents/graph/signal_processing.py, tradingagents/dataflows/omxh_utils.py, telegram_bot/
task_runner.py, db/schema.sql, Dockerfile, pyproject.toml. Reuse the pipeline/config/dataflows —
do NOT rewrite the agents.

INTEGRATION FACTS (don't re-derive):
- Pipeline: graph = TradingAgentsGraph(config=get_finnish_config(overrides),
  selected_analysts=["market","social","news","fundamentals"], debug=False);
  final_state, decision = graph.propagate(ticker, "YYYY-MM-DD")
  -> decision in {BUY, OVERWEIGHT, HOLD, UNDERWEIGHT, SELL}.
- omxh_utils.resolve_ticker() maps names->yfinance (.HE/.ST/...); OMXH_COMPANY_NAMES is a
  curated ~40-ticker dict. Prices via yfinance.

SAXO SIM API (grounded - use as-is):
- SIM REST base: https://gateway.saxobank.com/sim/openapi ; auth base https://sim.logonvalidation.net
- Auth: 24h "one-day token" from the Saxo Developer Portal (no app creds for SIM); send as Bearer.
  Live uses OAuth code-grant - OUT OF SCOPE.
- Place order: POST /trade/v2/orders  body: {AccountKey, Uic, AssetType:"Stock",
  BuySell:"Buy"|"Sell", Amount, OrderType:"Market", ManualOrder:false,
  OrderDuration:{DurationType:"DayOrder"}}
- UIC lookup: GET /ref/v1/instruments?Keywords=<sym>&AssetTypes=Stock
- Account/cash: GET /port/v1/accounts/me, GET /port/v1/balances/me ; positions: GET /port/v1/positions/me

BUILD (autotrader/):
- config.py: TraderConfig from env - BROKER(saxo|memory), SAXO_ENV(sim|live), SAXO_TOKEN,
  ALLOW_LIVE (live IMPOSSIBLE without SAXO_ENV=live AND ALLOW_LIVE=1), TRADING_HALT kill-switch,
  AUTOTRADER_DRY_RUN, universe/screener/risk params, LLM tier, run time (Europe/Helsinki),
  DATABASE_URL, Telegram. validate() enforces the live gate.
- broker/base.py: BrokerClient ABC + dataclasses Account/Position/Quote/OrderResult, Side=BUY|SELL.
  No broker-specific types leak out.
- broker/saxo.py: Saxo SIM adapter - Bearer token, base-url by env, get_account (balances),
  get_positions, get_quote, resolve_uic (ticker->UIC via /ref/v1/instruments + manual-override map +
  cache), place_market_order (POST /trade/v2/orders). INJECT the HTTP session so it's unit-testable
  without creds. Handle 401/non-2xx clearly.
- broker/memory.py: in-memory wallet for offline/CI (idealized fills at yfinance price + commission/
  slippage). Document it is NOT the performance source. Used by tests.
- prices.py: yfinance history + last-price wrapper, injectable; pass index symbols (^...) through
  WITHOUT resolve_ticker.
- universe.py: FI+EU universe from OMXH_COMPANY_NAMES (+ optional Sweden, + config extras).
- screener.py: cheap quant pre-screen (momentum / RSI / SMA), rank, return top-N + current holdings.
  No LLM. Injectable price source.
- analysis.py: wrap propagate(); map LLM tier->Claude models; a failing ticker returns safe HOLD.
- portfolio.py: decisions -> target weights -> orders (BUY opens to max_position_pct; SELL closes;
  UNDERWEIGHT trims; HOLD or already-held = no-op). Deterministic, pure.
- risk.py: guardrails BEFORE execution - kill-switch (reject all), drawdown halt (block buys / allow
  sells), min cash buffer, max position %, max daily orders, max new buys. Trim or reject; return
  approved + rejected(reason).
- metrics.py: equity-curve metrics - total return, CAGR, max drawdown, vol, Sharpe, and vs OMXH
  benchmark (^OMXHPI). FIRST-CLASS: this is the "how good is it" output.
- storage.py: persistence on SQLite (default) AND Postgres (DATABASE_URL). Wire the existing
  db/schema.sql + tables runs/decisions/orders/equity_curve/uic_map/wallet. Idempotent (one run/day).
  Provide equity-curve read for metrics.
- engine.py: daily orchestrator - trading-calendar gate (FI holidays, Europe/Helsinki) -> idempotency
  -> account+positions -> universe->screener->shortlist(+holdings) -> LLM analyze (hard budget cap on #
  analyses) -> portfolio -> risk -> execute via active broker (unless dry-run) -> persist equity+metrics
  -> Telegram report. CLI: python -m autotrader.engine --once [--dry-run] [--force] [--date YYYY-MM-DD].
- scheduler.py: APScheduler cron (Europe/Helsinki, mon-fri, configurable time) + a /health HTTP
  endpoint for Railway. Railway-Cron path via --once.
- notify.py: Telegram daily report (reuse TELEGRAM_BOT_TOKEN + a chat id). Keep the disclaimer.
- market_calendar.py: is_trading_day() with Nasdaq Helsinki holidays (Easter-derived + fixed).

REFACTORS THIS NEEDS:
- Wire db/schema.sql (currently unused) + a migration runner. Move telegram_bot salkku/halytys +
  handlers' in-memory dicts into the DB so Railway redeploys don't wipe state.
- Lift the max_workers=1 + global asyncio.Lock in task_runner.py into a budgeted concurrency path
  for the batch (the documented "B->C migration"); keep per-API rate limits + the EUR budget cap.

DEPLOYMENT:
- Parametrize the Dockerfile (currently ENTRYPOINT ["tradingagents"]) for per-service start commands.
- Add railway.json/toml + a "Deploy on Railway" README: Postgres plugin, two services
  (worker: python -m autotrader.scheduler ; bot: python -m telegram_bot.bot), and all env vars.
- Update docker-compose.yml with postgres for local parity. Add deps: apscheduler, psycopg[binary].
- Add a Saxo SIM setup guide: register a dev app, get the 24h token, set SAXO_TOKEN, and verify the
  ticker->UIC mapping against your own SIM account.

TESTS (mock LLM + yfinance + Saxo HTTP; NO network, NO creds): screener ranking, portfolio order
mapping, EVERY risk cap (over-cap orders blocked), memory-broker fills/cash math, metrics math,
storage round-trips, Saxo adapter (mocked session: resolve_uic, order body, balances, 401), engine
end-to-end via the memory broker. Keep the existing suite green.

SAFETY / SCOPE: default BROKER=saxo, SAXO_ENV=sim. Live impossible without SAXO_ENV=live AND
ALLOW_LIVE=1. Log every intended order to the DB BEFORE placement; idempotent per trading day. Do
NOT implement the Saxo live order path or OAuth refresh - SIM 24h token + a documented live stub
only. Finnish UI strings, EUR, keep the disclaimer. Commit in logical chunks; open a PR explaining
the phased design and the EXACT env vars to run the SIM paper trader. Explicitly list what remains
for Phase 2 (validate Saxo SIM with real creds + reconciliation) and Phase 3 (live + OAuth).
```
