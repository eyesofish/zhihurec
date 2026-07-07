#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main() -> None:
    from backend.app.events.consumer import run_profile_consumer

    run_profile_consumer()


if __name__ == "__main__":
    main()
