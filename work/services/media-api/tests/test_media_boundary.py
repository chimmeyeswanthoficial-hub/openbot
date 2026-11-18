"""Experimental media code cannot accept uploads by default or fake split success."""

from __future__ import annotations

from unittest.mock import patch

import media_app
import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("route", ["convert", "compress", "split"])
def test_media_routes_disabled_without_explicit_experiment_and_token(route, monkeypatch):
    monkeypatch.delenv("MEDIA_API_ENABLE_EXPERIMENTAL", raising=False)
    monkeypatch.delenv("MEDIA_API_TOKEN", raising=False)
    with (
        patch("media_app.is_ffmpeg_available", return_value=True),
        patch("media_app.run_ffmpeg_stream") as run,
    ):
        r = TestClient(media_app.app).post(f"/v1/{route}", content=b"not-allowed")
    assert r.status_code == 503
    run.assert_not_called()


@pytest.mark.parametrize("headers", [{}, {"X-Media-Token": "wrong"}])
def test_experiment_still_needs_valid_server_token(headers, monkeypatch):
    monkeypatch.setenv("MEDIA_API_ENABLE_EXPERIMENTAL", "1")
    monkeypatch.setenv("MEDIA_API_TOKEN", "synthetic-local-only-token")
    with (
        patch("media_app.is_ffmpeg_available", return_value=True),
        patch("media_app.run_ffmpeg_stream") as run,
    ):
        r = TestClient(media_app.app).post("/v1/convert", headers=headers, content=b"not-allowed")
    assert r.status_code == 401
    run.assert_not_called()


def test_split_customer_uploads_stay_disabled_even_with_tooling_available(monkeypatch):
    monkeypatch.delenv("MEDIA_API_ENABLE_EXPERIMENTAL", raising=False)
    monkeypatch.setenv("MEDIA_API_TOKEN", "synthetic-local-only-token")
    with (
        patch("media_app.is_ffmpeg_available", return_value=True),
        patch("media_app.run_ffmpeg_stream") as run,
    ):
        r = TestClient(media_app.app).post(
            "/v1/split", content=b"sample", headers={"X-Media-Token": "synthetic-local-only-token"}
        )
    assert r.status_code == 503
    run.assert_not_called()
