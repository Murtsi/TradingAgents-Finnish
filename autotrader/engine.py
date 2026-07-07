"""Päivittäinen autotrader-orchestrator."""

from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from datetime import date
from typing import Any

from autotrader.analysis import AnalysisResult, PipelineAnalyzer
from autotrader.broker.base import BrokerClient, BrokerError
from autotrader.broker.memory import MemoryBroker
from autotrader.broker.saxo import SaxoBroker
from autotrader.config import TraderConfig
from autotrader.market_calendar import is_trading_day
from autotrader.metrics import calculate_metrics
from autotrader.notify import DailyReport, send_telegram_report
from autotrader.portfolio import ProposedOrder, build_orders
from autotrader.prices import PriceSource, YFinancePriceSource
from autotrader.risk import approve_orders
from autotrader.screener import ScreeningCandidate, screen_universe
from autotrader.storage import Storage, get_storage
from autotrader.universe import build_universe

logger = logging.getLogger(__name__)


def create_broker(config: TraderConfig, price_source: PriceSource | None = None) -> BrokerClient:
    """Luo aktiivinen broker. Dry run ilman Saxo-tokenia käyttää muistibrokeria."""
    price_source = price_source or YFinancePriceSource()
    if config.broker == "memory" or (config.dry_run and not config.saxo_token):
        return MemoryBroker(
            initial_cash=config.initial_cash,
            commission_pct=config.commission_pct,
            slippage_pct=config.slippage_pct,
            price_source=price_source,
        )
    return SaxoBroker(config=config, price_source=price_source)


