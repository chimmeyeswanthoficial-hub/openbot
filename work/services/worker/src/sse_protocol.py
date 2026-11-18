"""Bounded incremental UTF-8/SSE + a narrow AG-UI event profile, not full AG-UI.

No event executes a tool. Persistence/correlation happens before UI notification.
Every enabled tool still needs the independent authenticated kernel boundary.
"""

from __future__ import annotations

import codecs
import json
import time

from policy import contains_secret
from work_store import WorkError, canonical, digest

PROFILE = {
    "RUN_STARTED": set(),
    "RUN_FINISHED": set(),
    "RUN_ERROR": {"message"},
    "TEXT_MESSAGE_START": {"messageId"},
    "TEXT_MESSAGE_CONTENT": {"messageId", "delta"},
    "TEXT_MESSAGE_END": {"messageId"},
    "TOOL_CALL_START": {"toolCallId", "toolName", "args"},
    "TOOL_CALL_END": {"toolCallId"},
}


def validate_event(event, run_id=None):
    if (
        not isinstance(event, dict)
        or not isinstance(event.get("type"), str)
        or event.get("type") not in PROFILE
    ):
        raise WorkError("unsupported_stream_event")
    required = {"type", "runId", "threadId", "seq"} | PROFILE[event["type"]]
    if set(event) != required or type(event["seq"]) is not int or not 1 <= event["seq"] <= 1000000:
        raise WorkError("invalid_stream_fields")
    if (
        not isinstance(event["runId"], str)
        or not event["runId"]
        or event["threadId"] != "thread_" + event["runId"]
        or (run_id is not None and event["runId"] != run_id)
    ):
        raise WorkError("uncorrelated_stream")
    for key, value in event.items():
        if key == "seq":
            continue
        if (
            not isinstance(value, str)
            or len(value.encode()) > 16384
            or "\x00" in value
            or contains_secret(value)
        ):
            raise WorkError("unsafe_stream_value")
    for key in ("toolCallId", "messageId"):
        if key in event and not event[key].startswith(event["runId"] + ":"):
            raise WorkError("uncorrelated_stream_child")
    return event


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise WorkError("duplicate_json_key")
        out[key] = value
    return out


class SSEDecoder:
    def __init__(
        self,
        *,
        max_bytes=131072,
        max_frame=32768,
        max_events=128,
        timeout_s=3,
        clock=time.monotonic,
    ):
        if (
            any(type(n) is not int or n <= 0 for n in (max_bytes, max_frame, max_events))
            or max_frame > max_bytes
            or not 0 < timeout_s <= 30
        ):
            raise WorkError("invalid_stream_bounds")
        self.max_bytes, self.max_frame, self.max_events = max_bytes, max_frame, max_events
        self.clock, self.deadline = clock, clock() + timeout_s
        self.decoder = codecs.getincrementaldecoder("utf-8")("strict")
        self.total, self.frame_size, self.frames = 0, 0, 0
        self.line, self.data, self.frame_id = "", [], None
        self.skip_lf = False
        self.closed = False

    def _line(self):
        line, self.line = self.line, ""
        if not line:
            if not self.data:
                self.frame_id = None
                self.frame_size = 0
                return None
            if self.frame_id is None:
                raise WorkError("durable_event_id_required")
            try:
                value = json.loads(
                    "\n".join(self.data),
                    object_pairs_hook=unique_object,
                    parse_constant=lambda _x: (_ for _ in ()).throw(WorkError("nonfinite_json")),
                )
            except (ValueError, UnicodeError) as exc:
                raise WorkError("invalid_stream_json") from exc
            if not isinstance(value, dict) or ("seq" in value and value["seq"] != self.frame_id):
                raise WorkError("conflicting_stream_id")
            value["seq"] = self.frame_id
            validate_event(value)
            self.frames += 1
            if self.frames > self.max_events:
                raise WorkError("too_many_stream_events")
            self.data, self.frame_id, self.frame_size = [], None, 0
            return value
        if line.startswith(":"):
            return None
        field, sep, value = line.partition(":")
        if not sep:
            raise WorkError("invalid_sse_field")
        value = value[1:] if value.startswith(" ") else value
        if field == "data":
            self.data.append(value)
        elif (
            field == "id"
            and self.frame_id is None
            and len(value) <= 7
            and value.isascii()
            and value.isdigit()
            and 1 <= int(value) <= 1000000
        ):
            self.frame_id = int(value)
        else:
            raise WorkError("unsupported_or_duplicate_sse_field")
        return None

    def feed(self, chunk):
        if self.closed or not isinstance(chunk, bytes) or len(chunk) > 8192:
            raise WorkError("invalid_stream_chunk")
        if self.clock() >= self.deadline:
            raise WorkError("stream_deadline")
        self.total += len(chunk)
        if self.total > self.max_bytes:
            raise WorkError("stream_byte_limit")
        try:
            text = self.decoder.decode(chunk)
        except UnicodeError as exc:
            raise WorkError("invalid_stream_utf8") from exc
        output = []
        for character in text:
            if self.skip_lf:
                self.skip_lf = False
                if character == "\n":
                    continue
            self.frame_size += len(character.encode())
            if self.frame_size > self.max_frame:
                raise WorkError("stream_frame_limit")
            if character in "\r\n":
                self.skip_lf = character == "\r"
                value = self._line()
                if value is not None:
                    output.append(value)
            else:
                self.line += character
        return output

    def finish(self):
        try:
            self.decoder.decode(b"", final=True)
        except UnicodeError as exc:
            raise WorkError("truncated_stream_utf8") from exc
        if self.line or self.data or self.frame_id is not None:
            raise WorkError("partial_stream_frame")
        if self.clock() >= self.deadline:
            raise WorkError("stream_deadline")
        self.closed = True


