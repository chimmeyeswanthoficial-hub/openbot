"""Mandatory Linux controls: fresh missing-import simulations + actual Linux flock.

Refusal tests guard ordering before pin/native/state/DB access. Simulated Windows
and macOS are NOT native platform certification; no runtime fallback is added.
"""
from __future__ import annotations

import importlib
import json
import os
import sys

import hq_readiness as hq
import isolation
import pytest
from local_executor import Authority
from namespace_executor import NamespaceExecutor

REQUEST_ID = "90a22229-e876-4937-b683-265b3bdb0819"


@pytest.fixture()
def company(tmp_path):
    root = tmp_path / "company"
    (root / ".openbot/state").mkdir(parents=True)
    (root / "audit").mkdir()
    (root / "company").mkdir()
    (root / ".openbot/state/budget.json").write_text(json.dumps({
        "company_day_cap_usd": 0, "spent_today_usd": 0, "paused": True,
    }))
    (root / ".openbot/state/active_ventures.yaml").write_text(
        "ventures:\n  - slug: media-api\n    paused: true\n")
    (root / "audit/verification-current.json").write_text(json.dumps({
        "python": {"passed": 251, "skipped": 2, "failed": 0, "collected": 253},
        "scope": "historical UNIT fixture, not a new measurement",
    }))
    (root / "company/hq-local-policy.json").write_text(json.dumps({
        "version": 1, "enabled": True, "egress_mode": "deny_all", "auto_spend_usd": 0,
        "allowed_actions": ["company.readiness"],
    }))
    return root


def _forbidden(*_args, **_kwargs):
    pytest.fail("mandatory-control refusal must precede this operation")


def _no_state_access(monkeypatch):
    for name in ("_private_dir", "open_store", "read_evidence"):
        monkeypatch.setattr(hq, name, _forbidden)


def _no_pin_or_native_access(monkeypatch):
    monkeypatch.setattr(isolation, "load_lock", _forbidden)
    monkeypatch.setattr(isolation, "checked_binary", _forbidden)
    monkeypatch.setattr(isolation.os, "memfd_create", _forbidden, raising=False)


def _fresh_missing_fcntl(name, monkeypatch):
    original = sys.modules.pop(name, None)
    monkeypatch.setitem(sys.modules, "fcntl", None)
    try:
        module = importlib.import_module(name)
        assert module is not original and module.fcntl is None
        return module
    finally:
        sys.modules.pop(name, None)
        if original is not None:
            sys.modules[name] = original


def test_hq_readiness_importable_when_fcntl_missing(monkeypatch):
    module = _fresh_missing_fcntl("hq_readiness", monkeypatch)
    assert callable(module.run_request)


def test_hq_readiness_refuses_when_fcntl_missing(company, tmp_path, monkeypatch):
    state = tmp_path / "missing-fcntl-state"
    _no_state_access(monkeypatch)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(hq, "fcntl", None)
    assert hq.run_request({"request_id": REQUEST_ID, "action": "company.readiness"},
                          root=company, state_dir=state) == {
        "ok": False, "executed": False, "replayed": False, "code": "hq.platform_unavailable",
    }
    assert not state.exists()


def test_hq_readiness_refuses_on_non_linux(company, tmp_path, monkeypatch):
    _no_state_access(monkeypatch)
    for simulated in ("win32", "darwin"):
        state = tmp_path / simulated
        monkeypatch.setattr(sys, "platform", simulated)
        assert hq.run_request({"request_id": REQUEST_ID, "action": "company.readiness"},
                              root=company, state_dir=state) == {
            "ok": False, "executed": False, "replayed": False, "code": "hq.platform_unavailable",
        }
        assert not state.exists()


@pytest.mark.skipif(not sys.platform.startswith("linux") or hq.fcntl is None,
                    reason="actual independent-descriptor flock requires Linux fcntl")
def test_hq_readiness_requires_flock_on_linux(company, tmp_path, monkeypatch):
    import fcntl

    state = tmp_path / "busy-state"
    state.mkdir()
    monkeypatch.setattr(hq, "open_store", _forbidden)
    fd = os.open(state / "jobs.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert hq.run_request({"request_id": REQUEST_ID, "action": "company.readiness"},
                              root=company, state_dir=state) == {
            "ok": False, "executed": False, "code": "hq.busy",
        }
        assert not (state / "sentinel.sqlite3").exists()
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def test_isolation_importable_when_fcntl_missing(monkeypatch):
    module = _fresh_missing_fcntl("isolation", monkeypatch)
    assert callable(module.load_binary) and callable(module.run_fixed)


def test_isolation_load_binary_refuses_without_fcntl(monkeypatch):
    _no_pin_or_native_access(monkeypatch)
    monkeypatch.setattr(isolation, "fcntl", None)
    with pytest.raises(ValueError, match="mandatory Linux fcntl sealing unavailable; never fall back"):
        isolation.load_binary()


def test_isolation_run_fixed_refuses_without_fcntl(monkeypatch):
    _no_pin_or_native_access(monkeypatch)
    monkeypatch.setattr(isolation, "fcntl", None)
    with pytest.raises(ValueError, match="mandatory Linux fcntl sealing unavailable; never fall back"):
        isolation.run_fixed("wordcount", {"request_id": REQUEST_ID, "text": "hello", "delay_ms": 0})


def test_namespace_executor_refuses_before_state_creation_without_fcntl(tmp_path, monkeypatch):
    _no_pin_or_native_access(monkeypatch)
    state = tmp_path / "refused-namespace-executor-state"
    monkeypatch.setattr(isolation, "fcntl", None)
    authority = Authority("agent:fixture", "isolation-fixture", "person", "synthetic-human-fixture")
    with pytest.raises(ValueError, match="mandatory Linux fcntl sealing unavailable; never fall back"):
        NamespaceExecutor(state, authority, experimental=True)
    assert not state.exists()
