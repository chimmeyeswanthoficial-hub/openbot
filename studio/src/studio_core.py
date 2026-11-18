"""Dependency-free, offline planning primitives; not an execution authority.

No provider SDK, shell execution, account token, public write, VM driver, or IDE
installer exists in this module. Checksums identify content, not an approver.
The owner-controlled local filesystem remains trusted; directory permissions
are not a hostile-tenant isolation boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import unicodedata
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

VERSION = "0.3.0-local-planning"
POLICY_CHECKED = "2026-11-10"
MAX_JSON = 65_536
ROLES = ("builder", "researcher", "creator", "analyst")
PROVIDERS = ("unconfigured", "openai", "xai", "meta_or_local")
IDE_TOOLS = ("claude_code", "antigravity", "t3_code")
PLATFORMS = ("x", "instagram", "youtube")
SOURCES = {
    "x": [
        "https://help.x.com/en/rules-and-policies/x-automation",
        "https://docs.x.com/developer-terms/policy",
    ],
    "instagram": [
        "https://developers.facebook.com/documentation/instagram-platform/content-publishing"
    ],
    "youtube": [
        "https://developers.google.com/youtube/data/revision_history#november_2_2026",
        "https://developers.google.com/youtube/data/reference/rest/v3/videos/insert",
    ],
}
SECRET = re.compile(
    r"(?:\bsk-[A-Za-z0-9_-]{20,}|\bBearer\s+\S{16,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bAKIA[A-Z0-9]{16}\b)",
    re.IGNORECASE,
)


class PlanError(ValueError):
    """Stable, non-secret-bearing refusal code."""


def _json_value(value: Any, depth: int = 0) -> None:
    if depth > 24:
        raise PlanError("json_nesting_limit")
    if value is None or type(value) in (bool, int):
        if type(value) is int and abs(value) > 2**63 - 1:
            raise PlanError("json_integer_limit")
        return
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeError as exc:
            raise PlanError("valid_unicode_required") from exc
        return
    if type(value) is list and len(value) <= 1024:
        for child in value:
            _json_value(child, depth + 1)
        return
    if type(value) is dict and len(value) <= 1024:
        for key, child in value.items():
            if type(key) is not str:
                raise PlanError("json_string_keys_required")
            _json_value(key, depth + 1)
            _json_value(child, depth + 1)
        return
    raise PlanError("bounded_integer_json_required")


def canonical(value: Any) -> bytes:
    _json_value(value)
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise PlanError("duplicate_json_key")
        result[key] = value
    return result


def _non_integer(_):
    raise PlanError("integer_json_required")


def decode_json(raw: bytes) -> Any:
    if len(raw) > MAX_JSON:
        raise PlanError("json_byte_limit")
    try:
        result = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_float=_non_integer,
            parse_constant=_non_integer,
        )
        canonical(result)
        return result
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise PlanError("valid_bounded_json_required") from exc


def _unlinked_path(path: Path) -> Path:
    # Do not resolve: resolving would hide links from the following check.
    path = Path(os.path.abspath(path))
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise PlanError("symlink_not_allowed")
    return path


def _file_bytes(path: Path, *, limit: int = MAX_JSON, private: bool = False) -> bytes:
    path = _unlinked_path(path)
    try:
        fd = os.open(
            path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        )
        with os.fdopen(fd, "rb") as stream:
            observed = os.fstat(stream.fileno())
            if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
                raise PlanError("single_link_regular_file_required")
            if observed.st_size > limit:
                raise PlanError("file_byte_limit")
            if private and (
                observed.st_mode & 0o077
                or (hasattr(os, "getuid") and observed.st_uid != os.getuid())
            ):
                raise PlanError("private_owned_file_required")
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            if len(raw) > limit or (observed.st_size, observed.st_mtime_ns) != (
                after.st_size,
                after.st_mtime_ns,
            ):
                raise PlanError("file_changed_or_limit")
            return raw
    except OSError as exc:
        raise PlanError("readable_regular_file_required") from exc


def load_json(path: Path | str) -> Any:
    return decode_json(_file_bytes(Path(path)))


def _exact(value: Any, fields) -> None:
    if type(value) is not dict or set(value) != set(fields):
        raise PlanError("exact_versioned_fields_required")


def _text(value: Any, *, maximum: int, minimum: int = 0, multiline: bool = False) -> str:
    if type(value) is not str:
        raise PlanError("text_required")
    canonical(value)
    if len(value) > maximum:
        raise PlanError("text_length_limit")
    if any(
        unicodedata.category(c) in ("Cc", "Cs") and not (multiline and c in "\n\t\r") for c in value
    ):
        raise PlanError("text_control_character_refused")
    if SECRET.search(value):
        raise PlanError("possible_credential_refused_do_not_paste_secrets")
    value = value.strip()
    if len(value) < minimum:
        raise PlanError("nonempty_text_required")
    return value


def _choice(value, options):
    if type(value) is not str or value not in options:
        raise PlanError("unsupported_enum_value")
    return value


def _uuid(value):
    if type(value) is not str:
        raise PlanError("canonical_uuid4_required")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise PlanError("canonical_uuid4_required") from exc
    if str(parsed) != value or parsed.version != 4:
        raise PlanError("canonical_uuid4_required")
    return value


def _digest_plan(plan):
    return {**plan, "sha256": hashlib.sha256(canonical(plan)).hexdigest()}


def companion_plan(request: dict, *, companion_id: str | None = None) -> dict:
    _exact(request, {"name", "role", "provider", "ide_tools"})
    name = _text(request["name"], maximum=64, minimum=1)
    role = _choice(request["role"], ROLES)
    provider = _choice(request["provider"], PROVIDERS)
    tools = request["ide_tools"]
    if type(tools) is not list or len(tools) > len(IDE_TOOLS):
        raise PlanError("bounded_tool_list_required")
    chosen = [_choice(tool, IDE_TOOLS) for tool in tools]
    if len(set(chosen)) != len(chosen):
        raise PlanError("duplicate_tool_refused")
    identity = _uuid(companion_id) if companion_id is not None else str(uuid.uuid4())
    return _digest_plan(
        {
            "schema": "openbot.companion-blueprint/1",
            "id": identity,
            "name": name,
            "role": role,
            "provider_requested": provider,
            "authority": "planning_only",
            "execution_authorized": False,
            "model_connected": False,
            "vm_started": False,
            "workspace": {
                "kind": "vm_requested_not_provisioned",
                "owner_companion_id": identity,
                "separate_os_required": True,
                "network": "deny",
                "host_mounts": [],
                "secret_material": "none",
                "requested_vcpu": 2,
                "requested_ram_mib": 4096,
                "requested_disk_gib": 32,
                "resource_sizes_are_enforced": False,
            },
            "toolchain": [
                {
                    "tool": tool,
                    "status": "requested_not_installed",
                    "distribution_license_and_os_review_required": True,
                }
                for tool in IDE_TOOLS
                if tool in chosen
            ],
            "requirements": [
                "owner_selects_vm_host_and_cost_limit",
                "pinned_os_image_and_hypervisor_review",
                "real_per_bot_vm_provisioner_implementation",
                "host_and_cross_bot_isolation_tests",
                "explicit_network_and_secret_broker_policy",
                "pinned_ide_distribution_and_license_review",
                "provider_connection_and_budget_authorization",
                "human_authorization_before_install_or_start",
            ],
            "integrity_note": "SHA-256 is content integrity, not an authorization or signed approval.",
        }
    )


def _social_input(request):
    _exact(
        request,
        {
            "platform",
            "text",
            "title",
            "media_kind",
            "asset_sha256",
            "rights_ref",
            "ai_disclosure",
            "made_for_kids",
        },
    )
    draft = {
        "platform": _choice(request["platform"], PLATFORMS),
        "text": _text(request["text"], maximum=12000, multiline=True),
        "title": _text(request["title"], maximum=400),
        "media_kind": _choice(request["media_kind"], ("none", "image", "video")),
        "asset_sha256": _text(request["asset_sha256"], maximum=64),
        "rights_ref": _text(request["rights_ref"], maximum=200),
        "ai_disclosure": _choice(
            request["ai_disclosure"], ("original", "synthetic", "needs_review")
        ),
        "made_for_kids": _choice(request["made_for_kids"], ("yes", "no", "needs_review")),
    }
    if draft["asset_sha256"] and not re.fullmatch(r"[a-f0-9]{64}", draft["asset_sha256"]):
        raise PlanError("lowercase_sha256_required")
    return draft


def _normalized(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    return " ".join(text.split())


def _duplicate(draft, old):
    if draft["asset_sha256"] and draft["asset_sha256"] == old["asset_sha256"]:
        return True
    a, b = _normalized(draft["text"]), _normalized(old["text"])
    if a and a == b:
        return True
    # Bounded token overlap is an advisory, not a plagiarism/content-policy oracle.
    # Never rewrite a duplicate to bypass platform detection.
    aa, bb = set(re.findall(r"\w+", a)), set(re.findall(r"\w+", b))
    return bool(min(len(a), len(b)) >= 32 and aa and bb and len(aa & bb) * 10 >= len(aa | bb) * 8)


def social_plan(request: dict, *, history: list | None = None) -> dict:
    draft = _social_input(request)
    history = [] if history is None else history
    if type(history) is not list or len(history) > 100:
        raise PlanError("bounded_draft_history_required")
    old_drafts = [_social_input(old) for old in history]
    duplicate = any(_duplicate(draft, old) for old in old_drafts)
    requirements = [
        "oauth_not_connected",
        "publisher_adapter_not_implemented",
        "human_content_review_required",
        "exact_action_approval_required",
        "rights_review_required",
        "current_platform_policy_and_quota_review_required",
    ]
    notes = ["official_apis_only", "no_rate_limit_evasion", "no_ban_immunity"]
    kind, service = draft["media_kind"], draft["platform"]
    synthetic = {"original": False, "synthetic": True, "needs_review": None}[draft["ai_disclosure"]]
    audience = {"yes": True, "no": False, "needs_review": None}[draft["made_for_kids"]]
    if synthetic is None:
        requirements.append("ai_disclosure_review_required")
    if not draft["rights_ref"]:
        requirements.append("ownership_or_license_evidence_required")
    if kind != "none" and not draft["asset_sha256"]:
        requirements.append("exact_owned_asset_digest_required")
    if duplicate:
        requirements.append("duplicate_content_review_required")
    if service == "youtube":
        host = "www.googleapis.com"
        scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        metadata = {
            "snippet": {"title": draft["title"], "description": draft["text"]},
            "status": {
                "privacyStatus": "private",
                "containsSyntheticMedia": synthetic,
                "selfDeclaredMadeForKids": audience,
            },
            "notifySubscribers": False,
        }
        if kind != "video":
            requirements.append("owned_media_required")
        if not draft["title"]:
            requirements.append("video_title_required")
        if len(draft["title"]) > 100 or len(draft["text"]) > 5000:
            requirements.append("platform_text_length_review_required")
        if audience is None:
            requirements.append("audience_classification_required")
        notes += [
            "privacy_is_explicitly_private_not_provider_default",
            "unverified_private_upload_restriction_reversed_2026_11_02",
        ]
    elif service == "instagram":
        host = "graph.instagram.com"
        scopes = ["instagram_business_basic", "instagram_business_content_publish"]
        metadata = {
            "caption": draft["text"],
            "media_type": "REELS" if kind == "video" else "IMAGE",
            "is_ai_generated": synthetic,
        }
        requirements += [
            "professional_account_verification_required",
            "chosen_instagram_login_access_review_required",
            "approved_asset_host_required",
            "pinned_graph_api_version_required",
            "container_processing_and_publish_limit_check_required",
        ]
        if kind == "none":
            requirements.append("owned_media_required")
        if not draft["text"]:
            requirements.append("caption_review_required")
        if len(draft["text"]) > 2200:
            requirements.append("platform_text_length_review_required")
        notes += [
            "instagram_login_path_reference_only",
            "do_not_mix_facebook_or_unified_login_scopes",
            "quota_documentation_conflicts_query_actual_account_limits",
        ]
    else:
        host = "api.x.com"
        scopes = ["tweet.read", "tweet.write", "users.read"]
        metadata = {"text": draft["text"]}
        if not draft["text"]:
            requirements.append("post_text_required")
        if len(draft["text"]) > 280:
            requirements.append("account_specific_text_length_review_required")
        if "@" in draft["text"]:
            requirements.append("mention_and_recipient_consent_review_required")
        if kind != "none":
            requirements.append("separate_media_upload_review_required")
        requirements += ["bot_label_and_operator_review_required"]
        notes += [
            "automated_ai_replies_require_separate_platform_approval",
            "no_automated_likes",
            "no_unsolicited_dms_or_replies",
            "no_multi_account_duplicate_blast",
            "oauth_is_not_blanket_action_consent",
        ]
    return _digest_plan(
        {
            "schema": "openbot.social-review/1",
            "authority": "planning_only",
            "draft": draft,
            "action": "review_own_post_only",
            "account_connected": False,
            "external_write_enabled": False,
            "no_ban_guarantee": False,
            "duplicate_risk": duplicate,
            "duplicate_check_scope": "only_provided_local_drafts_not_platform_history",
            "requirements": requirements,
            "policy_notes": notes,
            "policy_checked_on": POLICY_CHECKED,
            "policy_sources": SOURCES[service].copy(),
            "api_host_reference": host,
            "scope_references_not_grants": scopes,
            "metadata_preview": metadata,
            "transport_request": None,
            "integrity_note": "SHA-256 identifies this preview, not a compliance decision or approval.",
        }
    )


def host_observation() -> dict:
    return {
        "schema": "openbot.host-observation/1",
        "os": platform.system(),
        "binary_detected": {
            name: shutil.which(name) is not None
            for name in ("qemu-system-x86_64", "virsh", "docker")
        },
        "kvm_device_present": Path("/dev/kvm").exists(),
        "vm_backend_implemented": False,
        "virtual_pc_running": False,
        "host_security_accepted": False,
        "interpretation": "Presence is not usability; folders, containers and namespace fixtures are not virtual PCs.",
    }


class BlueprintStore:
    """Explicit local private blueprint directories. No process or VM is created."""

    def __init__(self, root: Path | str, *, initialize: bool = False):
        self.root = _unlinked_path(Path(root))
        if initialize:
            try:
                self.root.mkdir(mode=0o700, exist_ok=False)
            except OSError as exc:
                raise PlanError("new_private_store_parent_required") from exc
        self._check_root()

    def _check_root(self):
        _unlinked_path(self.root)
        try:
            observed = self.root.stat()
        except OSError as exc:
            raise PlanError("existing_private_store_required") from exc
        if (
            not stat.S_ISDIR(observed.st_mode)
            or observed.st_mode & 0o077
            or (hasattr(os, "getuid") and observed.st_uid != os.getuid())
        ):
            raise PlanError("private_owned_store_required")

    def create_companion(self, request):
        plan = companion_plan(request)
        self._check_root()
        if len(list(self.root.iterdir())) >= 100:
            raise PlanError("local_blueprint_capacity")
        folder = self.root / plan["id"]
        try:
            folder.mkdir(mode=0o700, exist_ok=False)
            fd = os.open(
                folder / "blueprint.json",
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            with os.fdopen(fd, "wb") as stream:
                stream.write(canonical(plan) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            raise PlanError("new_blueprint_write_failed") from exc
        return plan

    def read_companion(self, identity):
        identity = _uuid(identity)
        self._check_root()
        folder = _unlinked_path(self.root / identity)
        try:
            observed = folder.stat()
        except OSError as exc:
            raise PlanError("companion_blueprint_missing") from exc
        if (
            not stat.S_ISDIR(observed.st_mode)
            or observed.st_mode & 0o077
            or (hasattr(os, "getuid") and observed.st_uid != os.getuid())
        ):
            raise PlanError("private_owned_companion_directory_required")
        stored = decode_json(_file_bytes(folder / "blueprint.json", private=True))
        try:
            expected = companion_plan(
                {
                    "name": stored["name"],
                    "role": stored["role"],
                    "provider": stored["provider_requested"],
                    "ide_tools": [item["tool"] for item in stored["toolchain"]],
                },
                companion_id=identity,
            )
        except (KeyError, TypeError) as exc:
            raise PlanError("invalid_blueprint") from exc
        if canonical(stored) != canonical(expected):
            raise PlanError("blueprint_integrity_or_schema_mismatch")
        return stored

    def list_companions(self):
        self._check_root()
        items = sorted(self.root.iterdir())
        if len(items) > 100:
            raise PlanError("local_blueprint_capacity")
        return [self.read_companion(path.name) for path in items]


EXPORT_EXTENSIONS = {
    ".md",
    ".txt",
    ".py",
    ".html",
    ".css",
    ".js",
    ".ts",  # Explicitly listed, text-only upstream review sources; never executed here.
    ".cjs",
    ".mjs",
    ".json",
    ".toml",
    ".svg",
    ".sh",
    ".yaml",
    ".yml",
}
EXPORT_DENIED_PARTS = {
    ".git",
    ".env",
    ".openbot",
    "node_modules",
    "__pycache__",
    ".venv",
    ".cache",
    "runtime",
    "private",
    "state",
    "credentials",
    "secrets",
}


def clean_export(source: Path | str, files: list[str], output: Path | str) -> dict:
    """Reproducible, allowlisted SOURCE export, never a backup of runtime state."""
    root, target = _unlinked_path(Path(source)), _unlinked_path(Path(output))
    if not root.is_dir() or type(files) is not list or not files or len(files) > 512:
        raise PlanError("explicit_bounded_source_allowlist_required")
    if any(type(name) is not str for name in files) or len(set(files)) != len(files):
        raise PlanError("unique_source_allowlist_required")
    blobs = {}
    total = 0
    for name in sorted(files):
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or str(relative) != name
            or "\\" in name
            or not relative.parts
            or any(
                part in ("", ".", "..")
                or part.lower() in EXPORT_DENIED_PARTS
                or part.lower().startswith(".env")
                for part in relative.parts
            )
            or name == "EXPORT_MANIFEST.json"
            or (
                relative.suffix.lower() not in EXPORT_EXTENSIONS
                and relative.name not in {"LICENSE", "NOTICE", "Makefile", ".gitignore"}
            )
        ):
            raise PlanError("source_export_path_refused")
        raw = _file_bytes(root / name, limit=4 * 1024 * 1024)
        try:
            text = raw.decode("utf-8")
        except UnicodeError as exc:
            raise PlanError("text_source_only") from exc
        # A heuristic is defense in depth, not a full-history secret clearance.
        if "\0" in text or SECRET.search(text):
            raise PlanError("possible_secret_or_binary_export_refused")
        total += len(raw)
        if total > 32 * 1024 * 1024:
            raise PlanError("source_export_total_limit")
        blobs[name] = raw
    manifest = {
        "schema": "openbot.clean-source-export/1",
        "scope": "only_explicit_allowlisted_source_not_a_full_workspace_backup",
        "files": {
            name: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            for name, raw in blobs.items()
        },
        "omitted": "All unlisted paths, runtime state, tokens, private bot data and dependencies.",
        "not_a_signed_release": True,
    }
    blobs["EXPORT_MANIFEST.json"] = canonical(manifest) + b"\n"
    # Exclusive creation is essential: source export cannot overwrite a backup.
    try:
        with (
            target.open("xb") as stream,
            zipfile.ZipFile(
                stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
            ) as archive,
        ):
            for name, raw in sorted(blobs.items()):
                item = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                item.create_system = 3
                item.external_attr = 0o100644 << 16
                item.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(item, raw)
    except FileExistsError as exc:
        raise PlanError("new_export_target_required") from exc
    return {
        "schema": manifest["schema"],
        "files": len(blobs),
        "bytes": target.stat().st_size,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }
