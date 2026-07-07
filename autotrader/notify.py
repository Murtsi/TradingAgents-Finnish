"""Telegram-raportointi autotrader-ajosta."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from autotrader.metrics import EquityMetrics

logger = logging.getLogger(__name__)

SHORT_DISCLAIMER = (
    "Tämä on AI:n tuottama analyysi, ei sijoitussuositus. "
    "Tee sijoituspäätökset oman harkintasi mukaan."
)


@dataclass(frozen=True)
class DailyReport:
    """Päivittäisen autotrader-ajon tiivistelmä."""

    run_date: str
    status: str
    decisions: dict[str, str]
    approved_orders: int
    rejected_orders: int
    equity: float
    metrics: EquityMetrics
    dry_run: bool


def _signal_label(decision: str) -> str:
    labels = {
        "BUY": "[OSTA-SIGNAALI]",
        "OVERWEIGHT": "[POSITIIVINEN NÄKYMÄ]",
        "HOLD": "[PIDÄ-SIGNAALI]",
        "UNDERWEIGHT": "[NEGATIIVINEN NÄKYMÄ]",
        "SELL": "[MYY-SIGNAALI]",
    }
    return labels.get(decision.upper(), "[PIDÄ-SIGNAALI]")


def format_daily_report(report: DailyReport) -> str:
    """Muotoile Telegram-raportti ammattimaiseksi tekstiksi."""
    decisions = ", ".join(f"{ticker}: {_signal_label(decision)}" for ticker, decision in sorted(report.decisions.items()))
    if not decisions:
        decisions = "Ei analysoituja tickereitä"

    mode = "DRY RUN" if report.dry_run else "SIM"
    return (
        f"[AUTOTRADER] Päiväajo {report.run_date} ({mode})\n"
        f"Tila: {report.status}\n"
        f"Signaalit: {decisions}\n"
        f"Hyväksytyt toimeksiannot: {report.approved_orders}\n"
        f"Hylätyt toimeksiannot: {report.rejected_orders}\n"
        f"Equity: {report.equity:.2f} EUR\n"
        f"Kokonaistuotto: {report.metrics.total_return:.2%}\n"
        f"Max drawdown: {report.metrics.max_drawdown:.2%}\n"
        f"Sharpe: {report.metrics.sharpe:.2f}\n\n"
        f"{SHORT_DISCLAIMER}"
    )


def send_telegram_report(token: str | None, chat_id: str | None, report: DailyReport) -> bool:
    """Lähetä raportti Telegramiin, jos asetukset on annettu."""
    if not token or not chat_id:
        return False

    text = format_daily_report(report)
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=20,
    )
    if not 200 <= response.status_code < 300:
        logger.warning("Telegram-raportin lähetys epäonnistui: %s", response.text[:300])
        return False
    return True
