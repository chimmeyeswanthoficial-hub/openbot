"""Default-off bounded, token-protected LOCAL OWNED/SYNTHETIC media experiment.

Not mounted in the execution server. No customer uploads/generative video. Real
segments are returned only after each segment is independently probed/decoded.
"""

from __future__ import annotations

import asyncio
import hmac
import os
import threading
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from ffmpeg_runner import MediaError, is_ffmpeg_available
from ffmpeg_runner import run_ffmpeg_stream as run_ffmpeg_stream  # explicit compatibility export
from owned_media import MAX_INPUT, MediaEngine
from starlette.requests import ClientDisconnect

MAX_FILE_BYTES = MAX_INPUT


def spool_root():
    value = os.environ.get("MEDIA_SPOOL_ROOT", "")
    if not value or not Path(value).is_absolute():
        raise MediaError("explicit_private_spool_required", 503)
    return value


@asynccontextmanager
async def lifecycle(_app):
    if os.environ.get("MEDIA_API_ENABLE_EXPERIMENTAL") == "1":
        MediaEngine.recover(spool_root())
    yield


app = FastAPI(title="OpenBot Local Owned Media", version="0.2.0", lifespan=lifecycle)


def require_experiment(x_media_token: str | None = Header(default=None)):
    expected = os.environ.get("MEDIA_API_TOKEN", "")
    if os.environ.get("MEDIA_API_ENABLE_EXPERIMENTAL") != "1" or not expected:
        raise HTTPException(503, "Media API disabled: local owned experiment only")
    if not x_media_token or not hmac.compare_digest(x_media_token, expected):
        raise HTTPException(401, "valid local media experiment token required")


@app.exception_handler(MediaError)
async def media_error(_request, exc):
    return JSONResponse({"detail": exc.code}, status_code=exc.status)


@app.get("/healthz")
def healthz():
    available = is_ffmpeg_available()
    return JSONResponse(
        {
            "ok": available,
            "ffmpeg": available,
            "venture": "media-api",
            "max_file_mb": MAX_FILE_BYTES // (1024 * 1024),
            "customer_uploads_enabled": False,
        },
        status_code=200 if available else 503,
    )


class ScopedResponse(StreamingResponse):
    def __init__(self, engine, result):
        self.engine = engine

        async def chunks():
            with result["path"].open("rb") as handle:
                while block := handle.read(65536):
                    yield block
                    await asyncio.sleep(0)

        super().__init__(
            chunks(),
            media_type=result["media_type"],
            headers={
                "Content-Disposition": f'attachment; filename="{result["path"].name}"',
                "Content-Length": str(result["path"].stat().st_size),
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "X-OpenBot-Media-Scope": "local-owned-synthetic-only",
            },
        )

    async def __call__(self, scope, receive, send):
        try:
            # Includes ASGI send/backpressure, not just time spent yielding chunks.
            async with asyncio.timeout(20):
                await super().__call__(scope, receive, send)
        finally:
            self.engine.close()


async def perform(request, operation):
    if not is_ffmpeg_available():
        raise MediaError("reviewed_media_tools_unavailable", 503)
    options = dict(request.query_params)
    mapping = {
        "format": "format",
        "bitrate": "bitrate",
        "segment_time": "segment_seconds",
        "start": "start",
        "duration": "duration",
        "width": "width",
        "height": "height",
        "text": "text",
    }
    if len(request.query_params.multi_items()) != len(options) or set(options) - set(mapping):
        raise MediaError("unknown_or_duplicate_option")
    try:
        options = {
            mapping[k]: (
                int(v)
                if k in {"width", "height"}
                else float(v)
                if k in {"segment_time", "start", "duration"}
                else v
            )
            for k, v in options.items()
        }
    except ValueError as exc:
        raise MediaError("invalid_option") from exc
    length = request.headers.get("content-length")
    if length and (not length.isdecimal() or int(length) > MAX_FILE_BYTES):
        raise MediaError("Upload exceeded maximum allowed size", 413)
    stop = threading.Event()
    engine = MediaEngine(spool_root(), timeout=90, cancelled=stop.is_set)
    task = None
    try:
        async with asyncio.timeout(90):
            with (engine.directory / "input.media").open("xb") as handle:
                async for block in request.stream():
                    engine.append(handle, block, cap=MAX_FILE_BYTES)
            task = asyncio.create_task(asyncio.to_thread(engine.run, operation, options))
            while not task.done():
                if await request.is_disconnected():
                    stop.set()
                    raise MediaError("client_disconnected", 499)
                await asyncio.wait({task}, timeout=0.025)
            result = task.result()
        return ScopedResponse(engine, result)
    except BaseException as exc:
        stop.set()
        if task is not None:
            # Shield cleanup: never remove the lease while a child can still write.
            with suppress(BaseException):
                await asyncio.shield(task)
        engine.close()
        if isinstance(exc, TimeoutError):
            raise MediaError("upload_or_job_deadline", 408) from exc
        if isinstance(exc, ClientDisconnect):
            raise MediaError("client_disconnected", 499) from exc
        raise


def route(operation):
    async def endpoint(request: Request):
        return await perform(request, operation)

    endpoint.__name__ = operation + "_endpoint"
    return endpoint


for operation in ("convert", "compress", "audio", "split", "cut", "scale", "captions", "concat"):
    app.post("/v1/" + operation, dependencies=[Depends(require_experiment)])(route(operation))
