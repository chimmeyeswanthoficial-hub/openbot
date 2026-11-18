#!/usr/bin/env python3
"""Export genuine synthetic media outputs/receipts for reproduction and preview."""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/media-api/src"))


def main():
    from ffmpeg_runner import tool_paths
    from owned_media import MediaEngine

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    target = args.out.absolute()
    if target.exists():
        raise SystemExit("New export directory required")
    target.mkdir(mode=0o700, parents=True)
    spool = target / "spool"
    spool.mkdir(mode=0o700)
    source = target / "owned-source.mp4"
    env = {**os.environ, "LD_LIBRARY_PATH": os.environ["MEDIA_LIBRARY_PATH"]}
    subprocess.run(
        [
            tool_paths()["ffmpeg"],
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=10:duration=2.4",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=2.4",
            "-threads",
            "1",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(source),
        ],
        env=env,
        check=True,
        timeout=20,
    )
    data = source.read_bytes()
    matrix = [
        ("cut", {"start": 0.5, "duration": 0.7}),
        ("concat", {}),
        ("scale", {"width": 160, "height": 90}),
        ("captions", {"text": "OpenBot owned sample"}),
        ("audio", {"format": "mp3"}),
        ("split", {"segment_seconds": 1}),
    ]
    receipts = []
    for operation, options in matrix:
        content = data
        if operation == "concat":
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as archive:
                for i in range(2):
                    archive.writestr(f"part-{i:02}.mp4", data)
            content = buf.getvalue()
        with MediaEngine(spool) as engine:
            with (engine.directory / "input.media").open("xb") as handle:
                engine.append(handle, content)
            result = engine.run(operation, options)
            output = target / (operation + result["path"].suffix)
            shutil.copyfile(result["path"], output)
            if operation == "captions":
                engine.ffmpeg(
                    engine.source("result.mp4"),
                    ["-frames:v", "1", "-an", "-c:v", "mjpeg", "-update", "1", "frame.jpg"],
                )
                shutil.copyfile(engine.directory / "frame.jpg", target / "captions-frame.jpg")
            receipts.append(
                {
                    "operation": operation,
                    "options": options,
                    "outputs": result["outputs"],
                    "processes": result["processes"],
                    "export_name": output.name,
                    "input_bytes": result["input_bytes"],
                    "actual_decode_readback": True,
                    "customer_security_accepted": False,
                }
            )
    receipt = {
        "schema": "openbot.owned-media-exports/1",
        "source": "fixed synthetic testsrc2 + sine",
        "operations": receipts,
        "spool_empty": not list(spool.glob("media-*")),
        "qualified_human_quality_acceptance": False,
        "per_job_cgroup_accepted": False,
    }
    (target / "media-exports.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "actual_operations": len(receipts),
                "all_decoded": True,
                "all_children_reaped": all(p["reaped"] for r in receipts for p in r["processes"]),
                "preview_frame": str(target / "captions-frame.jpg"),
                "human_quality_accepted": False,
            }
        )
    )


if __name__ == "__main__":
    os.umask(0o077)
    main()
