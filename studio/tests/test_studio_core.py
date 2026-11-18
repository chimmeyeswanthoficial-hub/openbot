"""Local planning/export tests. No model, account, VM or public post is used."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from studio_core import (
    BlueprintStore,
    PlanError,
    canonical,
    clean_export,
    companion_plan,
    host_observation,
    load_json,
    social_plan,
)


def companion(**changes):
    return {
        "name": "Atlas",
        "role": "builder",
        "provider": "unconfigured",
        "ide_tools": ["claude_code", "antigravity", "t3_code"],
        **changes,
    }


def social(**changes):
    return {
        "platform": "youtube",
        "text": "A video made from owned footage.",
        "title": "Owned field notes",
        "media_kind": "video",
        "asset_sha256": "a" * 64,
        "rights_ref": "owned:fixture",
        "ai_disclosure": "original",
        "made_for_kids": "no",
        **changes,
    }


class PlanningTests(unittest.TestCase):
    def test_companions_are_unprovisioned_even_with_named_providers_and_ides(self):
        for provider in ["unconfigured", "openai", "xai", "meta_or_local"]:
            with self.subTest(provider=provider):
                plan = companion_plan(companion(provider=provider))
                self.assertEqual(plan["workspace"]["kind"], "vm_requested_not_provisioned")
                self.assertFalse(plan["model_connected"])
                self.assertFalse(plan["vm_started"])
                self.assertEqual(plan["workspace"]["network"], "deny")
                self.assertEqual(plan["workspace"]["host_mounts"], [])
                self.assertEqual(
                    {x["status"] for x in plan["toolchain"]}, {"requested_not_installed"}
                )
                self.assertEqual(plan["authority"], "planning_only")

    def test_provider_aliases_paths_commands_credentials_and_fake_status_cannot_be_injected(self):
        for changes in [
            {"provider": "openai;curl example.invalid"},
            {"name": "sk-" + "q" * 35},
            {"command": "bash"},
            {"workspace": "/home/user"},
            {"vm_started": True},
            {"ide_tools": ["custom-shell"]},
            {"name": "\x00bad"},
            {"role": "owner"},
            {"name": " "},
            {"ide_tools": ["claude_code", "claude_code"]},
        ]:
            with self.subTest(changes=changes), self.assertRaises(PlanError):
                companion_plan(companion(**changes))

    def test_all_input_objects_are_copied_not_retained(self):
        request = companion()
        plan = companion_plan(request)
        request["ide_tools"].clear()
        request["name"] = "changed"
        self.assertEqual(plan["name"], "Atlas")
        self.assertEqual(len(plan["toolchain"]), 3)

    def test_plan_checksum_is_integrity_not_approval(self):
        plan = companion_plan(companion(), companion_id=str(uuid.uuid4()))
        raw = {k: v for k, v in plan.items() if k != "sha256"}
        self.assertEqual(plan["sha256"], hashlib.sha256(canonical(raw)).hexdigest())
        self.assertFalse(plan["execution_authorized"])
        self.assertIn("not an authorization", plan["integrity_note"])

    def test_youtube_privacy_is_explicit_not_delegated_to_provider_default(self):
        plan = social_plan(social())
        self.assertEqual(plan["metadata_preview"]["status"]["privacyStatus"], "private")
        self.assertFalse(plan["metadata_preview"]["notifySubscribers"])
        self.assertFalse(plan["metadata_preview"]["status"]["containsSyntheticMedia"])
        self.assertFalse(plan["external_write_enabled"])
        self.assertFalse(plan["account_connected"])
        self.assertIsNone(plan["transport_request"])

    def test_synthetic_media_is_explicit_and_unknown_is_never_silently_false(self):
        self.assertTrue(
            social_plan(social(ai_disclosure="synthetic"))["metadata_preview"]["status"][
                "containsSyntheticMedia"
            ]
        )
        unknown = social_plan(social(ai_disclosure="needs_review", made_for_kids="needs_review"))
        self.assertIsNone(unknown["metadata_preview"]["status"]["containsSyntheticMedia"])
        self.assertIsNone(unknown["metadata_preview"]["status"]["selfDeclaredMadeForKids"])
        self.assertIn("ai_disclosure_review_required", unknown["requirements"])
        self.assertIn("audience_classification_required", unknown["requirements"])

    def test_instagram_is_professional_account_and_public_asset_review_not_ready_upload(self):
        plan = social_plan(social(platform="instagram", media_kind="image", title=""))
        self.assertIn("professional_account_verification_required", plan["requirements"])
        self.assertIn("approved_asset_host_required", plan["requirements"])
        self.assertEqual(plan["api_host_reference"], "graph.instagram.com")
        self.assertIsNone(plan["transport_request"])
        self.assertFalse(plan["external_write_enabled"])

    def test_x_has_no_replies_dms_likes_or_multiaccount_blast_shortcuts(self):
        plan = social_plan(social(platform="x", media_kind="none", asset_sha256="", title=""))
        self.assertIn(
            "automated_ai_replies_require_separate_platform_approval", plan["policy_notes"]
        )
        for extra in [
            {"action": "auto_reply"},
            {"accounts": ["one", "two"]},
            {"endpoint": "https://evil.invalid"},
            {"cookie": "stolen"},
            {"oauth_approved": True},
        ]:
            with self.subTest(extra=extra), self.assertRaises(PlanError):
                social_plan(social(platform="x", **extra))

    def test_duplicate_normalization_is_conservative_not_an_evasion_rewriter(self):
        old = social(
            platform="x",
            text="Our owned release notes are ready for careful human review",
            media_kind="none",
            asset_sha256="",
        )
        for text in [
            " OUR owned release NOTES are ready for careful human review  ",
            "Our owned release notes are ready for careful human review today",
            "Our owned release notes are ready for careful human re\u200bview",
        ]:
            with self.subTest(text=text):
                current = social_plan({**old, "text": text}, history=[old])
                self.assertTrue(current["duplicate_risk"])
                self.assertIn("duplicate_content_review_required", current["requirements"])
                self.assertEqual(current["draft"]["text"], text.strip())

    def test_other_platforms_require_a_separate_review(self):
        for platform in ["tiktok", "facebook", "linkedin", "reddit", "mastodon", "X", ""]:
            with self.subTest(platform=platform), self.assertRaises(PlanError):
                social_plan(social(platform=platform))

    def test_types_bounds_and_bogus_media_digests_are_refused(self):
        for change in [
            {"text": True},
            {"title": "a" * 401},
            {"text": "a" * 12001},
            {"asset_sha256": "g" * 64},
            {"asset_sha256": "../secret"},
            {"made_for_kids": False},
            {"ai_disclosure": False},
            {"media_kind": "shell"},
            {"rights_ref": "Bearer " + "a" * 45},
        ]:
            with self.subTest(change=change), self.assertRaises(PlanError):
                social_plan(social(**change))

    def test_incomplete_drafts_stay_blocked_instead_of_faking_success(self):
        plan = social_plan(social(title="", media_kind="none", asset_sha256="", rights_ref=""))
        for need in [
            "owned_media_required",
            "rights_review_required",
            "video_title_required",
            "oauth_not_connected",
            "publisher_adapter_not_implemented",
        ]:
            self.assertIn(need, plan["requirements"])
        self.assertFalse(plan["external_write_enabled"])
        self.assertFalse(plan["no_ban_guarantee"])

    def test_json_canonicalization_rejects_floats_nonstring_keys_and_objects(self):
        for bad in [1.0, {"x": float("nan")}, {1: "x"}, object()]:
            with self.subTest(bad=type(bad).__name__), self.assertRaises(PlanError):
                canonical(bad)

    def test_no_network_or_model_call_during_any_planning(self):
        with patch.object(socket, "socket", side_effect=AssertionError("outbound forbidden")):
            companion_plan(companion())
            social_plan(social())
            host_observation()

    def test_host_inspection_does_not_certify_a_vm_from_a_path_or_binary(self):
        observed = host_observation()
        self.assertFalse(observed["vm_backend_implemented"])
        self.assertFalse(observed["virtual_pc_running"])
        self.assertFalse(observed["host_security_accepted"])
        self.assertIn("os", observed)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_missing_store_does_not_implicitly_initialize(self):
        with self.assertRaises(PlanError):
            BlueprintStore(self.root / "missing")
        self.assertFalse((self.root / "missing").exists())

    @unittest.skipIf(os.name != "posix", "POSIX private permissions (0o700) required; Windows CLI boundary fails closed")
    def test_real_per_companion_private_directories_are_only_blueprints_not_vms(self):
        store = BlueprintStore(self.root / "private", initialize=True)
        one = store.create_companion(companion())
        two = store.create_companion(companion(name="Lyra"))
        self.assertNotEqual(one["id"], two["id"])
        self.assertEqual(len(store.list_companions()), 2)
        for item in [one, two]:
            folder = store.root / item["id"]
            self.assertTrue(folder.is_dir())
            self.assertEqual(folder.stat().st_mode & 0o777, 0o700)
            self.assertEqual((folder / "blueprint.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual(store.read_companion(item["id"]), item)
            self.assertFalse(item["vm_started"])

    @unittest.skipIf(os.name != "posix", "POSIX private permissions (0o700) required; Windows CLI boundary fails closed")
    def test_paths_symlink_hardlink_and_tampered_blueprints_fail_closed(self):
        store = BlueprintStore(self.root / "private", initialize=True)
        item = store.create_companion(companion())
        for value in ["../outside", "/etc/passwd", "0" * 32, "not-an-id"]:
            with self.subTest(value=value), self.assertRaises(PlanError):
                store.read_companion(value)
        path = store.root / item["id"] / "blueprint.json"
        original = path.read_bytes()
        value = json.loads(original)
        value["vm_started"] = True
        path.write_text(json.dumps(value))
        with self.assertRaises(PlanError):
            store.read_companion(item["id"])
        path.write_bytes(original)
        os.link(path, self.root / "linked.json")
        with self.assertRaises(PlanError):
            store.read_companion(item["id"])

    @unittest.skipIf(os.name != "posix", "POSIX private permissions (0o700) required; Windows CLI boundary fails closed")
    def test_integer_zero_cannot_impersonate_boolean_false_in_stored_blueprint(self):
        store = BlueprintStore(self.root / "private", initialize=True)
        item = store.create_companion(companion())
        path = store.root / item["id"] / "blueprint.json"
        value = json.loads(path.read_bytes())
        value["vm_started"] = 0
        path.write_text(json.dumps(value))
        with self.assertRaises(PlanError):
            store.read_companion(item["id"])

    def test_store_rejects_linked_or_nonprivate_root(self):
        actual = self.root / "actual"
        actual.mkdir(mode=0o700)
        linked = self.root / "linked"
        linked.symlink_to(actual, target_is_directory=True)
        with self.assertRaises(PlanError):
            BlueprintStore(linked, initialize=True)
        actual.chmod(0o755)
        with self.assertRaises(PlanError):
            BlueprintStore(actual)

    @unittest.skipIf(os.name != "posix", "POSIX private permissions (0o700) required; Windows CLI boundary fails closed")
    def test_schema_and_input_cannot_supply_a_runtime_or_account(self):
        store = BlueprintStore(self.root / "private", initialize=True)
        with self.assertRaises(PlanError):
            store.create_companion(companion(api_key="hidden"))
        self.assertEqual(store.list_companions(), [])

    @unittest.skipIf(os.name == "posix", "Windows CLI boundary fails closed test")
    def test_windows_store_fails_closed_without_posix_permissions(self):
        with self.assertRaises(PlanError) as ctx:
            BlueprintStore(self.root / "private", initialize=True)
        self.assertEqual(str(ctx.exception), "private_owned_store_required")

    def test_json_loader_refuses_duplicate_keys_links_and_oversized_data(self):
        path = self.root / "draft.json"
        path.write_text('{"a":1,"a":2}')
        with self.assertRaises(PlanError):
            load_json(path)
        path.write_text("x" * 70000)
        with self.assertRaises(PlanError):
            load_json(path)
        path.unlink()
        path.symlink_to(self.root / "missing")
        with self.assertRaises(PlanError):
            load_json(path)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "project"
        self.source.mkdir()
        (self.source / "README.md").write_text("Owned source")
        (self.source / "main.py").write_text('print("local")\n')

    def test_export_contains_only_reviewed_source_and_exact_checksums(self):
        (self.source / ".env").write_text("NEVER_EXPORT=secret")
        (self.source / "state.sqlite3").write_bytes(b"private")
        target = self.root / "source.zip"
        receipt = clean_export(self.source, ["README.md", "main.py"], target)
        with zipfile.ZipFile(target) as archive:
            self.assertEqual(
                set(archive.namelist()), {"README.md", "main.py", "EXPORT_MANIFEST.json"}
            )
            manifest = json.loads(archive.read("EXPORT_MANIFEST.json"))
            for name, meta in manifest["files"].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), meta["sha256"])
        self.assertEqual(receipt["sha256"], hashlib.sha256(target.read_bytes()).hexdigest())
        self.assertEqual((self.source / ".env").read_text(), "NEVER_EXPORT=secret")

    def test_export_refuses_traversal_credentials_binary_state_and_duplicates(self):
        (self.source / ".env").write_text("private")
        (self.source / "state.db").write_bytes(b"private")
        for files in [
            ["../outside"],
            ["/etc/passwd"],
            [".env"],
            ["state.db"],
            ["README.md", "README.md"],
        ]:
            with self.subTest(files=files), self.assertRaises(PlanError):
                clean_export(self.source, files, self.root / (uuid.uuid4().hex + ".zip"))

    def test_export_never_overlays_existing_output(self):
        target = self.root / "source.zip"
        target.write_bytes(b"KEEP")
        with self.assertRaises(PlanError):
            clean_export(self.source, ["README.md"], target)
        self.assertEqual(target.read_bytes(), b"KEEP")

    def test_export_rejects_symlink_and_hardlink_sources(self):
        (self.source / "linked.py").symlink_to(self.source / "main.py")
        with self.assertRaises(PlanError):
            clean_export(self.source, ["linked.py"], self.root / "linked.zip")
        try:
            os.link(self.source / "main.py", self.source / "hard.py")
            with self.assertRaises(PlanError):
                clean_export(self.source, ["hard.py"], self.root / "hard.zip")
        except PermissionError:
            (self.source / "hard.py").write_text('print("hardlink simulation")\n')
            from unittest.mock import patch
            orig_fstat = os.fstat
            def fake_fstat(fd):
                res = orig_fstat(fd)
                return os.stat_result((res.st_mode, res.st_ino, res.st_dev, 2, res.st_uid, res.st_gid, res.st_size, res.st_atime, res.st_mtime, res.st_ctime))
            with patch("os.fstat", fake_fstat):
                with self.assertRaises(PlanError):
                    clean_export(self.source, ["hard.py"], self.root / "hard.zip")

    def test_export_is_reproducible_and_does_not_mutate_source(self):
        before = {p.name: p.read_bytes() for p in self.source.iterdir()}
        clean_export(self.source, ["README.md", "main.py"], self.root / "one.zip")
        clean_export(self.source, ["main.py", "README.md"], self.root / "two.zip")
        self.assertEqual((self.root / "one.zip").read_bytes(), (self.root / "two.zip").read_bytes())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.source.iterdir()})


if __name__ == "__main__":
    unittest.main()
