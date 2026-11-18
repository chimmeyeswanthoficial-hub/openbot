"""Existing-schema opening is an explicit connection mode, not a migration fallback."""
from __future__ import annotations

import sqlite3

import pytest
from economic import EconomicError, EconomicUnavailable
from economic_repository import EconomicBook
from repository import Store


def test_existing_sqlite_store_opens_without_recreating_schema(tmp_path):
    path = tmp_path/'existing.db'
    setup = Store(str(path))
    setup.audit({'run_id': 'r_existing', 'decision': 'allow', 'rule': 'test.existing'})
    before = list(setup._conn.execute('SELECT type,name,sql FROM sqlite_master ORDER BY name'))
    before = [tuple(row) for row in before]
    setup._conn.close()
    runtime = Store(str(path), initialize=False)
    try:
        assert runtime.audit_count() == 1
        assert [tuple(row) for row in runtime._conn.execute('SELECT type,name,sql FROM sqlite_master ORDER BY name')] == before
    finally:
        runtime._conn.close()


def test_existing_sqlite_open_does_not_create_an_absent_file(tmp_path):
    missing = tmp_path/'not-created.db'
    with pytest.raises(sqlite3.OperationalError):
        Store(str(missing), initialize=False)
    assert not missing.exists()


@pytest.mark.parametrize('path', [':memory:', 'file:ambiguous.db?mode=rwc'])
def test_existing_mode_requires_an_unambiguous_plain_existing_sqlite_path(path):
    with pytest.raises(ValueError, match='existing_plain_sqlite_path_required'):
        Store(path, initialize=False)


@pytest.mark.parametrize('value', [None, 0, 1, 'false', []])
def test_store_initialization_flag_is_not_truthiness(tmp_path, value):
    missing = tmp_path/'not-created.db'
    with pytest.raises(ValueError, match='initialize_must_be_boolean'):
        Store(str(missing), initialize=value)
    assert not missing.exists()


@pytest.mark.parametrize('value', [None, 0, 1, 'false', []])
def test_economic_initialization_flag_is_not_truthiness(value):
    store = Store()
    try:
        with pytest.raises(EconomicError, match='initialize_must_be_boolean'):
            EconomicBook(store, experimental=True, initialize=value)
        assert not store._conn.in_transaction
        assert store._conn.execute("SELECT count(*) FROM sqlite_master WHERE name LIKE 'economic_v1_%'").fetchone()[0] == 0
    finally:
        store._conn.close()


def test_missing_canonical_schema_is_not_silently_created_in_existing_mode():
    store = Store()
    try:
        with pytest.raises(EconomicUnavailable) as error:
            EconomicBook(store, experimental=True, initialize=False)
        assert not error.value.uncertain
        assert not store._conn.in_transaction
        assert store._conn.execute("SELECT count(*) FROM sqlite_master WHERE name LIKE 'economic_v1_%'").fetchone()[0] == 0
        assert store.audit_count() == 0
    finally:
        store._conn.close()


@pytest.mark.parametrize('version', [None, 2])
def test_existing_canonical_schema_version_is_checked_not_repaired(version):
    store = Store()
    try:
        EconomicBook(store, experimental=True)
        if version is None:
            store._conn.execute('DELETE FROM economic_v1_schema')
        else:
            store._conn.execute('UPDATE economic_v1_schema SET version=?', (version,))
        store._conn.commit()
        with pytest.raises(EconomicError, match='unsupported_economic_schema'):
            EconomicBook(store, experimental=True, initialize=False)
        row = store._conn.execute('SELECT version FROM economic_v1_schema').fetchone()
        assert (None if row is None else row[0]) == version
    finally:
        store._conn.close()


def test_existing_book_never_commits_or_rolls_back_caller_transaction():
    store = Store()
    try:
        EconomicBook(store, experimental=True)
        store._conn.execute('BEGIN')
        store._conn.execute("INSERT INTO runs(id,routine_id,venture,started,status) VALUES('r_borrowed','routine','media-api','test','running')")
        with pytest.raises(EconomicError, match='existing_transaction_not_owned'):
            EconomicBook(store, experimental=True, initialize=False)
        assert store._conn.in_transaction
        assert store._conn.execute("SELECT count(*) FROM runs WHERE id='r_borrowed'").fetchone()[0] == 1
        store._conn.rollback()
        assert store._conn.execute("SELECT count(*) FROM runs WHERE id='r_borrowed'").fetchone()[0] == 0
    finally:
        store._conn.close()
