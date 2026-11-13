"""T7 Deploy Pipeline — unit tests for scripts/deploy.py.

Tests verify:
1. deploy() records entry in deployments.json
2. deploy() updates current_sha and previous_sha correctly
3. rollback() reverts current_sha to previous_sha
4. rollback() fails gracefully when no previous_sha exists
5. sequential deploy + rollback round-trip
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

# Make scripts/ importable
_SCRIPTS = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_SCRIPTS))

import deploy as deploy_mod  # noqa: E402


@pytest.fixture()
def state_file(tmp_path, monkeypatch):
    """Redirect STATE_FILE to a temp location so tests don't touch .openbot/."""
    sf = tmp_path / "deployments.json"
    monkeypatch.setattr(deploy_mod, "STATE_FILE", sf)
    return sf


# ---------------------------------------------------------------------------
# T7-1: deploy records entry in history
# ---------------------------------------------------------------------------
def test_deploy_records_history_entry(state_file):
    result = deploy_mod.deploy("v0.3.0", migration_id="mig_001")
    assert result is True
    data = json.loads(state_file.read_text())
    assert len(data["history"]) == 1
    entry = data["history"][0]
    assert entry["sha"] == "v0.3.0"
    assert entry["migration_id"] == "mig_001"
    assert entry["status"] == "success"


# ---------------------------------------------------------------------------
# T7-2: deploy updates current_sha and previous_sha
# ---------------------------------------------------------------------------
def test_deploy_updates_current_and_previous_sha(state_file):
    deploy_mod.deploy("v0.3.0")
    deploy_mod.deploy("v0.3.1")
    data = json.loads(state_file.read_text())
    assert data["current_sha"] == "v0.3.1"
    assert data["previous_sha"] == "v0.3.0"


# ---------------------------------------------------------------------------
# T7-3: rollback reverts current_sha to previous_sha
# ---------------------------------------------------------------------------
def test_rollback_reverts_current_sha(state_file):
    deploy_mod.deploy("v0.3.0")
    deploy_mod.deploy("v0.3.1")
    result = deploy_mod.rollback()
    assert result is True
    data = json.loads(state_file.read_text())
    assert data["current_sha"] == "v0.3.0"


# ---------------------------------------------------------------------------
# T7-4: rollback fails without a previous_sha
# ---------------------------------------------------------------------------
def test_rollback_fails_without_previous_sha(state_file):
    # Only a single deploy — previous_sha is None (starting default)
    deploy_mod.deploy("v0.3.0")
    # First deploy uses default state which has previous_sha=None
    # We need a fresh state_file with no previous deploy
    state_file.write_text(
        json.dumps({"current_sha": "v0.3.0", "previous_sha": None, "history": []}),
        encoding="utf-8",
    )
    result = deploy_mod.rollback()
    assert result is False


# ---------------------------------------------------------------------------
# T7-5: deploy + rollback round-trip leaves a rollback row in history
# ---------------------------------------------------------------------------
def test_deploy_rollback_roundtrip_records_rollback_row(state_file):
    deploy_mod.deploy("v0.3.0")
    deploy_mod.deploy("v0.3.1")
    deploy_mod.rollback()
    data = json.loads(state_file.read_text())
    # Should have 3 history entries: deploy v0.3.0, deploy v0.3.1, rollback
    assert len(data["history"]) == 3
    last = data["history"][-1]
    assert last["status"] == "rolled_back"
    assert last["sha"] == "v0.3.0"