class Correlator:
    def __init__(self, run_id):
        self.run_id = run_id
        self.seen = {}
        self.started, self.finished = False, False
        self.message = None
        self.tools, self.tool_ids, self.message_ids = set(), set(), set()
        self.text = ""

    def accept(self, event):
        validate_event(event, self.run_id)
        seq = event["seq"]
        sha = digest(event)
        if seq in self.seen:
            if self.seen[seq] != sha:
                raise WorkError("stream_replay_conflict")
            return False
        if seq != len(self.seen) + 1 or self.finished:
            raise WorkError("stream_order_or_terminal_conflict")
        kind = event["type"]
        if not self.started:
            if kind != "RUN_STARTED":
                raise WorkError("stream_start_required")
            self.started = True
        elif kind == "RUN_STARTED":
            raise WorkError("duplicate_stream_start")
        if kind == "TEXT_MESSAGE_START":
            if self.message is not None or event["messageId"] in self.message_ids:
                raise WorkError("message_already_open_or_id_reused")
            self.message = event["messageId"]
            self.message_ids.add(event["messageId"])
        elif kind in {"TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END"}:
            if event["messageId"] != self.message:
                raise WorkError("message_not_open")
            if kind == "TEXT_MESSAGE_END":
                self.message = None
            else:
                self.text += event["delta"]
                if len(self.text.encode()) > 32768:
                    raise WorkError("message_byte_limit")
        elif kind == "TOOL_CALL_START":
            if event["toolCallId"] in self.tool_ids:
                raise WorkError("duplicate_tool_call")
            self.tools.add(event["toolCallId"])
            self.tool_ids.add(event["toolCallId"])
        elif kind == "TOOL_CALL_END":
            if event["toolCallId"] not in self.tools:
                raise WorkError("tool_not_open")
            self.tools.remove(event["toolCallId"])
        elif kind in {"RUN_FINISHED", "RUN_ERROR"}:
            if self.message is not None or self.tools:
                raise WorkError("unfinished_stream_children")
            self.finished = True
        self.seen[seq] = sha
        return True


def encode_event(event):
    validate_event(event)
    body = dict(event)
    seq = body.pop("seq")
    return ("id: " + str(seq) + "\ndata: " + canonical(body) + "\n\n").encode()
