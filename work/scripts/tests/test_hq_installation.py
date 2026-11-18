"""Static boundary and portable-wrapper checks. Not a dependency/security attestation."""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HQ = ROOT / "apps/bot-hq"


def test_hq_default_is_compiled_provider_disabled_entry_not_upstream():
    package = json.loads((HQ / "server/package.json").read_text())
    assert package["scripts"]["start"] == "node dist/local-entry.js"
    assert "tsx" not in package.get("devDependencies", {})
    assert "throw new Error" in (HQ / "server/src/index.ts").read_text()
    assert not list((HQ / "scripts").glob("*.sh"))


def test_local_server_relative_import_closure_contains_no_provider_modules():
    pending = [HQ / "server/src/local-entry.ts"]
    visited = set()
    forbidden = {"engine.ts", "loop.ts", "routes.ts", "computer.ts", "box.ts", "voice.ts",
                 "mcp.ts", "orgo.ts", "composio.ts", "routines.ts", "triggers.ts", "proactive.ts"}
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        assert path.name not in forbidden
        source = path.read_text()
        assert not re.search(r"\bfetch\s*\(", source), path
        for target in re.findall(r"(?:from\s+|import\s*)['\"]([^'\"]+)['\"]", source):
            if target.startswith("."):
                child = (path.parent / target).resolve().with_suffix(".ts")
                assert child.is_relative_to(HQ.resolve() / "server/src")
                pending.append(child)
    assert {"db.ts", "store.ts", "auth.ts", "hub.ts"} <= {p.name for p in visited}


def test_installed_web_contains_no_excluded_donor_art_or_paths():
    assert not (HQ / "web/artwork").exists()
    assert not (HQ / "web/public/assets").exists()
    assert not (HQ / "web/src/avatar/shapes.gen.ts").exists()
    for path in (HQ / "web/src").rglob("*"):
        if path.suffix not in (".tsx", ".ts", ".css"):
            continue
        text = path.read_text()
        assert not any(token in text for token in ("/assets/", "shapes.gen", "<svg", "<path ")), path
    assert (HQ / "LICENSE").exists() and (HQ / "THIRD_PARTY_NOTICES.md").exists()


def test_deploy_shell_passes_explicit_record_only_and_refuses_without_it(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("deploy.sh", "deploy.py"):
        shutil.copy2(ROOT / "scripts" / name, scripts / name)
    refused = subprocess.run(["bash", str(scripts / "deploy.sh"), "--sha", "test-label"], capture_output=True, text=True, check=False)
    assert refused.returncode != 0
    state = tmp_path / ".openbot/state/deployment-records.json"
    assert not state.exists()
    recorded = subprocess.run(["bash", str(scripts / "deploy.sh"), "--record-only", "--sha", "test-label"], capture_output=True, text=True, check=False)
    assert recorded.returncode == 0 and "RECORD ONLY" in recorded.stdout
    assert json.loads(state.read_text())["record_only"] is True


def test_verification_recorder_derives_measurement_date_instead_of_hardcoding(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("verification_recorder", ROOT / "scripts/record-verification.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    for name in ("README.md", "PROJECT_STATE.md", "CHANGELOG.md"):
        (tmp_path / name).write_text("Current Python: `pass=1, skip=0, fail=0, collected=1`\n")
    junit = tmp_path / "result.xml"
    # Synthetic UNIT XML must still be structurally complete; it is not measured proof.
    junit.write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0" time="0.1" timestamp="2030-02-03T10:00:00+00:00"><testcase classname="unit" name="fixture" /></testsuite></testsuites>')
    receipt = module.record(junit)
    assert receipt["measurement_date"] == "2030-02-03"
    assert receipt["runner_timestamp"].startswith("2030-02-03")