class AutotraderEngine:
    """Yksi päiväajo: kalenteri -> seulonta -> LLM -> riski -> SIM -> raportti."""

    def __init__(
        self,
        config: TraderConfig,
        storage: Storage | None = None,
        broker: BrokerClient | None = None,
        price_source: PriceSource | None = None,
        analyzer: PipelineAnalyzer | None = None,
    ):
        self.config = config
        self.price_source = price_source or YFinancePriceSource()
        self.storage = storage or get_storage(config.database_url)
        self.broker = broker or create_broker(config, self.price_source)
        self.analyzer = analyzer or PipelineAnalyzer(config)

    def _current_drawdown(self) -> float:
        points = self.storage.load_equity_curve()
        return calculate_metrics(points).max_drawdown if points else 0.0

    def _candidate_prices(self, candidates: list[ScreeningCandidate]) -> dict[str, float]:
        prices = {candidate.ticker: candidate.latest_price for candidate in candidates}
        return prices

    def _save_intended_orders(self, run_id: int, orders: list[ProposedOrder]) -> None:
        for order in orders:
            self.storage.log_order(run_id, order, status="INTENDED", reason=order.reason)

    def run_once(self, run_date: date | None = None, force: bool = False) -> DailyReport:
        """Aja yksi päivittäinen kierros."""
        run_date = run_date or date.today()
        if not force and not is_trading_day(run_date):
            metrics = calculate_metrics(self.storage.load_equity_curve())
            return DailyReport(
                run_date=str(run_date),
                status="skipped_non_trading_day",
                decisions={},
                approved_orders=0,
                rejected_orders=0,
                equity=0.0,
                metrics=metrics,
                dry_run=self.config.dry_run,
            )

        if not force and self.storage.is_run_completed(run_date):
            metrics = calculate_metrics(self.storage.load_equity_curve(), self.storage.load_benchmark_prices())
            return DailyReport(
                run_date=str(run_date),
                status="skipped_already_completed",
                decisions={},
                approved_orders=0,
                rejected_orders=0,
                equity=0.0,
                metrics=metrics,
                dry_run=self.config.dry_run,
            )

        run_id = self.storage.start_run(
            run_date,
            broker=self.config.broker,
            dry_run=self.config.dry_run,
            metadata={
                "llm_tier": self.config.llm_tier,
                "shortlist_size": self.config.shortlist_size,
                "max_analyses_per_run": self.config.max_analyses_per_run,
            },
        )

        try:
            account = self.broker.get_account()
            positions = self.broker.get_positions()
            holdings = [position.ticker for position in positions if position.amount > 0]
            universe = build_universe(self.config)
            candidates = screen_universe(universe, holdings, self.price_source, self.config.shortlist_size)
            candidates = candidates[: self.config.max_analyses_per_run]
            prices = self._candidate_prices(candidates)

            analyses: list[AnalysisResult] = []
            for candidate in candidates:
                result = self.analyzer.analyze(candidate.ticker, str(run_date))
                analyses.append(result)
                self.storage.save_decision(
                    run_id=run_id,
                    ticker=candidate.ticker,
                    decision=result.decision,
                    score=candidate.score,
                    final_state=result.final_state,
                    error=result.error,
                )

            decisions = {result.ticker: result.decision for result in analyses}
            orders = build_orders(decisions, prices, account, positions, self.config)
            self._save_intended_orders(run_id, orders)

            risk = approve_orders(
                orders,
                account=account,
                positions=positions,
                config=self.config,
                current_drawdown_pct=self._current_drawdown(),
            )

            for rejected in risk.rejected:
                self.storage.log_order(
                    run_id,
                    rejected.order,
                    status="REJECTED",
                    reason=rejected.reason,
                )

            for order in risk.approved:
                order_id = self.storage.log_order(run_id, order, status="APPROVED", reason=order.reason)
                if self.config.dry_run:
                    self.storage.update_order(order_id, status="DRY_RUN", reason="Dry run: toimeksiantoa ei lähetetty.")
                    continue

                try:
                    result = self.broker.place_market_order(order.ticker, order.side, order.amount)
                    self.storage.update_order(
                        order_id,
                        status="PLACED",
                        broker_order_id=result.broker_order_id,
                        raw=result.raw,
                        reason=result.message,
                    )
                except BrokerError as exc:
                    self.storage.update_order(order_id, status="FAILED", reason=str(exc))

            final_account = self.broker.get_account()
            benchmark_price = self.price_source.last_price("^OMXHPI")
            self.storage.save_equity(
                run_date,
                equity=final_account.equity or final_account.cash,
                cash=final_account.cash,
                benchmark_symbol="^OMXHPI",
                benchmark_price=benchmark_price,
            )
            metrics = calculate_metrics(
                self.storage.load_equity_curve(),
                self.storage.load_benchmark_prices("^OMXHPI"),
            )
            report = DailyReport(
                run_date=str(run_date),
                status="completed",
                decisions=decisions,
                approved_orders=len(risk.approved),
                rejected_orders=len(risk.rejected),
                equity=final_account.equity or final_account.cash,
                metrics=metrics,
                dry_run=self.config.dry_run,
            )
            send_telegram_report(self.config.telegram_bot_token, self.config.telegram_chat_id, report)
            self.storage.finish_run(run_id, "completed")
            logger.info("Autotrader päiväajo valmis: %s", run_date)
            return report
        except Exception as exc:
            self.storage.finish_run(run_id, "failed", error=str(exc))
            logger.exception("Autotrader päiväajo epäonnistui")
            raise


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KauppaAgentit autotrader")
    parser.add_argument("--once", action="store_true", help="Aja yksi päiväajo ja poistu.")
    parser.add_argument("--dry-run", action="store_true", help="Älä lähetä toimeksiantoja.")
    parser.add_argument("--force", action="store_true", help="Ohita kalenteri ja idempotenssitarkistus.")
    parser.add_argument("--date", help="Ajon päivämäärä muodossa YYYY-MM-DD.")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)
    args = _parse_args()
    config = TraderConfig.from_env()
    if args.dry_run:
        config = replace(config, dry_run=True).validate()

    run_date = date.fromisoformat(args.date) if args.date else date.today()
    engine = AutotraderEngine(config)
    if args.once:
        report = engine.run_once(run_date=run_date, force=args.force)
        print(f"{report.status}: equity {report.equity:.2f} EUR")
        return

    report = engine.run_once(run_date=run_date, force=args.force)
    print(f"{report.status}: equity {report.equity:.2f} EUR")


if __name__ == "__main__":
    main()
