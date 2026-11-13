"""Worker daemon entrypoint.

Runs Worker.tick() on a 60-second cycle with Sentinel policy validation,
logging {fired, refused} metrics per tick.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime

# Setup paths
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "services", "sentinel"))

from repository import Store  # noqa: E402
from runner import Worker, summarise  # noqa: E402
from sentinel_client import SentinelClient  # noqa: E402
from heartbeat import ping_deadman  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("worker")


def create_worker(
    sentinel_url: str | None = None,
    db_path: str | None = None,
    state_dir: str | None = None,
) -> Worker:
    store = Store(db_path or os.environ.get("SENTINEL_DB", ":memory:"))
    client = SentinelClient(base_url=sentinel_url)
    return Worker(store=store, sentinel=client.decide, state_dir=state_dir)


def run_loop(worker: Worker, interval_sec: int = 60, max_ticks: int | None = None, deadman_url: str | None = None) -> None:
    target_deadman = deadman_url or os.environ.get("DEADMAN_PING_URL", "")
    logger.info("Worker started. Checking due routines every %ds...", interval_sec)
    ticks = 0
    try:
        while True:
            now = datetime.now()
            results = worker.tick(when=now)
            summary = summarise(results)
            if summary["fired"] > 0 or summary["refused"] > 0:
                logger.info(
                    "Tick at %s: fired=%d refused=%d",
                    now.strftime("%Y-%m-%d %H:%M"),
                    summary["fired"],
                    summary["refused"],
                )
            if target_deadman:
                ping_deadman(target_deadman)
            ticks += 1
            if max_ticks and ticks >= max_ticks:
                break
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        logger.info("Worker stopped by keyboard interrupt.")


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenBot OS Worker Daemon")
    parser.add_argument("--sentinel-url", default=None, help="Sentinel endpoint URL")
    parser.add_argument("--interval", type=int, default=60, help="Tick interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run a single tick and exit")
    parser.add_argument("--deadman-url", default=None, help="Dead-man's switch heartbeat URL")
    args = parser.parse_args()

    worker = create_worker(sentinel_url=args.sentinel_url)
    if args.once:
        results = worker.tick()
        summary = summarise(results)
        deadman = args.deadman_url or os.environ.get("DEADMAN_PING_URL", "")
        if deadman:
            ping_deadman(deadman)
        print(f"Fired: {summary['fired']}, Refused: {summary['refused']}")
        for r in summary["detail"]:
            print(f"  - {r.get('routine')}: ok={r.get('ok')} code={r.get('code')}")
    else:
        run_loop(worker, interval_sec=args.interval, deadman_url=args.deadman_url)


if __name__ == "__main__":
    main()

