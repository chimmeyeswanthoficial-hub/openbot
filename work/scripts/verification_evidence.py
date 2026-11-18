"""Strict parsing of completed pytest JUnit artifacts, not proof of execution alone.

Pair the unchanged XML with real runner logs and a source pin. A checksum cannot
make a collection-derived or otherwise fabricated report into execution evidence.
"""
from __future__ import annotations

import hashlib
import math
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

MAX_XML_BYTES = 16_000_000


def read_junit(path: Path) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= MAX_XML_BYTES:
        raise ValueError('expected bounded regular completed JUnit XML')
    data = path.read_bytes()
    if b'<!DOCTYPE' in data or b'<!ENTITY' in data:
        raise ValueError('DTD/entity declarations are not evidence')
    root = ET.fromstring(data)
    suites = [root] if root.tag == 'testsuite' else list(root) if root.tag == 'testsuites' else []
    if not suites or any(s.tag != 'testsuite' or s.find('testsuite') is not None for s in suites):
        raise ValueError('expected flat pytest testsuites')
    counts = {'passed': 0, 'skipped': 0, 'failed': 0, 'collected': 0}
    names, timestamps = set(), []
    for suite in suites:
        cases = suite.findall('testcase')
        failure = error = skipped = 0
        for case in cases:
            identity = (case.get('classname', ''), case.get('name', ''))
            if not identity[1] or identity in names:
                raise ValueError('missing/duplicate testcase identity')
            names.add(identity)
            flags = [case.find(k) is not None for k in ('failure', 'error', 'skipped')]
            if sum(flags) > 1:
                raise ValueError('contradictory testcase outcomes')
            failure += flags[0]
            error += flags[1]
            skipped += flags[2]
        expected = {'tests': len(cases), 'failures': failure, 'errors': error, 'skipped': skipped}
        for name, value in expected.items():
            raw = suite.get(name, '')
            if not raw.isdecimal() or int(raw) != value:
                raise ValueError('suite header differs from actual testcase outcomes')
        timestamp = suite.get('timestamp', '')
        try:
            clock = datetime.fromisoformat(timestamp)
            duration = float(suite.get('time', '0'))
        except (ValueError, TypeError) as exc:
            raise ValueError('invalid runner timestamp/time') from exc
        if clock.tzinfo is None or not math.isfinite(duration) or duration < 0:
            raise ValueError('missing timezone or invalid suite duration')
        timestamps.append(timestamp)
        counts['collected'] += len(cases)
        counts['skipped'] += skipped
        counts['failed'] += failure + error
    if not counts['collected']:
        raise ValueError('empty run; no measurement recorded')
    counts['passed'] = counts['collected'] - counts['skipped'] - counts['failed']
    return {'python': counts, 'runner_timestamp': timestamps[0],
            'measurement_date': timestamps[0][:10], 'junit_sha256': hashlib.sha256(data).hexdigest()}
