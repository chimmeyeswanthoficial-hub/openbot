"""Reviewed fixed namespace QA worker; only bundled source literals may execute."""

import ctypes
import doctest
import hashlib
import importlib.util
import io
import json
import os
import platform
import resource
import signal
import sys
import time
import types
import unittest
import xml.etree.ElementTree as ET


def main():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != 1:
        raise ValueError("mandatory namespace parent guard")
    limits = {"CPU": 2, "AS": 128 * 1024 * 1024, "FSIZE": 0, "NOFILE": 16, "CORE": 0, "NPROC": 1}
    for name, value in limits.items():
        resource.setrlimit(getattr(resource, "RLIMIT_" + name), (value, value))
    status = {}
    with open("/proc/self/status") as stream:
        for line in stream:
            key, _, value = line.partition(":")
            if key in {"CapEff", "NoNewPrivs", "Seccomp"}:
                status[key] = value.strip()
    controls = {
        "status": status,
        "rlimits": {
            name: list(resource.getrlimit(getattr(resource, "RLIMIT_" + name))) for name in limits
        },
        "namespaces": {
            name: os.readlink("/proc/self/ns/" + name)
            for name in ("net", "mnt", "pid", "user", "uts", "ipc")
        },
        "host_environment_absent": set(os.environ)
        <= {"PATH", "LANG", "LC_CTYPE", "PWD", "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE"},
    }
    payload = sys.stdin.buffer.read(2049)
    if len(payload) > 2048:
        raise ValueError("fixed input bound")
    body = json.loads(payload)
    if not isinstance(body, dict) or set(body) != {"fixture"}:
        raise ValueError("fixed owned fixture only")
    spec = importlib.util.spec_from_file_location("owned_catalog", "/fixtures.py")
    catalog = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(catalog)
    if body["fixture"] not in catalog.FIXTURES:
        raise ValueError("unknown reviewed sample")
    source = catalog.FIXTURES[body["fixture"]]
    module = types.ModuleType("owned_example")
    module.__file__ = "/owned_example.py"
    # Source is a reviewed literal from the read-only mounted catalog, NEVER input.
    exec(compile(source, module.__file__, "exec"), module.__dict__)

    class OwnedTests(unittest.TestCase):
        def test_discount(self):
            self.assertEqual(module.discounted_total(1250, 2, 10), 2250)

        def test_free(self):
            self.assertEqual(module.discounted_total(999, 1, 100), 0)

        def test_no_discount(self):
            self.assertEqual(module.discounted_total(100, 3), 300)

        def test_reject_negative(self):
            with self.assertRaises(ValueError):
                module.discounted_total(-1, 1)

        def test_reject_float(self):
            with self.assertRaises(TypeError):
                module.discounted_total(1.5, 1)

        def test_reject_bool(self):
            with self.assertRaises(TypeError):
                module.discounted_total(True, 1)

    cases = []

    class Result(unittest.TextTestResult):
        def startTest(self, test):
            self.started = time.monotonic()
            super().startTest(test)

        def addSuccess(self, test):
            super().addSuccess(test)
            cases.append((test, "passed", "", time.monotonic() - self.started))

        def addFailure(self, test, error):
            super().addFailure(test, error)
            cases.append(
                (
                    test,
                    "failure",
                    self._exc_info_to_string(error, test),
                    time.monotonic() - self.started,
                )
            )

        def addError(self, test, error):
            super().addError(test, error)
            cases.append(
                (
                    test,
                    "error",
                    self._exc_info_to_string(error, test),
                    time.monotonic() - self.started,
                )
            )

    suite = unittest.TestSuite(
        [unittest.defaultTestLoader.loadTestsFromTestCase(OwnedTests), doctest.DocTestSuite(module)]
    )
    captured = io.StringIO()
    result = unittest.TextTestRunner(stream=captured, verbosity=2, resultclass=Result).run(suite)
    xml = ET.Element(
        "testsuite",
        tests=str(result.testsRun),
        failures=str(len(result.failures)),
        errors=str(len(result.errors)),
        skipped="0",
    )
    observed = []
    for test, outcome, trace, elapsed in cases:
        name = (
            "OwnedTests." + test._testMethodName
            if isinstance(test, OwnedTests)
            else "owned_example"
        )
        node = ET.SubElement(
            xml, "testcase", classname="owned_qa", name=name, time=str(round(elapsed, 6))
        )
        if outcome != "passed":
            ET.SubElement(node, outcome, message="actual assertion/example failure").text = trace
        observed.append({"case": name, "outcome": outcome, "trace": trace})
    if sorted(item["case"] for item in observed) != sorted(catalog.CASE_NAMES):
        raise ValueError("required sample assertions were not all observed")
    output = {
        "fixture": body["fixture"],
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "junit": ET.tostring(xml, encoding="unicode"),
        "runner_output": captured.getvalue(),
        "cases": observed,
        "environment": {
            "python": platform.python_version(),
            "platform": sys.platform,
            "network_profile": "unshared-deny-network",
            "program_scope": "bundled-owned-literals",
        },
        "exit_code": 0 if result.wasSuccessful() else 1,
        "doctest_executed": True,
        "controls": controls,
    }
    print(json.dumps(output, sort_keys=True))
    return output["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
