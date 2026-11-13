"""FFmpeg streaming runner for Media API (T6).

Implements streaming conversions, splitting, and compression using ffmpeg
subprocess stdin/stdout pipes, strictly avoiding buffering unbounded data to disk.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Generator


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg binary exists on PATH."""
    return shutil.which("ffmpeg") is not None


def run_ffmpeg_stream(
    args: list[str],
    input_stream: Generator[bytes, None, None] | bytes,
    *,
    chunk_size: int = 65536,
) -> Generator[bytes, None, None]:
    """Stream input through an ffmpeg pipeline and yield stdout chunks."""
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", *args]

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Stream stdin
    if isinstance(input_stream, bytes):
        proc.stdin.write(input_stream)
        proc.stdin.close()
    else:
        try:
            for chunk in input_stream:
                proc.stdin.write(chunk)
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    # Read stdout in chunks
    try:
        while True:
            chunk = proc.stdout.read(chunk_size)
            if not chunk:
                break
            yield chunk
    finally:
        proc.stdout.close()
        proc.stderr.close()
        proc.wait()

