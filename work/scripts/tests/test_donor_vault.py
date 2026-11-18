"""Lossless donor recovery must refuse malformed archives before writing anything."""
from __future__ import annotations

import hashlib
import io
import json
import stat
import tarfile

import donor_vault as vault
import pytest


def _archive(tmp_path, *, change=None, extra=(), remove=()):
    entries = [("LICENSE", b"MIT; donor copyright", 0o644),
               ("src/review.ts", b"inert reference only\n", 0o755)]
    manifest = {"schema": 1, "source_root": "repos/OpenDots", "files": [
        {"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
         "mode": mode} for path, data, mode in entries], "protected_omissions": [".env"]}
    if change:
        change(manifest)
    members = [("donor-source/manifest.json", json.dumps(manifest).encode(), 0o644),
               *[(f"donor-source/files/{path}", data, mode) for path, data, mode in entries]]
    path = tmp_path / "donor.tar.xz"
    with tarfile.open(path, "w:xz") as archive:
        for name, data, mode in [*members, *extra]:
            if name in remove:
                continue
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), mode
            archive.addfile(info, io.BytesIO(data))
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_verify_is_read_only_and_restore_preserves_exact_bytes_and_modes(tmp_path):
    path, digest = _archive(tmp_path)
    result = vault.verify_archive(path, expected_sha256=digest)
    assert result["validated"] and result["files"] == 2
    assert result["source_root"] == "repos/OpenDots"
    dest = tmp_path / "new-restore"
    assert not dest.exists()
    restored = vault.restore_archive(path, dest, expected_sha256=digest)
    assert restored["files_restored"] == 2
    assert (dest / "src/review.ts").read_bytes() == b"inert reference only\n"
    assert stat.S_IMODE((dest / "src/review.ts").stat().st_mode) == 0o755
    assert (dest / "LICENSE").read_bytes() == b"MIT; donor copyright"
    assert not (dest / ".env").exists()
    assert path.exists()


@pytest.mark.parametrize("value", ["", "not-a-digest", "0" * 64])
def test_wrong_or_absent_digest_refuses_before_creating_destination(tmp_path, value):
    path, _ = _archive(tmp_path)
    dest = tmp_path / "never-created"
    with pytest.raises(ValueError):
        vault.restore_archive(path, dest, expected_sha256=value)
    assert not dest.exists()


@pytest.mark.parametrize("name", ["/absolute", "../escape", "donor-source/../escape",
                                  "donor-source/files/folder\\escape", "other/files/x"])
def test_unsafe_or_foreign_member_path_refuses_before_restore(tmp_path, name):
    path, digest = _archive(tmp_path, extra=[(name, b"bad", 0o644)])
    dest = tmp_path / "never-created"
    with pytest.raises(ValueError):
        vault.restore_archive(path, dest, expected_sha256=digest)
    assert not dest.exists()


@pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.DIRTYPE,
                                  tarfile.FIFOTYPE, tarfile.CHRTYPE])
def test_links_and_nonregular_members_are_refused(tmp_path, kind):
    path, _ = _archive(tmp_path)
    with tarfile.open(path) as archive:
        original = [(m, archive.extractfile(m).read()) for m in archive]
    with tarfile.open(path, "w:xz") as archive:
        for info, data in original:
            archive.addfile(info, io.BytesIO(data))
        info = tarfile.TarInfo("donor-source/files/unsafe")
        info.type, info.linkname = kind, "../../outside"
        archive.addfile(info)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        vault.verify_archive(path, expected_sha256=digest)


@pytest.mark.parametrize("source", ["apps/bot-hq", "tools/findrepo", "repos/OpenBot", "../rakazo", [], {}, None])
def test_active_tools_and_other_roots_cannot_be_mislabelled_as_retired_donors(tmp_path, source):
    path, digest = _archive(tmp_path, change=lambda m: m.update(source_root=source))
    with pytest.raises(ValueError):
        vault.verify_archive(path, expected_sha256=digest)


@pytest.mark.parametrize("mutate", [
    lambda m: m.update(schema=2),
    lambda m: m.update(files=[]),
    lambda m: m["files"].append(dict(m["files"][0])),
    lambda m: m["files"][1].update(path="../escape"),
    lambda m: m["files"][1].update(path=".env"),
    lambda m: m["files"][1].update(bytes=True),
    lambda m: m["files"][1].update(bytes=-1),
    lambda m: m["files"][1].update(bytes=1),
    lambda m: m["files"][1].update(mode=0o644),
    lambda m: m["files"][1].update(mode=0o4755),
    lambda m: m["files"][1].update(sha256="0" * 64),
])
def test_manifest_schema_set_sizes_modes_hashes_and_credentials_are_checked(tmp_path, mutate):
    path, digest = _archive(tmp_path, change=mutate)
    dest = tmp_path / "never-created"
    with pytest.raises(ValueError):
        vault.restore_archive(path, dest, expected_sha256=digest)
    assert not dest.exists()


