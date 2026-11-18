"""S04 wire parsing, durable offsets and real loopback HTTP/stop/meter evidence.

All usage is synthetic, not settled money or a live provider certification.
"""

from __future__ import annotations

import json
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from provider_fixture import serve_fixture
from provider_transport import FixtureTransport
from repository import Store
from sse_protocol import Correlator, SSEDecoder
from work_store import WorkError, WorkStore

RUN = "w_protocol"


def events(run=RUN):
    common = {"runId": run, "threadId": "thread_" + run}
    return [
        {"seq": index + 1, "type": kind, **common, **extra}
        for index, (kind, extra) in enumerate(
            [
                ("RUN_STARTED", {}),
                ("TEXT_MESSAGE_START", {"messageId": run + ":msg"}),
                ("TEXT_MESSAGE_CONTENT", {"messageId": run + ":msg", "delta": "Hello ₹ తెలుగు"}),
                ("TEXT_MESSAGE_END", {"messageId": run + ":msg"}),
                ("RUN_FINISHED", {}),
            ]
        )
    ]


def wire(rows):
    return b"".join(
        (
            "id: "
            + str(row["seq"])
            + "\ndata: "
            + json.dumps({k: v for k, v in row.items() if k != "seq"}, ensure_ascii=False)
            + "\n\n"
        ).encode()
        for row in rows
    )


def test_every_utf8_and_frame_split_preserves_actual_events():
    expected = events()
    data = wire(expected)
    for split in range(len(data) + 1):
        decoder = SSEDecoder()
        assert decoder.feed(data[:split]) + decoder.feed(data[split:]) == expected
        decoder.finish()
    decoder = SSEDecoder()
    actual = []
    for byte in data.replace(b"\n", b"\r\n"):
        actual += decoder.feed(bytes([byte]))
    decoder.finish()
    assert actual == expected


@pytest.mark.parametrize(
    "data",
    [
        b"id: 1\ndata: \xff\n\n",
        b"data: {}\n\n",
        b"id: 1\nid: 2\ndata: {}\n\n",
        b'id: 1\ndata: {"type":"RUN_STARTED","type":"RUN_FINISHED"}\n\n',
        b"id: 1\ndata: NaN\n\n",
        b"id: 1\ndata: {}\n\n",
        b"event: shell\ndata: {}\n\n",
        b"id: 0\ndata: {}\n\n",
    ],
)
def test_malformed_overspecified_or_uncorrelated_frames_refuse(data):
    with pytest.raises(WorkError):
        SSEDecoder().feed(data)


def test_partial_utf8_frame_and_deadline_are_not_a_success():
    d = SSEDecoder()
    d.feed(b"id: 1\ndata: " + b"\xe2")
    with pytest.raises(WorkError):
        d.finish()
    d = SSEDecoder()
    d.feed(b"id: 1\ndata: {")
    with pytest.raises(WorkError):
        d.finish()
    clock = [0.0]
    d = SSEDecoder(clock=lambda: clock[0], timeout_s=1)
    clock[0] = 2
    with pytest.raises(WorkError, match="deadline"):
        d.feed(b": heartbeat\n\n")


def test_frame_byte_and_event_counts_are_actually_bounded():
    with pytest.raises(WorkError, match="frame_limit"):
        d = SSEDecoder()
        for _ in range(40):
            d.feed(b"x" * 1024)
    with pytest.raises(WorkError, match="byte_limit"):
        d = SSEDecoder(max_bytes=20, max_frame=20)
        for _ in range(10):
            d.feed(b": hello\n\n")
    with pytest.raises(WorkError, match="too_many"):
        SSEDecoder(max_events=1).feed(wire(events()[:2]))


def test_duplicate_ids_must_match_and_ordered_children_must_close():
    tracker = Correlator(RUN)
    rows = events()
    assert tracker.accept(rows[0]) and not tracker.accept(rows[0])
    with pytest.raises(WorkError, match="conflict"):
        tracker.accept({**rows[0], "type": "RUN_FINISHED"})
    with pytest.raises(WorkError):
        tracker.accept(rows[2])
    for event in rows[1:]:
        assert tracker.accept(event)
    with pytest.raises(WorkError):
        tracker.accept({**rows[-1], "seq": 6})


def provider_task(b, key="provider"):
    row, _ = b.work.register(
        venture="demo",
        routine="provider-fixture",
        origin="manual",
        key=key,
        when=datetime(2026, 11, 10, tzinfo=UTC),
        initiator={"kind": "routine", "id": "owned-origin", "actor": "agent:qa"},
        plan={"tool": "local-provider-fixture", "prompt": "owned fixture only"},
        upper_minor=5,
    )
    assert b.work.reserve(row["id"])
    return row


