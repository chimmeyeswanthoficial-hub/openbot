#!/usr/bin/env python3
"""Record-only deployment-plan simulator, NOT a deployment/rollback executor.

The incoming Antigravity code only changed JSON. Preserve that useful bookkeeping
without claiming it verifies migrations, launches an image or changes a running service.
The CLI refuses unless --record-only is explicit. Actual T7 remains unimplemented.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / ".openbot" / "state" / "deployment-records.json"


def load_deployments() -> dict:
    if not STATE_FILE.exists():
        return {"current_sha": None, "previous_sha": None, "record_only": True, "history": []}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_deployments(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def deploy(target_sha: str, migration_id: str | None = None) -> bool:
    """Legacy name: record a PROPOSED target. Never deploys or validates a migration."""
    state = load_deployments()
    previous = state.get("current_sha")
    entry = {"sha": target_sha, "previous_sha": previous, "migration_id": migration_id,
             "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "status": "recorded_only", "migration_verified": False}
    state.update(current_sha=target_sha, previous_sha=previous, record_only=True)
    state.setdefault("history", []).append(entry)
    save_deployments(state)
    print(f"RECORD ONLY: proposed {target_sha}; no migration, image or service was changed.")
    return True


def rollback() -> bool:
    """Record a proposed reversal; no infrastructure or data restoration occurs."""
    state = load_deployments()
    previous = state.get("previous_sha")
    if not previous:
        print("No previous proposed target to record.", file=sys.stderr)
        return False
    current = state.get("current_sha")
    state.update(current_sha=previous, previous_sha=current, record_only=True)
    state.setdefault("history", []).append({
        "sha": previous, "previous_sha": current, "status": "rollback_recorded_only",
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "migration_verified": False,
    })
    save_deployments(state)
    print(f"RECORD ONLY: proposed reversal to {previous}; no deployment was rolled back.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Record-only deployment plan simulator; no infrastructure execution")
    parser.add_argument("--record-only", action="store_true", help="Acknowledge JSON bookkeeping only")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sha", help="Proposed target image digest or label")
    group.add_argument("--rollback", action="store_true", help="Record a proposed reversal")
    parser.add_argument("--migration", help="Unverified migration label")
    args = parser.parse_args()
    if not args.record_only:
        parser.error("real deployment is not implemented; --record-only is required for bookkeeping")
    success = rollback() if args.rollback else deploy(args.sha, args.migration)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
