"""Portable handoff: safe archive names/types, file integrity and session redaction."""
from __future__ import annotations

import io
import sqlite3
import tarfile

import handoff
import pytest


def test_create_keeps_project_context_and_excludes_credentials_generated_files(tmp_path):
    (tmp_path / ".claude/skills/example").mkdir(parents=True)
    (tmp_path / ".claude/skills/example/SKILL.md").write_text("inert instructions")
    (tmp_path / "CONTINUE_HERE.md").write_text("read memory then brain")
    (tmp_path / ".env").write_text("secret must not be packed")
    (tmp_path / ".env.example").write_text("KEY=")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules/generated.txt").write_text("generated")
    (tmp_path / ".config").mkdir()
    (tmp_path / ".config/private.json").write_text("private harness config")
    receipt = handoff.create_bundle(tmp_path, task_date="2026-11-10")
    result = handoff.verify_bundle(tmp_path / handoff.ARCHIVE_NAME, expected_sha256=receipt["archive_sha256"])
    assert result["validated"] and result["regular_files"] == 4  # three project files + manifest
    assert receipt["manifest_location"] == "inside archive only"
    assert not (tmp_path / handoff.MANIFEST).exists()  # do not duplicate a full-project manifest beside the tar
    with tarfile.open(tmp_path / handoff.ARCHIVE_NAME) as archive:
        names = archive.getnames()
        assert f"{handoff.PREFIX}/.env.example" in names
        assert f"{handoff.PREFIX}/CONTINUE_HERE.md" in names
        assert not any(n.endswith("/.env") or "/node_modules/" in n or "/.config/" in n for n in names)


@pytest.mark.parametrize("name", ["/absolute", "../escape", "openbot-continuation/../escape", "openbot-continuation/folder\\escape"])
def test_unsafe_archive_paths_are_rejected(tmp_path, name):
    path = tmp_path / "bad.tar"
    with tarfile.open(path, "w") as archive:
        info = tarfile.TarInfo(name)
        info.size = 1
        archive.addfile(info, io.BytesIO(b"x"))
    with pytest.raises(ValueError):
        handoff.verify_bundle(path)


def test_archive_links_are_rejected_before_extraction(tmp_path):
    path = tmp_path / "bad.tar"
    with tarfile.open(path, "w") as archive:
        info = tarfile.TarInfo("openbot-continuation/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "../../outside"
        archive.addfile(info)
    with pytest.raises(ValueError):
        handoff.verify_bundle(path)


def test_duplicate_members_are_rejected(tmp_path):
    path = tmp_path / "bad.tar"
    with tarfile.open(path, "w") as archive:
        for _ in range(2):
            info = tarfile.TarInfo("openbot-continuation/same")
            archive.addfile(info, io.BytesIO(b""))
    with pytest.raises(ValueError):
        handoff.verify_bundle(path)


def test_modified_payload_does_not_pass_its_original_manifest(tmp_path):
    (tmp_path / "PROJECT_BRAIN.md").write_text("preserve this reasoning")
    handoff.create_bundle(tmp_path, task_date="2026-11-10")
    original = tmp_path / handoff.ARCHIVE_NAME
    tampered = tmp_path / "tampered.tar"
    with tarfile.open(original) as source, tarfile.open(tampered, "w") as out:
        for member in source:
            data = source.extractfile(member).read()
            if member.name.endswith("/PROJECT_BRAIN.md"):
                data = b"malicious replacement"
            copy = tarfile.TarInfo(member.name)
            copy.size = len(data)
            out.addfile(copy, io.BytesIO(data))
    with pytest.raises(ValueError):
        handoff.verify_bundle(tampered)


def test_sqlite_snapshot_strips_auth_without_changing_business_rows(tmp_path):
    source, target = tmp_path / "source.sqlite3", tmp_path / "snapshot.sqlite3"
    with sqlite3.connect(source) as db:
        db.executescript("CREATE TABLE auth_sessions(token TEXT); CREATE TABLE login_attempts(id TEXT); CREATE TABLE tasks(id TEXT, note TEXT);")
        db.execute("INSERT INTO auth_sessions VALUES (?)", ("disposable-auth-secret",))
        db.execute("INSERT INTO tasks VALUES (?,?)", ("task1", "preserve this evidence"))
    result = handoff.snapshot_database(source, target, sanitize_hq=True)
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT count(*) FROM auth_sessions").fetchone()[0] == 0
        assert db.execute("SELECT note FROM tasks").fetchone()[0] == "preserve this evidence"
    assert b"disposable-auth-secret" not in target.read_bytes()
    assert result["business_counts_preserved"] is True
    with sqlite3.connect(source) as db:
        assert db.execute("SELECT count(*) FROM auth_sessions").fetchone()[0] == 1  # source not erased


def test_wal_snapshot_is_closed_redacted_and_stable_before_packaging(tmp_path, monkeypatch):
    """A connection context commits but does NOT close/checkpoint a WAL database."""
    source, target = tmp_path / "live.sqlite3", tmp_path / "export.sqlite3"
    original_connect = sqlite3.connect
    live = original_connect(source)
    live.execute("PRAGMA journal_mode=WAL")
    live.executescript("CREATE TABLE auth_sessions(token TEXT); CREATE TABLE tasks(note TEXT);")
    live.execute("INSERT INTO auth_sessions VALUES ('wal-auth-must-not-travel')")
    live.execute("INSERT INTO tasks VALUES ('retain live business evidence')")
    live.commit()
    connections = []

    def retain_connection(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        connections.append(connection)  # no accidental GC checkpoint can hide the bug
        return connection

    monkeypatch.setattr(sqlite3, "connect", retain_connection)
    try:
        handoff.snapshot_database(source, target, sanitize_hq=True)
        for connection in connections:
            with pytest.raises(sqlite3.ProgrammingError, match="closed"):
                connection.execute("SELECT 1")
        payload = target.read_bytes()
        assert b"wal-auth-must-not-travel" not in payload
        assert not target.with_name(target.name + "-wal").exists()
        portable = tmp_path / "main-file-only.sqlite3"
        portable.write_bytes(payload)
        db = original_connect(portable)
        try:
            assert db.execute("SELECT count(*) FROM auth_sessions").fetchone()[0] == 0
            assert db.execute("SELECT note FROM tasks").fetchone()[0] == "retain live business evidence"
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            db.close()
        assert target.read_bytes() == payload
        assert live.execute("SELECT count(*) FROM auth_sessions").fetchone()[0] == 1
    finally:
        for connection in connections:
            connection.close()
        live.close()
