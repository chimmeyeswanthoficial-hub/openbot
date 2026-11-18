"""Bookkeeping is not deployment and must not produce an implicit success claim."""
from __future__ import annotations

import sys

import deploy
import pytest


def test_deploy_cli_refuses_without_explicit_record_only(tmp_path, monkeypatch):
    state = tmp_path / "records.json"
    monkeypatch.setattr(deploy, "STATE_FILE", state)
    monkeypatch.setattr(sys, "argv", ["deploy.py", "--sha", "example-image"])
    with pytest.raises(SystemExit) as exc:
        deploy.main()
    assert exc.value.code != 0
    assert not state.exists()
