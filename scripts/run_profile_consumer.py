#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    from backend.app.config import get_settings
    from backend.app.events.consumer import run_profile_consumer
    from backend.app.observability import configure_logging, start_worker_metrics_server

    settings = get_settings()
    configure_logging()
    start_worker_metrics_server(settings.consumer_metrics_port)
    run_profile_consumer(settings)


if __name__ == "__main__":
    main()
