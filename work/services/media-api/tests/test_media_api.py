"""Actual local media HTTP contract, without mocked playable output."""

from __future__ import annotations

import media_app
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_API_ENABLE_EXPERIMENTAL", "1")
    monkeypatch.setenv("MEDIA_API_TOKEN", "synthetic-local-only-token")
    root = tmp_path / "spool"
    root.mkdir(mode=0o700)
    monkeypatch.setenv("MEDIA_SPOOL_ROOT", str(root))
    return TestClient(media_app.app, headers={"X-Media-Token": "synthetic-local-only-token"})


def test_healthz_checks_real_reviewed_tool_lock(client):
    reply = client.get("/healthz")
    assert reply.status_code == 200 and reply.json()["ffmpeg"] is True
    assert reply.json()["customer_uploads_enabled"] is False


def test_missing_tools_return_503_before_upload(client, monkeypatch):
    monkeypatch.setenv("MEDIA_TOOL_LOCK", "/nonexistent/openbot-media-lock")
    assert client.get("/healthz").status_code == 503
    assert client.post("/v1/convert", content=b"x").status_code == 503


def test_bad_media_returns_error_before_streaming_success(client):
    reply = client.post("/v1/convert?format=mp3", content=b"not media")
    assert reply.status_code == 422
    assert reply.headers["content-type"].startswith("application/json")


def test_payload_too_large_exceeds_cap_returns_413(client, monkeypatch):
    monkeypatch.setattr(media_app, "MAX_FILE_BYTES", 100)
    reply = client.post("/v1/convert", content=b"x" * 200)
    assert reply.status_code == 413
    assert "exceeded maximum allowed size" in reply.json()["detail"].lower()


@pytest.mark.parametrize("query", ["program=sh", "format=mp3&format=wav", "segment_time=nan"])
def test_unknown_duplicate_and_invalid_options_refused(client, query):
    reply = client.post("/v1/split?" + query, content=b"x")
    assert reply.status_code == 422


def test_split_no_longer_fakes_a_single_stream(client):
    # The real 3-segment ZIP/manifest/decode proof is in test_owned_media.
    # Invalid input is now a proper 422, not a fabricated successful segment.
    assert client.post("/v1/split?segment_time=1", content=b"invalid").status_code == 422
