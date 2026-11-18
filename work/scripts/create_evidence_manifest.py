"""Bind an evidence manifest to the receipt's actual designated completed XML.

Integrity/consistency is checked, but cannot authenticate arbitrary supplied XML.
Real subprocess logs and tested source identity must be independently retained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import stat

from verification_evidence import read_junit

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / 'audit/evidence-ag0-c02'


def create_manifest(evidence: pathlib.Path | None = None, *, base_commit: str | None = None) -> dict:
    evidence = pathlib.Path(evidence or EVIDENCE).absolute()
    if base_commit is not None and not re.fullmatch('[a-f0-9]{40}', base_commit):
        raise ValueError('base commit must be a full pin, not a guessed current HEAD')
    receipt_bytes = (ROOT / 'audit/verification-current.json').read_bytes()
    receipt = json.loads(receipt_bytes)
    artifact = pathlib.Path(receipt['junit_artifact'])
    artifact = artifact if artifact.is_absolute() else ROOT / artifact
    if artifact.is_symlink() or artifact.resolve().parent != evidence.resolve():
        raise ValueError('designated artifact must be in the selected evidence directory')
    measured = read_junit(artifact)
    if any(receipt.get(key) != measured[key] for key in ('python', 'junit_sha256', 'runner_timestamp', 'measurement_date')):
        raise ValueError('receipt does not bind to designated XML outcomes/hash/timestamp')
    files = []
    for path in sorted(evidence.iterdir()):
        if path.name == 'manifest.json':
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError('only regular evidence files may be manifested')
        data = path.read_bytes()
        files.append({'path': path.name, 'bytes': len(data),
                      'sha256': hashlib.sha256(data).hexdigest(),
                      'mode': stat.S_IMODE(path.stat().st_mode)})
    manifest = {
        'schema': 2, 'scope': 'verified artifact binding; pair with real runner logs/source inventory',
        'base_commit': base_commit, 'receipt_artifact': 'audit/verification-current.json',
        'receipt_sha256': hashlib.sha256(receipt_bytes).hexdigest(), 'python_outcomes': measured['python'],
        'runner_timestamp': measured['runner_timestamp'],
        'designated_junit': artifact.name, 'designated_junit_sha256': measured['junit_sha256'],
        'files': files,
    }
    (evidence / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=pathlib.Path, default=EVIDENCE)
    parser.add_argument('--base-commit')
    args = parser.parse_args()
    print(json.dumps(create_manifest(args.evidence_dir, base_commit=args.base_commit), indent=2))
