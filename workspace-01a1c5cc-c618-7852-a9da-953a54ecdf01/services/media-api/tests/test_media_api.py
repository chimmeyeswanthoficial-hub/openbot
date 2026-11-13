"""Tests for Media API service (T6)."""

from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

import media_app

client = TestClient(media_app.app)


def test_healthz_when_ffmpeg_missing_returns_503():
    with patch("media_app.is_ffmpeg_available", return_value=False):
        r = client.get("/healthz")
        assert r.status_code == 503
        data = r.json()
        assert data["ok"] is False
        assert data["ffmpeg"] is False


def test_healthz_when_ffmpeg_present_returns_200():
    with patch("media_app.is_ffmpeg_available", return_value=True):
        r = client.get("/healthz")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["ffmpeg"] is True
        assert data["venture"] == "media-api"


def test_convert_returns_streaming_response():
    with patch("media_app.is_ffmpeg_available", return_value=True):
        with patch("media_app.run_ffmpeg_stream", return_value=iter([b"converted-audio-chunk"])):
            r = client.post("/v1/convert?format=mp3", content=b"fake-input-audio-bytes")
            assert r.status_code == 200
            assert r.content == b"converted-audio-chunk"
            assert "audio/mp3" in r.headers.get("content-type", "")


def test_split_returns_streaming_response():
    with patch("media_app.is_ffmpeg_available", return_value=True):
        with patch("media_app.run_ffmpeg_stream", return_value=iter([b"split-segment-1", b"split-segment-2"])):
            r = client.post("/v1/split?segment_time=30&format=mp3", content=b"fake-media-bytes")
            assert r.status_code == 200
            assert b"split-segment-1" in r.content


def test_payload_too_large_exceeds_cap_returns_413():
    with patch("media_app.is_ffmpeg_available", return_value=True):
        with patch("media_app.run_ffmpeg_stream", return_value=iter([b""])):
            with patch("media_app.MAX_FILE_BYTES", 100):
                large_content = b"x" * 200
                r = client.post("/v1/convert?format=mp3", content=large_content)
                assert r.status_code == 413
                assert "exceeded maximum allowed size" in r.json()["detail"].lower()
