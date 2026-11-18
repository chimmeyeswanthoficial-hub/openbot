"""Standard-library tests for source identity, clean export and new-only fixtures."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, TOOLS / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERIFY = load("test_source_verify", "verify-source.py")
EXPORT = load("test_source_export", "export-source.py")
PREPARE = load("test_source_prepare", "prepare-test-state.py")


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "workspace"
        self.root.mkdir()
        p = self.root / "README.md"
        p.write_text("Original source\n")
        p.chmod(0o644)
        self.manifest = {
            "schema": "openbot.workspace-source/1",
            "files": {
                "README.md": {
                    "bytes": p.stat().st_size,
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    "mode": 0o644,
                }
            },
        }
        (self.root / "SOURCE_MANIFEST.json").write_text(json.dumps(self.manifest))

    def package(self, target, *, after_check=None):
        original = VERIFY.check

        def check():
            result = original(self.root)
            if after_check:
                after_check()
            return result

        with (
            patch.object(EXPORT, "ROOT", self.root),
            patch.object(EXPORT, "VERIFY", VERIFY),
            patch.object(VERIFY, "check", check),
        ):
            return EXPORT.package(target)

    def test_readonly_manifest_check_and_changed_source_refusal(self):
        self.assertEqual(VERIFY.check(self.root)["verified_files"], 1)
        (self.root / "README.md").write_text("Changed")
        with self.assertRaises(ValueError):
            VERIFY.check(self.root)

    def test_present_manifest_metadata_digest_must_match_canonical_file_map(self):
        encoded = json.dumps(self.manifest["files"], sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        self.manifest["files_metadata_sha256"] = hashlib.sha256(encoded).hexdigest()
        path = self.root / "SOURCE_MANIFEST.json"
        path.write_text(json.dumps(self.manifest), encoding="utf-8")
        self.assertEqual(VERIFY.check(self.root)["verified_files"], 1)
        self.manifest["files_metadata_sha256"] = "0" * 64
        path.write_text(json.dumps(self.manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "metadata digest"):
            VERIFY.check(self.root)

    def test_manifest_archive_mode_is_canonical_independent_of_local_mode(self):
        path = self.root / "SOURCE_MANIFEST.json"
        one, two = self.base / "mode-one.zip", self.base / "mode-two.zip"
        path.chmod(0o644)
        self.package(one)
        path.chmod(0o600)
        self.package(two)
        self.assertEqual(one.read_bytes(), two.read_bytes())
        with zipfile.ZipFile(one) as archive:
            self.assertEqual(
                (archive.getinfo("OpenBot-Workspace/SOURCE_MANIFEST.json").external_attr >> 16)
                & 0o777,
                0o644,
            )

    def test_manifest_cannot_reference_parent_or_absolute_paths(self):
        for name in ["../outside", "/etc/passwd", "x/../../outside", "a\\b", "a//b"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                VERIFY.safe_file(self.root, name)

    def test_links_are_not_accepted_as_source(self):
        (self.root / "linked.md").symlink_to(self.root / "README.md")
        with self.assertRaises(ValueError):
            VERIFY.safe_file(self.root, "linked.md")
        try:
            os.link(self.root / "README.md", self.root / "hard.md")
            with self.assertRaises(ValueError):
                VERIFY.safe_file(self.root, "hard.md")
        except PermissionError:
            (self.root / "hard.md").write_text("hard link simulation")
            from unittest.mock import patch

            orig_stat = Path.stat

            def fake_stat(self, *args, **kwargs):
                res = orig_stat(self, *args, **kwargs)
                if self.name == "hard.md":
                    return os.stat_result(
                        (
                            res.st_mode,
                            res.st_ino,
                            res.st_dev,
                            2,
                            res.st_uid,
                            res.st_gid,
                            res.st_size,
                            res.st_atime,
                            res.st_mtime,
                            res.st_ctime,
                        )
                    )
                return res

            with patch.object(Path, "stat", fake_stat), self.assertRaises(ValueError):
                VERIFY.safe_file(self.root, "hard.md")

    def test_manifest_only_export_excludes_unlisted_private_state(self):
        (self.root / ".env").write_text("PRIVATE_FIXTURE=not-source")
        state = self.root / ".openbot/state"
        state.mkdir(parents=True)
        (state / "budget.json").write_text('{"private":true}')
        target = self.base / "source.zip"
        self.package(target)
        with zipfile.ZipFile(target) as archive:
            self.assertEqual(
                set(archive.namelist()),
                {"OpenBot-Workspace/README.md", "OpenBot-Workspace/SOURCE_MANIFEST.json"},
            )
        self.assertTrue((self.root / ".env").exists())
        with self.assertRaises(ValueError):
            VERIFY.check(self.root, strict=True)

    def test_export_is_reproducible_and_never_overwrites(self):
        one = self.base / "one.zip"
        two = self.base / "two.zip"
        self.package(one)
        self.package(two)
        self.assertEqual(one.read_bytes(), two.read_bytes())
        original = one.read_bytes()
        with self.assertRaises(FileExistsError):
            self.package(one)
        self.assertEqual(one.read_bytes(), original)

    def test_mutation_during_export_is_not_reported_as_success(self):
        with self.assertRaises(ValueError):
            self.package(
                self.base / "changed.zip",
                after_check=lambda: (self.root / "README.md").write_text("Changed after check"),
            )

    def test_synthetic_state_is_new_only_private_and_not_an_operating_grant(self):
        (self.root / "pyproject.toml").write_text('[project]\nname="local-test"\n')
        p = self.root / ".openbot/routines/scout-daily.md"
        p.parent.mkdir(parents=True)
        p.write_text("Test marker")
        result = PREPARE.prepare(self.root)
        self.assertFalse(result["services_started"])
        self.assertFalse(result["external_actions_enabled"])
        state = self.root / ".openbot/state"
        if os.name == "posix":
            self.assertEqual(state.stat().st_mode & 0o777, 0o700)
        budget = json.loads((state / "budget.json").read_bytes())
        self.assertTrue(budget["fixture_only"])
        self.assertEqual(budget["auto_spend_usd"], 0)
        before = {p.name: p.read_bytes() for p in state.iterdir()}
        with self.assertRaises(ValueError):
            PREPARE.prepare(self.root)
        self.assertEqual(before, {p.name: p.read_bytes() for p in state.iterdir()})

    def test_fixture_preparation_refuses_linked_or_unknown_roots(self):
        with self.assertRaises(ValueError):
            PREPARE.prepare(self.root)
        linked = self.base / "linked"
        linked.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            PREPARE.prepare(linked)


if __name__ == "__main__":
    unittest.main()
