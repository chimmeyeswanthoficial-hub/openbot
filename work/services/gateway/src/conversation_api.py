"""Opt-in human history over the existing signed-device gateway, MIT.

This is storage, not a chat/agent/tool runner. Only trusted host setup can supply
an already initialized dedicated ConversationJournal. No files, migrations,
network calls, model, SDK, telemetry or production state are opened here.

The gateway derives the principal/venture from its locked authenticated session;
JSON may never select them. Client input becomes an inert, application-namespaced
AG-UI CUSTOM event, never an assistant/system/tool instruction or approval.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3

from conversation_journal import ConversationJournal, JournalError, JournalUnavailable, Scope
from policy import contains_secret

PREFIX = "/api/v1/conversations"
THREAD_ID = r"c[a-f0-9]{32}"
MESSAGE_ID = r"m[a-f0-9]{32}"
MAX_TEXT_BYTES = 8192
MAX_RESPONSE_BYTES = 196608
HISTORY_SCOPES = frozenset({"history-read", "history-write", "history-delete"})


class HistoryError(ValueError):
    def __init__(self, code="history_contract_refused", status=422):
        super().__init__(code)
        self.code, self.status = code, status


def strict_json(raw):
    """Reject duplicate keys, non-JSON numeric constants and excessive nesting."""

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("non_json_number")

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("strict_json_required") from exc


def history_route(path):
    if path in {PREFIX + "/create", PREFIX + "/list"}:
        return path.rsplit("/", 1)[1], None
    match = re.fullmatch(PREFIX + "/(" + THREAD_ID + ")/(read|messages|delete)", path)
    return (match[2], match[1]) if match else None


def required_scope(path):
    route = history_route(path)
    if route is None:
        raise HistoryError("history_route_not_found", 404)
    return {
        "list": "history-read",
        "read": "history-read",
        "create": "history-write",
        "messages": "history-write",
        "delete": "history-delete",
    }[route[0]]


def _exact(value, fields):
    if type(value) is not dict or set(value) != set(fields):
        raise HistoryError("exact_history_fields_required")


def _identifier(value, pattern):
    if type(value) is not str or re.fullmatch(pattern, value) is None:
        raise HistoryError("invalid_history_identifier")
    return value


def _text(value, *, title=False):
    if type(value) is not str or any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise HistoryError("invalid_history_text")
    if (not title and not value.strip()) or (title and len(value) > 200):
        raise HistoryError("invalid_history_text")
    try:
        size = len(value.encode("utf-8", errors="strict"))
    except UnicodeError as exc:
        raise HistoryError("invalid_history_text") from exc
    if size > (800 if title else MAX_TEXT_BYTES):
        raise HistoryError("history_text_byte_limit", 413)
    if contains_secret(value):
        # A few known credential patterns, NOT comprehensive DLP or sanitization.
        # Refuse rather than silently change the content of an idempotent retry.
        raise HistoryError("credential_like_history_content_refused")
    return value


class ConversationAPI:
    """Pure history operations; call ONLY from the gateway's locked auth boundary.

    A custom event validating against AG-UI's schema does not establish full
    lifecycle/stream/runner interoperability. Idempotency is within one existing
    thread lifecycle; after deleting a thread clients must choose a fresh ID.
    Deletion is logical history deletion, never secure erase or audit deletion.
    """

    def __init__(self, journal):
        if type(journal) is not ConversationJournal:
            raise HistoryError("explicit_conversation_journal_required", 503)
        self.journal = journal

    def dispatch(self, server_id, session, path, raw):
        route = history_route(path)
        if route is None:
            raise HistoryError("history_route_not_found", 404)
        action, thread_id = route
        if required_scope(path) != "history-read" and (
            session["role"] != "owner" or not session["actor"].startswith("human:")
        ):
            raise HistoryError("human_history_write_required", 403)
        # Include both gateway identity and venture, without accepting scope JSON.
        tenant = (
            "gw-"
            + hashlib.sha256((server_id + "\n" + session["venture"]).encode("utf-8")).hexdigest()
        )
        scope = Scope(tenant, session["actor"])
        try:
            value = strict_json(raw)
        except ValueError as exc:
            raise HistoryError("strict_json_required") from exc
        try:
            if action == "create":
                _exact(value, {"thread_id", "title"})
                thread_id = _identifier(value["thread_id"], THREAD_ID)
                self.journal.create_thread(
                    scope, thread_id, title=_text(value["title"], title=True)
                )
                data = {"thread_id": thread_id}
            elif action == "list":
                _exact(value, {"after", "limit"})
                if value["after"] != "":
                    _identifier(value["after"], THREAD_ID)
                data = self.journal.list_threads(scope, after=value["after"], limit=value["limit"])
            elif action == "read":
                _exact(value, {"after", "limit"})
                data = self.journal.read_events(
                    scope, thread_id, after=value["after"], limit=value["limit"]
                )
            elif action == "messages":
                _exact(value, {"message_id", "text", "expected_sequence"})
                message_id = _identifier(value["message_id"], MESSAGE_ID)
                # No client-selected event type, role, author, tool or permission.
                event = {
                    "type": "CUSTOM",
                    "name": "openbot.user_message.v1",
                    "value": {
                        "thread_id": thread_id,
                        "message_id": message_id,
                        "role": "user",
                        "author": session["actor"],
                        "text": _text(value["text"]),
                        "source": "authenticated_human_input",
                    },
                }
                sequence = self.journal.append(
                    scope,
                    thread_id,
                    event_id=message_id,
                    event=event,
                    expected_sequence=value["expected_sequence"],
                )
                data = {"thread_id": thread_id, "message_id": message_id, "sequence": sequence}
            else:
                _exact(value, set())
                self.journal.delete_thread(scope, thread_id)
                data = {"thread_id": thread_id, "deleted": True, "secure_erasure": False}
        except JournalError as exc:
            code = str(exc)
            status = 422
            if code == "thread_not_found":
                status = 404
            elif code in {"thread_identity_conflict", "event_identity_conflict", "stale_sequence"}:
                status = 409
            elif code.endswith("limit"):
                status = 413
            raise HistoryError(code, status) from exc
        except (JournalUnavailable, sqlite3.Error) as exc:
            raise HistoryError("conversation_storage_unavailable", 503) from exc
        result = {
            "history_api_version": "1",
            "history_only": True,
            "agent_executed": False,
            "source": "application_sqlite_journal",
            **data,
        }
        if (
            len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode())
            > MAX_RESPONSE_BYTES
        ):
            raise HistoryError("bounded_history_response_exceeded", 503)
        return result