@pytest.mark.parametrize("mode", ["normal", "duplicate"])
def test_real_stream_is_persisted_before_ui_and_reconciled_separately(durable_backend, mode):
    b = durable_backend
    row = provider_task(b)
    observed = []
    with serve_fixture(b.path / "provider.sqlite3", mode=mode) as fixture:
        transport = FixtureTransport(fixture.endpoint, fixture.token, fixture_mode=True)

        def after_commit(event):
            assert b.work.events(row["id"])[-1]["event"] == event
            observed.append(event)

        result = transport.run(b.work, row["id"], authorize=lambda *_: True, on_event=after_commit)
        assert result["status"] == "completed" and result["cost_settled"] is False
        assert len(observed) == 5 and len(b.work.events(row["id"], after=2)) == 3
        assert b.work.get(row["id"])["held_minor"] == 5
        usage = transport.reconcile(b.work, row["id"], authorize=lambda *_: True)
        assert usage["amount_minor"] == 2 and usage["money_settlement"] is False
        assert (
            b.work.get(row["id"])["spent_minor"] == 2 and b.work.get(row["id"])["held_minor"] == 0
        )
        assert not transport.run(b.work, row["id"], authorize=lambda *_: True)["provider_called"]
        assert fixture.row(row["id"])["accept_count"] == 1
        assert fixture.row(row["id"])["http_calls"] == 1


@pytest.mark.parametrize(
    "mode", ["gap", "bad_utf8", "oversize", "wrong_run", "drop", "accept_disconnect"]
)
def test_real_broken_wire_or_lost_acceptance_requires_reconciliation(durable_backend, mode):
    b = durable_backend
    row = provider_task(b)
    with serve_fixture(b.path / "provider.sqlite3", mode=mode) as fixture:
        t = FixtureTransport(fixture.endpoint, fixture.token, fixture_mode=True)
        result = t.run(b.work, row["id"], authorize=lambda *_: True)
        assert result["status"] == "uncertain" and not result["stop_confirmed"]
        assert b.work.get(row["id"])["held_minor"] == 5
        assert not t.run(b.work, row["id"], authorize=lambda *_: True)["provider_called"]
        assert fixture.row(row["id"])["accept_count"] == 1
        assert fixture.row(row["id"])["http_calls"] == 1


def test_gate_or_unavailable_audit_cannot_contact_provider(durable_backend):
    b = durable_backend
    row = provider_task(b)
    with serve_fixture(b.path / "provider.sqlite3") as fixture:
        t = FixtureTransport(fixture.endpoint, fixture.token, fixture_mode=True)
        result = t.run(b.work, row["id"], authorize=lambda *_: False)
        assert not result["provider_called"] and fixture.row(row["id"]) is None
        assert b.work.get(row["id"])["attempted"] == 0


@pytest.mark.parametrize("mode,confirmed", [("slow", True), ("unconfirmed_stop", False)])
def test_stop_is_reported_only_after_actual_fixture_ack(durable_backend, mode, confirmed):
    b = durable_backend
    row = provider_task(b)
    with serve_fixture(b.path / "provider.sqlite3", mode=mode) as fixture:
        t = FixtureTransport(fixture.endpoint, fixture.token, fixture_mode=True)
        with ThreadPoolExecutor(max_workers=1) as pool:
            running = pool.submit(t.run, b.work, row["id"], authorize=lambda *_: True)
            assert fixture.started.wait(3)
            stop = t.stop(b.work, row["id"], authorize=lambda *_: True)
            assert stop["stop_confirmed"] is confirmed
            running.result(timeout=5)
        assert b.work.get(row["id"])["held_minor"] == 5  # stopping is not usage reconciliation
        assert b.work.get(row["id"])["status"] == ("cancelled" if confirmed else "uncertain")
        t.reconcile(b.work, row["id"], authorize=lambda *_: True)
        assert b.work.get(row["id"])["spent_minor"] == 2


def _die_after_provider_acceptance(dsn, task_id, endpoint, token):
    s = Store(dsn, initialize=False)
    w = WorkStore(s)
    transport = FixtureTransport(endpoint, token, fixture_mode=True)
    transport.run(w, task_id, authorize=lambda *_: True, on_event=lambda _event: os._exit(82))


