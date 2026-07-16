#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish pending ZhihuRec outbox rows.")
    parser.add_argument("--once", action="store_true", help="Publish at most one batch.")
    return parser.parse_args()


def main() -> None:
    from backend.app.config import get_settings
    from backend.app.events.outbox import OutboxPublisherWorker
    from backend.app.observability import configure_logging, start_worker_metrics_server

    args = parse_args()
    settings = get_settings()
    configure_logging()
    start_worker_metrics_server(settings.outbox_metrics_port)
    worker = OutboxPublisherWorker(settings)
    try:
        if args.once:
            worker.run_once()
        else:
            worker.run_forever()
    finally:
        worker.close()


if __name__ == "__main__":
    main()