@pytest.mark.parametrize("remove", [("donor-source/manifest.json",),
                                    ("donor-source/files/LICENSE",)])
def test_missing_manifest_or_payload_cannot_be_recovered(tmp_path, remove):
    path, digest = _archive(tmp_path, remove=remove)
    with pytest.raises(ValueError):
        vault.verify_archive(path, expected_sha256=digest)


def test_duplicate_archive_member_is_refused(tmp_path):
    path, digest = _archive(tmp_path, extra=[("donor-source/files/LICENSE", b"MIT; donor copyright", 0o644)])
    with pytest.raises(ValueError):
        vault.verify_archive(path, expected_sha256=digest)


def test_special_permission_bits_are_refused(tmp_path):
    path, digest = _archive(tmp_path, extra=[("donor-source/files/x", b"x", 0o4755)])
    with pytest.raises(ValueError):
        vault.verify_archive(path, expected_sha256=digest)


def test_restore_never_overlays_existing_work(tmp_path):
    path, digest = _archive(tmp_path)
    dest = tmp_path / "existing"
    dest.mkdir()
    (dest / "LICENSE").write_text("owner work")
    with pytest.raises(ValueError):
        vault.restore_archive(path, dest, expected_sha256=digest)
    assert (dest / "LICENSE").read_text() == "owner work"


def test_archive_and_destination_symlinks_are_refused(tmp_path):
    path, digest = _archive(tmp_path)
    link = tmp_path / "link.tar.xz"
    link.symlink_to(path)
    with pytest.raises(ValueError):
        vault.verify_archive(link, expected_sha256=digest)
    parent = tmp_path / "linked-parent"
    parent.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        vault.restore_archive(path, parent / "escape", expected_sha256=digest)
    assert not (tmp_path / "escape").exists()


def test_unpacked_byte_limit_is_enforced_before_restore(tmp_path, monkeypatch):
    path, digest = _archive(tmp_path)
    monkeypatch.setattr(vault, "MAX_BYTES", 10)
    dest = tmp_path / "never-created"
    with pytest.raises(ValueError):
        vault.restore_archive(path, dest, expected_sha256=digest)
    assert not dest.exists()


def test_file_count_limit_is_enforced(tmp_path, monkeypatch):
    path, digest = _archive(tmp_path)
    monkeypatch.setattr(vault, "MAX_FILES", 1)
    with pytest.raises(ValueError):
        vault.verify_archive(path, expected_sha256=digest)


def test_cli_verify_never_prints_source_contents(tmp_path, capsys):
    path, digest = _archive(tmp_path)
    assert vault.main(["verify", str(path), "--sha256", digest]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["validated"] and "manifest" not in output
    assert "inert reference" not in json.dumps(output)


def test_file_cannot_also_be_a_parent_directory(tmp_path):
    def add_parent(manifest):
        manifest["files"].append({"path": "src", "bytes": 1,
                                  "sha256": hashlib.sha256(b"x").hexdigest(), "mode": 0o644})
    path, digest = _archive(tmp_path, change=add_parent,
                            extra=[("donor-source/files/src", b"x", 0o644)])
    with pytest.raises(ValueError):
        vault.verify_archive(path, expected_sha256=digest)


def test_manifest_byte_limit_is_enforced_before_restore(tmp_path, monkeypatch):
    path, digest = _archive(tmp_path)
    monkeypatch.setattr(vault, "MAX_MANIFEST_BYTES", 1)
    with pytest.raises(ValueError):
        vault.restore_archive(path, tmp_path / "never-created", expected_sha256=digest)
    assert not (tmp_path / "never-created").exists()


def test_cli_rejects_tampering_without_creating_output(tmp_path, capsys):
    path, _ = _archive(tmp_path)
    assert vault.main(["restore", str(path), "--sha256", "0" * 64,
                       "--destination", str(tmp_path / "never-created")]) == 2
    assert "SHA-256 mismatch" in capsys.readouterr().err
    assert not (tmp_path / "never-created").exists()
