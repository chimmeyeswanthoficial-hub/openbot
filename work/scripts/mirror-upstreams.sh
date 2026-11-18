#!/usr/bin/env bash
# Historical name; this helper is now a READ-ONLY local provenance check.
# No clone/init/reset/commit/create/push modes. Missing history is not a data leak.
# Recover a donor's exact recorded pin in a separate reviewed working copy; never attach arbitrary
# upstream HEAD history to installed bytes, and never reset the existing donor tree.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$#" -gt 1 ] || { [ "$#" -eq 1 ] && [ "$1" != "--check" ]; }; then
  echo "usage: scripts/mirror-upstreams.sh [--check] (read-only; init/push unsupported)" >&2
  exit 2
fi
"${PYTHON:-python3}" -B - <<'PY'
from pathlib import Path
import hashlib
import json
import subprocess

root = Path.cwd()
catalogue = root / "audit/donor-consolidation.json"
try:
    data = json.loads(catalogue.read_text()) if catalogue.is_file() else {}
    donors = data.get("donors", {}) if isinstance(data, dict) else {}
    if not isinstance(donors, dict):
        donors = {}
except (OSError, ValueError):
    print("Donor catalogue: UNVERIFIED (unreadable); no sources changed")
    donors = {}
for name in ("OpenBot", "OpenDots", "rakazo"):
    path = root / "repos" / name
    archived = donors.get(name) if name in {"OpenDots", "rakazo"} else None
    if isinstance(archived, dict):
        rel = f"archive/donor-sources/{name}.tar.xz"
        archive = root / rel
        verified = False
        if (archived.get("archive") == rel and archive.is_file()
                and not any(p.is_symlink() for p in (archive, *archive.parents))):
            with archive.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            verified = actual == archived.get("archive_sha256")
        status = "SHA-256 matches catalogue" if verified else "UNVERIFIED (missing/changed archive or invalid reference)"
        print(f"{name}: archived source; {status}; {rel}; not an upstream commit verification")
        continue
    if not path.is_dir():
        print(f"{name}: not installed")
        continue
    if not (path / ".git").exists():
        print(f"{name}: no git history (vendored tree); see .openbot/state/upstream.json")
        continue
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        print(f"{name}: git unavailable; revision UNVERIFIED")
        continue
    if result.returncode:
        print(f"{name}: revision UNVERIFIED (invalid or unreadable Git metadata)")
    else:
        print(f"{name}: HEAD {result.stdout.strip()} (not a pin/cleanliness verification)")
print("Report only: no network calls, no files or remotes changed, nothing pushed.")
PY
