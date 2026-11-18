"""Evidence must come from execution, never a collection-derived success prediction.

The XML strings below are explicitly synthetic UNIT fixtures, not measured receipts.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import generate_full_junit as generator
import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_script(name):
    spec = importlib.util.spec_from_file_location('fixture_' + name, ROOT / 'scripts' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def collected_fixture():
    return '\n'.join([f'services/example/tests/test_fake.py::test_unit_{i}' for i in range(586)] + [
        'services/sentinel/tests/test_repository_pg.py::test_a',
        'services/sentinel/tests/test_repository_pg.py::test_b',
    ])


UNIT_XML = '''<testsuites><testsuite name="unit-fixture" tests="3" failures="1" errors="0" skipped="1" time="0.1" timestamp="2025-01-01T00:00:00+00:00"><testcase classname="unit" name="pass"/><testcase classname="unit" name="fail"><failure message="intentional UNIT fixture"/></testcase><testcase classname="unit" name="skip"><skipped/></testcase></testsuite></testsuites>'''


def runner_fixture(monkeypatch, calls):
    def run(command, **kwargs):
        calls.append(command)
        output = next((arg.split('=', 1)[1] for arg in command if arg.startswith('--junitxml=')), None)
        if output is not None:
            Path(output).write_text(UNIT_XML)
        return subprocess.CompletedProcess(command, 1, stdout=collected_fixture(), stderr='unit fixture')
    monkeypatch.setattr(generator.subprocess, 'run', run)


def test_generator_executes_pytest_and_preserves_real_failure_xml(tmp_path, monkeypatch):
    calls = []
    runner_fixture(monkeypatch, calls)
    output = tmp_path / 'actual.xml'
    generator.generate(output)
    assert '--collect-only' not in calls[0], 'collection cannot be reported as execution'
    assert any(arg.startswith('--junitxml=') for arg in calls[0])
    assert '<failure ' in output.read_text(), 'must never convert a failed execution into a pass'
    assert output.read_text() == UNIT_XML, 'do not reconstruct or invent testcase times/outcomes'


def test_generator_does_not_overwrite_existing_evidence(tmp_path, monkeypatch):
    runner_fixture(monkeypatch, [])
    output = tmp_path / 'preserve.xml'
    output.write_text('original evidence')
    with pytest.raises(FileExistsError):
        generator.generate(output)
    assert output.read_text() == 'original evidence'


@pytest.mark.parametrize('xml', [
    '<testsuites><testsuite tests="2" failures="0" errors="0" skipped="0"><testcase classname="x" name="a"/></testsuite></testsuites>',
    '<testsuites><testsuite tests="2" failures="0" errors="0" skipped="0"><testcase classname="x" name="a"/><testcase classname="x" name="a"/></testsuite></testsuites>',
])
def test_record_refuses_inconsistent_or_duplicate_case_evidence(tmp_path, monkeypatch, xml):
    recorder = load_script('record-verification')
    monkeypatch.setattr(recorder, 'ROOT', tmp_path)
    for name in ('README.md', 'PROJECT_STATE.md', 'CHANGELOG.md'):
        (tmp_path / name).write_text('Current Python: `pass=1, skip=0, fail=0, collected=1`\n')
    evidence = tmp_path / 'bad.xml'
    evidence.write_text(xml)
    with pytest.raises(ValueError):
        recorder.record(evidence)
    assert not (tmp_path / 'audit/verification-current.json').exists()


def test_manifest_refuses_receipt_hash_not_matching_designated_xml(tmp_path, monkeypatch):
    publisher = load_script('create_evidence_manifest')
    monkeypatch.setattr(publisher, 'ROOT', tmp_path)
    evidence = tmp_path / 'audit/evidence-ag0-c02'
    evidence.mkdir(parents=True)
    monkeypatch.setattr(publisher, 'EVIDENCE', evidence)
    (evidence / 'full-python.xml').write_text(UNIT_XML)
    (tmp_path / 'audit/verification-current.json').write_text(json.dumps({
        'runner_timestamp': 'unit-fixture-not-a-measurement',
        'junit_artifact': 'audit/evidence-ag0-c02/full-python.xml',
        'junit_sha256': 'not-the-artifact-digest',
        'python': {'passed': 1, 'failed': 1, 'skipped': 1, 'collected': 3},
    }))
    with pytest.raises(ValueError):
        publisher.create_manifest()
    assert not (evidence / 'manifest.json').exists()


def test_generator_refuses_a_competing_file_created_after_initial_check(tmp_path, monkeypatch):
    runner_fixture(monkeypatch, [])
    output = tmp_path / 'race.xml'
    original_mkdir = Path.mkdir
    def competing_mkdir(path, *args, **kwargs):
        original_mkdir(path, *args, **kwargs)
        output.write_text('concurrent original evidence')
    monkeypatch.setattr(Path, 'mkdir', competing_mkdir)
    with pytest.raises(FileExistsError):
        generator.generate(output)
    assert output.read_text() == 'concurrent original evidence'


def test_generator_cli_propagates_pytest_failure(tmp_path, monkeypatch):
    runner_fixture(monkeypatch, [])
    monkeypatch.setattr(generator.sys, 'argv', ['generate_full_junit.py', '--output', str(tmp_path / 'failed.xml')])
    assert generator.main() == 1


def test_recorder_refuses_the_original_headerless_unit_shape(tmp_path):
    from verification_evidence import read_junit

    output = tmp_path / 'incomplete.xml'
    output.write_text('<testsuites><testsuite timestamp="2030-02-03T10:00:00+00:00"><testcase name="real" /></testsuite></testsuites>')
    with pytest.raises(ValueError):
        read_junit(output)
