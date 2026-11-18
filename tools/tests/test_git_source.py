"""Synthetic local Git fixtures; no remotes, credentials, downloads or native launch."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "git_source_test_target", Path(__file__).resolve().parents[1] / "verify-git-source.py"
)
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class GitSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.hooks = Path(self.temp.name) / "empty-hooks"
        self.hooks.mkdir()
        self.git("init", "--quiet", "--initial-branch=main")
        (self.root / "README.md").write_bytes(b"Source fixture\n")
        self.files = {
            "README.md": {
                "bytes": 15,
                "sha256": hashlib.sha256(b"Source fixture\n").hexdigest(),
                "mode": 0o600,
            }
        }
        self.files["README.md"]["bytes"] = len(b"Source fixture\n")
        self.manifest = {"schema": "openbot.workspace-source/1", "files": self.files}

    def git(self, *args):
        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "-c",
                "user.name=Synthetic Git Source Test",
                "-c",
                "user.email=fixture@openbot.invalid",
                "-c",
                "commit.gpgSign=false",
                "-c",
                "core.autocrlf=false",
                "-c",
                "core.hooksPath=" + str(self.hooks),
                *args,
            ],
            env=VERIFY.git_environment(),
            capture_output=True,
            check=True,
        )
        return result.stdout

    def write_manifest(self):
        raw = json.dumps(self.files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.manifest["files_metadata_sha256"] = hashlib.sha256(raw).hexdigest()
        (self.root / "SOURCE_MANIFEST.json").write_bytes(
            json.dumps(self.manifest, sort_keys=True).encode("utf-8")
        )

    def commit(self, *, write_manifest=True):
        if write_manifest:
            self.write_manifest()
        self.git("add", "--all")
        self.git("commit", "--quiet", "--allow-empty", "-m", "Synthetic local fixture")
        return self.git("rev-parse", "HEAD").decode().strip()

    def test_complete_tree_and_private_mode_boundary_are_explicit(self):
        commit = self.commit()
        result = VERIFY.check(self.root)
        self.assertEqual(result["revision"], commit)
        self.assertEqual(result["verified_files"], 1)
        self.assertTrue(result["metadata_digest_verified"])
        self.assertTrue(result["git_executable_bits_verified"])
        self.assertFalse(result["private_filesystem_permissions_verified"])
        self.assertFalse(result["working_tree_verified"])
        self.assertFalse(result["signed_release"])

    def test_dirty_working_tree_does_not_masquerade_as_committed_content(self):
        commit = self.commit()
        (self.root / "README.md").write_bytes(b"Uncommitted different content")
        result = VERIFY.check(self.root)
        self.assertEqual(result["revision"], commit)
        self.assertFalse(result["working_tree_verified"])
        self.assertEqual((self.root / "README.md").read_bytes(), b"Uncommitted different content")

    def test_missing_committed_source_is_refused(self):
        self.commit()
        (self.root / "README.md").unlink()
        self.commit()
        with self.assertRaisesRegex(ValueError, "missing committed source"):
            VERIFY.check(self.root)

    def test_wrong_content_hash_is_refused(self):
        self.files["README.md"]["sha256"] = "0" * 64
        self.commit()
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            VERIFY.check(self.root)

    def test_stale_aggregate_digest_is_refused(self):
        self.write_manifest()
        self.manifest["files_metadata_sha256"] = "0" * 64
        (self.root / "SOURCE_MANIFEST.json").write_bytes(json.dumps(self.manifest).encode())
        self.commit(write_manifest=False)
        with self.assertRaisesRegex(ValueError, "metadata digest"):
            VERIFY.check(self.root)

    def test_unlisted_committed_file_is_refused_without_reading_its_value(self):
        (self.root / "extra.txt").write_bytes(b"Synthetic unlisted data")
        self.commit()
        with self.assertRaisesRegex(ValueError, "unlisted committed paths"):
            VERIFY.check(self.root)

    def test_gitlink_is_refused(self):
        commit = self.commit()
        self.git("update-index", "--add", "--cacheinfo", "160000," + commit + ",guest")
        self.git("commit", "--quiet", "-m", "Synthetic gitlink")
        with self.assertRaisesRegex(ValueError, "non-regular committed entry"):
            VERIFY.check(self.root)

    def test_symlink_git_mode_is_refused_without_os_symlink_privilege(self):
        self.commit()
        oid = self.git("rev-parse", "HEAD:README.md").decode().strip()
        self.git("update-index", "--cacheinfo", "120000," + oid + ",README.md")
        self.git("commit", "--quiet", "-m", "Synthetic symlink mode")
        with self.assertRaisesRegex(ValueError, "non-regular committed entry"):
            VERIFY.check(self.root)

    def test_missing_git_executable_bit_is_refused(self):
        self.files["README.md"]["mode"] = 0o755
        self.commit()
        with self.assertRaisesRegex(ValueError, "executable-bit mismatch"):
            VERIFY.check(self.root)

    def test_correct_explicit_index_executable_bit_is_accepted(self):
        self.files["README.md"]["mode"] = 0o755
        self.commit()
        self.git("update-index", "--chmod=+x", "--", "README.md")
        self.git("commit", "--quiet", "-m", "Synthetic executable flag")
        self.assertTrue(VERIFY.check(self.root)["git_executable_bits_verified"])

    def test_invalid_or_option_like_ref_is_refused(self):
        self.commit()
        for ref in ("not-a-local-ref", "--help"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                VERIFY.check(self.root, revision=ref)

    def test_unsafe_manifest_paths_are_refused(self):
        for name in ("../outside", "/outside", "a\\b", "a//b", ".git/config", "line\nbreak"):
            with self.subTest(path=name):
                self.files = {name: dict(self.files[next(iter(self.files))])}
                self.manifest["files"] = self.files
                self.commit()
                with self.assertRaisesRegex(ValueError, "unsafe"):
                    VERIFY.check(self.root)

    def test_duplicate_or_nonobject_manifest_is_refused(self):
        for raw in (b"[]", b'{"schema":"x","schema":"y","files":{}}'):
            with self.subTest(raw=raw):
                (self.root / "SOURCE_MANIFEST.json").write_bytes(raw)
                self.commit(write_manifest=False)
                with self.assertRaises(ValueError):
                    VERIFY.check(self.root)

    def test_missing_committed_manifest_is_refused(self):
        self.git("add", "README.md")
        self.git("commit", "--quiet", "-m", "Synthetic no manifest")
        with self.assertRaisesRegex(ValueError, "(?i)manifest.*missing"):
            VERIFY.check(self.root)

    def test_partial_clone_and_inherited_git_overrides_are_refused(self):
        self.commit()
        overrides = {
            "GIT_ALLOW_PROTOCOL": "https",
            "GIT_DIR": str(self.root / "absent-foreign-repository"),
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "protocol.https.allow",
            "GIT_CONFIG_VALUE_0": "always",
            "GIT_ASKPASS": "synthetic-must-not-execute",
            "GIT_TRACE": "1",
        }
        with patch.dict(os.environ, overrides):
            clean = VERIFY.git_environment()
            for name in overrides:
                self.assertNotIn(name, clean)
            self.assertEqual(clean["GIT_NO_LAZY_FETCH"], "1")
            self.assertEqual(clean["GIT_TERMINAL_PROMPT"], "0")
            self.assertTrue(VERIFY.check(self.root)["metadata_digest_verified"])
            self.git("config", "remote.placeholder.promisor", "true")
            with self.assertRaisesRegex(ValueError, "partial/promisor"):
                VERIFY.check(self.root)


if __name__ == "__main__":
    unittest.main()
