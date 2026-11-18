#!/usr/bin/env python3
"""Real 250 MB owned-WAV exercise and five 100 MB local-host timing samples.

Not target-owner-host p95 acceptance. Media/dependencies stay in an explicit cache.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import threading
import time
import wave
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "services/media-api/src")]
from owned_media import MediaEngine  # noqa: E402 - explicit standalone source root


def wave_file(path, size):
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(192000)
        remaining = size
        block = b"\0" * 65536
        while remaining:
            n = min(remaining, len(block))
            handle.writeframesraw(block[:n])
            remaining -= n


def run(source, spool):
    start = time.monotonic()
    peaks = {"parent_rss_kb": 0, "job_disk_bytes": 0}
    done = threading.Event()

    def sample():
        while not done.wait(0.005):
            for line in Path(f"/proc/{os.getpid()}/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    peaks["parent_rss_kb"] = max(peaks["parent_rss_kb"], int(line.split()[1]))
            try:
                disk = sum(p.stat().st_size for p in spool.glob("media-*/*") if p.is_file())
                peaks["job_disk_bytes"] = max(peaks["job_disk_bytes"], disk)
            except FileNotFoundError:
                pass

    monitor = threading.Thread(target=sample, daemon=True)
    monitor.start()
    try:
        with MediaEngine(spool, timeout=120) as engine:
            with source.open("rb") as src, (engine.directory / "input.media").open("xb") as dest:
                while block := src.read(65536):
                    engine.append(dest, block)
            result = engine.run("audio", {"format": "mp3", "bitrate": "128k"})
            record = {
                "input_bytes": source.stat().st_size,
                "output": result["outputs"],
                "processes": result["processes"],
                "elapsed_seconds": time.monotonic() - start,
            }
    finally:
        done.set()
        monitor.join()
    return {**record, **peaks, "spool_empty": not list(spool.glob("media-*"))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    args.cache = args.cache.resolve()
    args.cache.mkdir(parents=True, exist_ok=True)
    spool = args.cache / "private-spool"
    spool.mkdir(mode=0o700, exist_ok=True)
    source = args.cache / "synthetic-250MB.wav"
    wave_file(source, 250000000)
    large = run(source, spool)
    source.unlink()
    source = args.cache / "synthetic-100MB.wav"
    wave_file(source, 100000000)
    samples = [run(source, spool) for _ in range(5)]
    source.unlink()
    timings = sorted(s["elapsed_seconds"] for s in samples)
    result = {
        "schema": "openbot.owned-media-benchmark/1",
        "large_input": large,
        "samples_100MB": samples,
        "n": len(samples),
        "mean_seconds": statistics.mean(timings),
        "sample_p95_nearest_rank_seconds": timings[math.ceil(0.95 * len(timings)) - 1],
        "measurement_host": "Arena sandbox Linux, not owner-selected deployment host",
        "target_host_accepted": False,
        "latency_slo_proven": False,
        "input_note": "Decimal payload bytes plus 44-byte WAV header; fixed synthetic silence",
        "sampling_note": "5 samples only; includes bounded spool, encode, probe and full decode",
    }
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    assert large["spool_empty"] and all(s["spool_empty"] for s in samples)
    assert all(p["reaped"] for s in [large, *samples] for p in s["processes"])
    print(
        json.dumps(
            {
                "large_bytes": large["input_bytes"],
                "large_seconds": large["elapsed_seconds"],
                "sample_p95_seconds": result["sample_p95_nearest_rank_seconds"],
                "n": 5,
                "all_reaped": True,
                "target_host_accepted": False,
            }
        )
    )


if __name__ == "__main__":
    main()
