"""APScheduler-pohjainen päivittäinen ajastin Railwaylle."""

from __future__ import annotations

import argparse
import logging
import os
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from autotrader.config import TraderConfig
from autotrader.engine import AutotraderEngine

logger = logging.getLogger(__name__)


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args: object) -> None:
        return


def start_health_server(port: int) -> ThreadingHTTPServer:
    """Käynnistä kevyt health-palvelin taustasäikeessä."""
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _run_job(config: TraderConfig) -> None:
    engine = AutotraderEngine(config)
    engine.run_once(run_date=date.today(), force=False)


def main() -> None:
    logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)
    parser = argparse.ArgumentParser(description="KauppaAgentit autotrader scheduler")
    parser.add_argument("--once", action="store_true", help="Aja yksi kierros ja poistu Railway Cronia varten.")
    parser.add_argument("--force", action="store_true", help="Ohita kalenteri/idempotenssi --once-ajossa.")
    args = parser.parse_args()

    config = TraderConfig.from_env()
    if args.once:
        AutotraderEngine(config).run_once(run_date=date.today(), force=args.force)
        return

    port = int(os.getenv("PORT", "8000"))
    start_health_server(port)
    scheduler = BlockingScheduler(timezone=ZoneInfo(config.timezone))
    scheduler.add_job(
        _run_job,
        "cron",
        args=[config],
        day_of_week="mon-fri",
        hour=config.run_time.hour,
        minute=config.run_time.minute,
        id="autotrader_daily",
        replace_existing=True,
    )
    logger.info("Autotrader scheduler käynnissä portissa %s", port)
    scheduler.start()


if __name__ == "__main__":
    main()
