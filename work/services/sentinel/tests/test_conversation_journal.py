"""Real disposable SQLite checks for the inert OpenBot OS conversation journal.

No production DB/environment, provider, network, external tool or HTTP auth is
used. Owner-scoped query tests do NOT establish end-to-end tenant authentication.
"""

import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import conversation_journal as module
from conversation_journal import ConversationJournal, JournalError, JournalUnavailable, Scope

OWNER = Scope("org-a", "owner-a")
OTHER_USER = Scope("org-a", "owner-b")
OTHER_TENANT = Scope("org-b", "owner-a")


class ConversationJournalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "private-conversations.sqlite"
        self.path.touch(mode=0o600)
        self.connections = []
        self.journal = self.open(initialize=True)
        self.journal.create_thread(OWNER, "thread-a", title="Owned conversation")

    def tearDown(self):
        for connection in self.connections:
            connection.close()
        self.directory.cleanup()

    def open(self, *, initialize=False):
        connection = sqlite3.connect(self.path, isolation_level=None, timeout=2)
        self.connections.append(connection)
        return ConversationJournal(connection, initialize=initialize)

    def append(self, *, event_id="event-1", expected=0, event=None, journal=None):
        return (journal or self.journal).append(
            OWNER,
            "thread-a",
            event_id=event_id,
            event={"type": "TEXT_MESSAGE_CONTENT", "delta": "hello"} if event is None else event,
            expected_sequence=expected,
        )

    def test_explicit_initialization_required_on_empty_connection(self):
        with sqlite3.connect(":memory:", isolation_level=None) as connection:
            with self.assertRaisesRegex(JournalError, "existing_schema_required"):
                ConversationJournal(connection)
            ConversationJournal(connection, initialize=True)

    def test_dedicated_autocommit_connection_and_boolean_setup_required(self):
        with (
            sqlite3.connect(":memory:") as connection,
            self.assertRaisesRegex(JournalError, "autocommit"),
        ):
            ConversationJournal(connection, initialize=True)
        with self.assertRaises(JournalError):
            ConversationJournal(object(), initialize=True)
        with self.assertRaises(JournalError):
            ConversationJournal(self.connections[0], initialize=1)

    def test_unrelated_existing_database_is_not_migrated(self):
        with sqlite3.connect(":memory:", isolation_level=None) as connection:
            connection.execute("CREATE TABLE precious(value TEXT)")
            connection.execute("INSERT INTO precious VALUES('retained')")
            with self.assertRaisesRegex(JournalError, "incompatible"):
                ConversationJournal(connection, initialize=True)
            self.assertEqual(
                connection.execute("SELECT * FROM precious").fetchall(), [("retained",)]
            )
            self.assertEqual(
                len(
                    connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                ),
                1,
            )

    def test_unknown_schema_version_is_refused_without_rewriting(self):
        self.connections[0].execute("UPDATE os_conversation_v1_schema SET version=999")
        with self.assertRaisesRegex(JournalError, "incompatible_schema_version"):
            self.open(initialize=True)
        self.assertEqual(
            self.connections[0]
            .execute("SELECT version FROM os_conversation_v1_schema")
            .fetchone()[0],
            999,
        )

    def test_scope_requires_explicit_valid_tenant_and_principal(self):
        for value in ["", "../bad", "space user", "x" * 129, "a\x00b", 7, True]:
            with self.subTest(value=value), self.assertRaises(JournalError):
                Scope(value, "owner")
        with self.assertRaisesRegex(JournalError, "authenticated_scope_required"):
            self.journal.list_threads({"tenant": "org-a", "principal": "owner-a"})

    def test_thread_create_retry_is_idempotent_and_conflicting_title_refused(self):
        self.assertEqual(
            self.journal.create_thread(OWNER, "thread-a", title="Owned conversation"), "thread-a"
        )
        with self.assertRaisesRegex(JournalError, "thread_identity_conflict"):
            self.journal.create_thread(OWNER, "thread-a", title="Different")
        self.assertEqual(len(self.journal.list_threads(OWNER)["threads"]), 1)

    def test_invalid_titles_and_identifiers_refused(self):
        for title in ["a" * 201, "bad\x00title", "\ud800", 1]:
            with self.subTest(title=repr(title)), self.assertRaises(JournalError):
                self.journal.create_thread(OWNER, "new-thread", title=title)
        with self.assertRaises(JournalError):
            self.journal.create_thread(OWNER, "../escape")

    def test_scoped_reads_appends_deletes_and_missing_ids_are_indistinguishable(self):
        self.append()
        for scope in [OTHER_USER, OTHER_TENANT]:
            with self.subTest(scope=scope):
                self.assertEqual(self.journal.list_threads(scope)["threads"], [])
                for operation in [
                    lambda scope=scope: self.journal.read_events(scope, "thread-a"),
                    lambda scope=scope: self.journal.append(
                        scope,
                        "thread-a",
                        event_id="new",
                        event={"type": "RUN_STARTED"},
                        expected_sequence=0,
                    ),
                    lambda scope=scope: self.journal.delete_thread(scope, "thread-a"),
                ]:
                    with self.assertRaisesRegex(JournalError, "^thread_not_found$"):
                        operation()
        self.assertEqual(self.journal.read_events(OWNER, "thread-a")["head_sequence"], 1)
        with self.assertRaisesRegex(JournalError, "^thread_not_found$"):
            self.journal.read_events(OWNER, "genuinely-missing")

    def test_same_ids_in_different_scopes_do_not_collide(self):
        for scope in [OWNER, OTHER_USER, OTHER_TENANT]:
            if scope != OWNER:
                self.journal.create_thread(scope, "thread-a")
            self.journal.append(
                scope,
                "thread-a",
                event_id="event-1",
                event={"type": "CUSTOM", "owner": scope.principal + scope.tenant},
                expected_sequence=0,
            )
        for scope in [OWNER, OTHER_USER, OTHER_TENANT]:
            events = self.journal.read_events(scope, "thread-a")["events"]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["event"]["owner"], scope.principal + scope.tenant)

    def test_append_and_replay_are_ordered_and_unicode_survives(self):
        self.append(event={"type": "RUN_STARTED", "threadId": "thread-a"})
        self.append(
            event_id="event-2",
            expected=1,
            event={"type": "TEXT_MESSAGE_CONTENT", "delta": "\u0c05\U0001f642"},
        )
        result = self.journal.read_events(OWNER, "thread-a")
        self.assertEqual([row["sequence"] for row in result["events"]], [1, 2])
        self.assertEqual(result["events"][1]["event"]["delta"], "\u0c05\U0001f642")
        self.assertIsNone(result["next_after"])
        self.assertEqual(result["head_sequence"], 2)

    def test_same_event_retry_does_not_duplicate_even_after_later_events(self):
        self.assertEqual(self.append(), 1)
        self.append(event_id="event-2", expected=1)
        self.assertEqual(self.append(), 1)
        self.assertEqual(self.journal.read_events(OWNER, "thread-a")["head_sequence"], 2)

    def test_canonical_key_order_supports_identical_retry(self):
        self.append(event={"type": "CUSTOM", "b": 2, "a": 1})
        self.assertEqual(self.append(event={"a": 1, "b": 2, "type": "CUSTOM"}), 1)

    def test_conflicting_event_id_content_or_precondition_rejected(self):
        self.append()
        for kwargs in [{"event": {"type": "CUSTOM"}}, {"expected": 1}]:
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaisesRegex(JournalError, "event_identity_conflict"),
            ):
                self.append(**kwargs)
        self.assertEqual(len(self.journal.read_events(OWNER, "thread-a")["events"]), 1)

    def test_stale_or_ahead_expected_sequence_rejected_without_append(self):
        self.append()
        for previous in [0, 2]:
            with self.assertRaisesRegex(JournalError, "stale_sequence"):
                self.append(event_id="different-event", expected=previous)
        self.assertEqual(self.journal.read_events(OWNER, "thread-a")["head_sequence"], 1)

    def test_conflicting_payload_thread_id_is_rejected(self):
        with self.assertRaisesRegex(JournalError, "thread_correlation_conflict"):
            self.append(event={"type": "RUN_STARTED", "threadId": "someone-elses-thread"})

    def test_non_json_nonfinite_and_unsafe_integer_values_rejected(self):
        for value in [float("nan"), float("inf"), 2**53, {1, 2}, (1, 2), object()]:
            with self.subTest(value=repr(value)), self.assertRaises(JournalError):
                self.append(event={"type": "CUSTOM", "value": value})
        for event in [[], {"type": "lowercase"}, {"type": 1}, {"type": "CUSTOM", 1: "coerced-key"}]:
            with self.subTest(event=repr(event)), self.assertRaises(JournalError):
                self.append(event=event)
        self.assertEqual(self.journal.read_events(OWNER, "thread-a")["events"], [])

    def test_event_size_utf8_surrogate_and_nesting_limits(self):
        for value in ["x" * 32768, "\u0c05" * 12000, "\ud800"]:
            with self.subTest(value_length=len(value)), self.assertRaises(JournalError):
                self.append(event={"type": "CUSTOM", "value": value})
        nested = []
        nested.append(nested)
        with self.assertRaisesRegex(JournalError, "complexity_limit"):
            self.append(event={"type": "CUSTOM", "value": nested})
        with self.assertRaisesRegex(JournalError, "complexity_limit"):
            self.append(event={"type": "CUSTOM", "value": [0] * 257})

    def test_boolean_negative_and_oversize_bounds_are_not_integer_cursors(self):
        for bound in [True, -1, 1.5, 4097]:
            with self.subTest(bound=bound), self.assertRaises(JournalError):
                self.journal.read_events(OWNER, "thread-a", after=bound)
        for limit in [True, 0, 101, 1.5]:
            with self.subTest(limit=limit), self.assertRaises(JournalError):
                self.journal.read_events(OWNER, "thread-a", limit=limit)
        with self.assertRaises(JournalError):
            self.append(expected=True)

    def test_thread_listing_uses_owner_scoped_keyset_pages(self):
        self.journal.create_thread(OWNER, "thread-b")
        self.journal.create_thread(OWNER, "thread-c")
        first = self.journal.list_threads(OWNER, limit=2)
        self.assertEqual([t["thread_id"] for t in first["threads"]], ["thread-a", "thread-b"])
        self.assertEqual(first["next_after"], "thread-b")
        second = self.journal.list_threads(OWNER, after=first["next_after"], limit=2)
        self.assertEqual([t["thread_id"] for t in second["threads"]], ["thread-c"])
        self.assertIsNone(second["next_after"])

    def test_event_pagination_and_resume_do_not_repeat_committed_events(self):
        for n in range(5):
            self.append(event_id=f"event-{n}", expected=n)
        cursor, seen = 0, []
        while True:
            page = self.journal.read_events(OWNER, "thread-a", after=cursor, limit=2)
            seen.extend(row["sequence"] for row in page["events"])
            if page["next_after"] is None:
                break
            cursor = page["next_after"]
        self.assertEqual(seen, [1, 2, 3, 4, 5])
        self.assertEqual(self.journal.read_events(OWNER, "thread-a", after=5)["events"], [])
        with self.assertRaisesRegex(JournalError, "cursor_ahead_of_thread"):
            self.journal.read_events(OWNER, "thread-a", after=6)

    def test_event_page_enforces_payload_bytes_not_only_row_count(self):
        for n in range(6):
            self.append(
                event_id=f"event-{n}", expected=n, event={"type": "CUSTOM", "delta": "x" * 30000}
            )
        page = self.journal.read_events(OWNER, "thread-a", limit=100)
        self.assertEqual(len(page["events"]), 4)
        self.assertLessEqual(page["payload_bytes"], 131072)
        self.assertEqual(page["next_after"], 4)
        self.assertEqual(len(self.journal.read_events(OWNER, "thread-a", after=4)["events"]), 2)

    def test_thread_count_quotas_are_transactional(self):
        with (
            patch.object(module, "MAX_THREADS_PER_SCOPE", 1),
            self.assertRaisesRegex(JournalError, "thread_count_limit"),
        ):
            self.journal.create_thread(OWNER, "another")
        with (
            patch.object(module, "MAX_THREADS_TOTAL", 1),
            self.assertRaisesRegex(JournalError, "thread_count_limit"),
        ):
            self.journal.create_thread(OTHER_TENANT, "another")

    def test_event_thread_and_global_payload_quotas_do_not_leave_partial_rows(self):
        for name, cap in [
            ("MAX_EVENTS_PER_THREAD", 0),
            ("MAX_THREAD_BYTES", 1),
            ("MAX_TOTAL_BYTES", 1),
        ]:
            with (
                self.subTest(quota=name),
                patch.object(module, name, cap),
                self.assertRaisesRegex(JournalError, "capacity_limit"),
            ):
                self.append()
            self.assertEqual(self.journal.read_events(OWNER, "thread-a")["head_sequence"], 0)
        self.assertEqual(self.append(), 1)

    def test_triggered_storage_failure_rolls_back_event_and_counter_together(self):
        db = self.connections[0]
        db.execute(
            "CREATE TRIGGER fail_update BEFORE UPDATE ON os_conversation_v1_threads BEGIN SELECT RAISE(ABORT,'synthetic failure'); END"
        )
        with self.assertRaisesRegex(JournalUnavailable, "^conversation_storage_unavailable$"):
            self.append()
        self.assertFalse(db.in_transaction)
        self.assertEqual(self.journal.read_events(OWNER, "thread-a")["events"], [])
        db.execute("DROP TRIGGER fail_update")
        self.assertEqual(self.append(), 1)

    def test_foreign_transaction_is_not_committed_or_rolled_back(self):
        db = self.connections[0]
        db.execute("BEGIN")
        with self.assertRaisesRegex(JournalError, "foreign_transaction_active"):
            self.append()
        self.assertTrue(db.in_transaction)
        db.rollback()
        self.assertEqual(self.append(), 1)

    def test_two_connections_racing_one_sequence_have_one_winner(self):
        barrier = threading.Barrier(2)

        def writer(n):
            connection = sqlite3.connect(self.path, isolation_level=None, timeout=2)
            try:
                journal = ConversationJournal(connection)
                barrier.wait(timeout=3)
                try:
                    return journal.append(
                        OWNER,
                        "thread-a",
                        event_id=f"race-{n}",
                        event={"type": "CUSTOM", "writer": n},
                        expected_sequence=0,
                    )
                except JournalError as exc:
                    return str(exc)
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(writer, [1, 2]))
        self.assertCountEqual(results, [1, "stale_sequence"])
        self.assertEqual(self.journal.read_events(OWNER, "thread-a")["head_sequence"], 1)

    def test_reopen_existing_file_preserves_committed_events(self):
        self.append()
        self.connections[0].close()
        reopened = self.open()
        self.assertEqual(
            reopened.read_events(OWNER, "thread-a")["events"][0]["event"]["delta"], "hello"
        )
        self.assertEqual(self.append(journal=reopened), 1)

    def test_real_child_process_commit_survives_abrupt_process_exit(self):
        source = Path(module.__file__).resolve().parent
        script = """
import os, sqlite3, sys
from conversation_journal import ConversationJournal, Scope
connection = sqlite3.connect(sys.argv[1], isolation_level=None)
journal = ConversationJournal(connection)
journal.append(Scope('org-a','owner-a'),'thread-a',event_id='child',event={'type':'CUSTOM','value':'committed'},expected_sequence=0)
os._exit(0)
"""
        run = subprocess.run(
            [sys.executable, "-c", script, str(self.path)],
            env={**os.environ, "PYTHONPATH": str(source)},
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(run.returncode, 0, run.stderr.decode())
        self.assertEqual(
            self.open().read_events(OWNER, "thread-a")["events"][0]["event"]["value"], "committed"
        )

    def test_deletion_cascades_only_owned_history_and_frees_logical_quota(self):
        self.append()
        self.journal.create_thread(OTHER_USER, "thread-a")
        self.journal.append(
            OTHER_USER,
            "thread-a",
            event_id="event-1",
            event={"type": "CUSTOM"},
            expected_sequence=0,
        )
        self.journal.delete_thread(OWNER, "thread-a")
        with self.assertRaisesRegex(JournalError, "thread_not_found"):
            self.journal.read_events(OWNER, "thread-a")
        self.assertEqual(len(self.journal.read_events(OTHER_USER, "thread-a")["events"]), 1)
        rows = (
            self.connections[0]
            .execute(
                "SELECT COUNT(*) FROM os_conversation_v1_events WHERE tenant='org-a' AND principal='owner-a'"
            )
            .fetchone()[0]
        )
        self.assertEqual(rows, 0)

    def test_accidental_payload_mutation_is_detected_not_silently_replayed(self):
        self.append()
        self.connections[0].execute("UPDATE os_conversation_v1_events SET payload='{}'")
        with self.assertRaisesRegex(JournalError, "stored_event_integrity_error"):
            self.journal.read_events(OWNER, "thread-a")

    def test_tool_named_events_are_inert_json_not_execution(self):
        event = {"type": "TOOL_CALL_START", "toolName": "shell", "args": "do-not-run"}
        self.append(event=event)
        self.assertEqual(self.journal.read_events(OWNER, "thread-a")["events"][0]["event"], event)
        event["args"] = "changed outside store"
        self.assertEqual(
            self.journal.read_events(OWNER, "thread-a")["events"][0]["event"]["args"], "do-not-run"
        )


if __name__ == "__main__":
    unittest.main()