def test_client_process_death_after_remote_acceptance_never_redrives(durable_backend):
    b = durable_backend
    row = provider_task(b)
    with serve_fixture(b.path / "provider.sqlite3") as fixture:
        child = multiprocessing.get_context("spawn").Process(
            target=_die_after_provider_acceptance,
            args=(b.dsn, row["id"], fixture.endpoint, fixture.token),
        )
        child.start()
        try:
            child.join(timeout=15)
            assert child.exitcode == 82 and not child.is_alive()
            assert b.work.get(row["id"])["attempted"] == 1
            b.clock[0] += 40
            transport = FixtureTransport(fixture.endpoint, fixture.token, fixture_mode=True)
            assert not transport.run(b.work, row["id"], authorize=lambda *_: True)[
                "provider_called"
            ]
            assert b.work.get(row["id"])["status"] == "uncertain"
            assert fixture.row(row["id"])["accept_count"] == 1
            transport.reconcile(b.work, row["id"], authorize=lambda *_: True)
            assert b.work.get(row["id"])["spent_minor"] == 2
        finally:
            if child.is_alive():
                child.terminate()
                child.join(timeout=3)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://localhost:1234",
        "https://127.0.0.1:1234",
        "http://example.com",
        "http://127.0.0.1:1234/path",
        "http://user@127.0.0.1:1234",
    ],
)
def test_fixture_adapter_cannot_be_repurposed_as_live_or_arbitrary_egress(endpoint):
    with pytest.raises(WorkError):
        FixtureTransport(endpoint, "a" * 43, fixture_mode=True)
    with pytest.raises(WorkError):
        FixtureTransport("http://127.0.0.1:1234", "a" * 43)


def test_closed_tool_and_message_ids_cannot_be_reused_for_different_calls():
    for kind in ("message", "tool"):
        tracker = Correlator(RUN)
        tracker.accept(events()[0])
        if kind == "message":
            begin = {"type": "TEXT_MESSAGE_START", "messageId": RUN + ":one"}
            end = {"type": "TEXT_MESSAGE_END", "messageId": RUN + ":one"}
        else:
            begin = {
                "type": "TOOL_CALL_START",
                "toolCallId": RUN + ":one",
                "toolName": "owned.qa",
                "args": "{}",
            }
            end = {"type": "TOOL_CALL_END", "toolCallId": RUN + ":one"}
        base = {"runId": RUN, "threadId": "thread_" + RUN}
        tracker.accept({**base, **begin, "seq": 2})
        tracker.accept({**base, **end, "seq": 3})
        with pytest.raises(WorkError):
            tracker.accept({**base, **begin, "seq": 4})


def test_real_slow_trickle_cannot_hide_inside_transport_chunk_buffer(durable_backend):
    import time

    b = durable_backend
    row = provider_task(b)
    with serve_fixture(b.path / "trickle.sqlite3", mode="trickle") as fixture:
        transport = FixtureTransport(fixture.endpoint, fixture.token, fixture_mode=True)
        start = time.monotonic()
        result = transport.run(b.work, row["id"], authorize=lambda *_: True)
        elapsed = time.monotonic() - start
        assert result["status"] == "uncertain"
        assert elapsed < 5.5, (
            "total stream deadline must apply even to tiny continuously arriving packets"
        )
        assert b.work.get(row["id"])["held_minor"] == 5
        assert not transport.run(b.work, row["id"], authorize=lambda *_: True)["provider_called"]
        assert fixture.row(row["id"])["http_calls"] == 1


@pytest.mark.parametrize("bad_type", [None, [], {}, True, 23])
def test_non_string_event_types_are_contract_errors_not_python_type_errors(bad_type):
    from sse_protocol import validate_event

    with pytest.raises(WorkError):
        validate_event({**events()[0], "type": bad_type})


def test_long_numeric_sse_ids_are_bounded_before_integer_conversion():
    with pytest.raises(WorkError):
        SSEDecoder().feed(b"id: " + b"1" * 5000 + b"\ndata: {}\n\n")


@pytest.mark.parametrize("mode", ["oversize_receipt", "malformed_receipt"])
def test_actual_bad_usage_and_stop_receipts_do_not_release_liability_or_claim_a_stop(
    durable_backend, mode
):
    b = durable_backend
    row = provider_task(b)
    with serve_fixture(b.path / "receipts.sqlite3", mode=mode) as fixture:
        transport = FixtureTransport(fixture.endpoint, fixture.token, fixture_mode=True)
        assert transport.run(b.work, row["id"], authorize=lambda *_: True)["status"] == "completed"
        with pytest.raises(WorkError):
            transport.reconcile(b.work, row["id"], authorize=lambda *_: True)
        assert b.work.get(row["id"])["held_minor"] == 5
        assert not transport.stop(b.work, row["id"], authorize=lambda *_: True)["stop_confirmed"]
        assert b.work.get(row["id"])["held_minor"] == 5
        assert fixture.row(row["id"])["http_calls"] == 1
