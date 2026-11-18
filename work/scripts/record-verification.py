#!/usr/bin/env python3
"""Record completed pytest XML and synchronize explicitly CURRENT outcome rows.

XML consistency/hash checks are not execution authentication. Preserve the real
runner logs, source identity and designated artifact as well as this receipt.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re

from verification_evidence import read_junit

ROOT = pathlib.Path(__file__).resolve().parent.parent


def record(junit: pathlib.Path) -> dict:
    result = read_junit(junit)
    outcomes = result['python']
    try:
        designated = junit.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        designated = str(junit.absolute())
    receipt = {
        'scope': 'local Python source tests; outcome snapshot, not a production certification',
        **result, 'junit_artifact': designated,
        'limits': ['PostgreSQL tests skipped unless explicitly opted into a disposable test database',
                   'No real Bot/model/payment provider/deploy/long-duration pilot exercised',
                   'XML hash/consistency alone is not proof of execution; retain runner logs/source pin'],
    }
    row = (f"Current Python: `pass={outcomes['passed']}, skip={outcomes['skipped']}, "
           f"fail={outcomes['failed']}, collected={outcomes['collected']}`")
    pattern = r'Current Python: `pass=\d+, skip=\d+, fail=\d+, collected=\d+`'
    documents = {}
    for name in ('README.md', 'PROJECT_STATE.md', 'CHANGELOG.md'):
        path = ROOT / name
        text = path.read_text(encoding='utf-8')
        if len(re.findall(pattern, text)) != 1:
            raise ValueError(f'{name} must have exactly one current outcome row')
        documents[path] = re.sub(pattern, row, text)
    dest = ROOT / 'audit/verification-current.json'
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    for path, text in documents.items():
        path.write_text(text, encoding='utf-8')
    print(row)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('junit', type=pathlib.Path)
    record(parser.parse_args().junit)
