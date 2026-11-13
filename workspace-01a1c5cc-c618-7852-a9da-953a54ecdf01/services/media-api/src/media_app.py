"""OpenBot OS — Media API Service (FastAPI) (T6).

Provides streaming media transformation (split, convert, compress) without buffering
unbounded data to disk. Governed by Sentinel media-api venture policy.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ffmpeg_runner import is_ffmpeg_available, run_ffmpeg_stream

logger = logging.getLogger("media-api")
MAX_FILE_BYTES = 500 * 1024 * 1024  # 500 MB hard cap

app = FastAPI(title="OpenBot OS Media API", version="0.1.0")


@app.get("/healthz")
def healthz() -> JSONResponse:
    """Health check endpoint: verifies ffmpeg availability."""
    have_ffmpeg = is_ffmpeg_available()
    status_code = 200 if have_ffmpeg else 503
    return JSONResponse(
        {
            "ok": have_ffmpeg,
            "ffmpeg": have_ffmpeg,
            "venture": "media-api",
            "max_file_mb": MAX_FILE_BYTES // (1024 * 1024),
        },
        status_code=status_code,
    )


async def _stream_with_size_limit(request: Request, max_bytes: int | None = None):
    """Generator reading request body chunks while enforcing a strict byte cap."""
    cap = max_bytes if max_bytes is not None else MAX_FILE_BYTES
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > cap:
            raise HTTPException(
                status_code=413,
                detail=f"Upload exceeded maximum allowed size of {cap // (1024 * 1024)} MB. Please split before uploading.",
            )
        yield chunk


@app.post("/v1/convert")
async def convert_endpoint(
    request: Request,
    target_format: str = Query("mp3", alias="format"),
) -> StreamingResponse:
    """Convert media format in a pure stream (no disk buffering)."""
    if not is_ffmpeg_available():
        raise HTTPException(status_code=503, detail="ffmpeg binary not available")

    input_stream = _stream_with_size_limit(request)
    ffmpeg_args = ["-i", "pipe:0", "-f", target_format, "pipe:1"]

    # Wrap async stream into synchronous chunks generator for subprocess pipe
    sync_chunks = []
    async for chunk in input_stream:
        sync_chunks.append(chunk)

    output_stream = run_ffmpeg_stream(ffmpeg_args, b"".join(sync_chunks))
    return StreamingResponse(output_stream, media_type=f"audio/{target_format}")


@app.post("/v1/split")
async def split_endpoint(
    request: Request,
    segment_seconds: int = Query(60, alias="segment_time"),
    target_format: str = Query("mp3", alias="format"),
) -> StreamingResponse:
    """Split media into segments streaming directly through pipe."""
    if not is_ffmpeg_available():
        raise HTTPException(status_code=503, detail="ffmpeg binary not available")

    input_stream = _stream_with_size_limit(request)
    ffmpeg_args = [
        "-i", "pipe:0",
        "-f", "segment",
        "-segment_time", str(segment_seconds),
        "-c", "copy",
        "pipe:1",
    ]

    sync_chunks = []
    async for chunk in input_stream:
        sync_chunks.append(chunk)

    output_stream = run_ffmpeg_stream(ffmpeg_args, b"".join(sync_chunks))
    return StreamingResponse(output_stream, media_type="application/octet-stream")


@app.post("/v1/compress")
async def compress_endpoint(
    request: Request,
    bitrate: str = Query("128k"),
    target_format: str = Query("mp3", alias="format"),
) -> StreamingResponse:
    """Compress media stream to target bitrate."""
    if not is_ffmpeg_available():
        raise HTTPException(status_code=503, detail="ffmpeg binary not available")

    input_stream = _stream_with_size_limit(request)
    ffmpeg_args = ["-i", "pipe:0", "-b:a", bitrate, "-f", target_format, "pipe:1"]

    sync_chunks = []
    async for chunk in input_stream:
        sync_chunks.append(chunk)

    output_stream = run_ffmpeg_stream(ffmpeg_args, b"".join(sync_chunks))
    return StreamingResponse(output_stream, media_type=f"audio/{target_format}")
