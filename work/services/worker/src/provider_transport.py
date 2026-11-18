"""Explicit local-fixture transport contract, not a live AG-UI/provider adapter.

Real HTTP streaming to one host-configured literal loopback address only. A call
requires durable reservation, claim/fence and pre-effect audit; no automatic new
attempt after ambiguous acceptance. Stream cost/text is never usage authority.
"""

from __future__ import annotations

import json
import re
import time
from urllib.parse import urlsplit

import httpx
from sse_protocol import Correlator, SSEDecoder, unique_object
from work_store import WorkError, digest


class FixtureTransport:
    def __init__(self, endpoint, token, *, fixture_mode=False):
        address = urlsplit(endpoint)
        if (
            fixture_mode is not True
            or address.scheme != "http"
            or address.hostname != "127.0.0.1"
            or not address.port
            or address.path
            or address.query
            or address.fragment
            or address.username
            or address.password
            or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token)
        ):
            raise WorkError("explicit_literal_loopback_fixture_required")
        self.endpoint, self.token = endpoint, token

    def _client(self):
        return httpx.Client(
            base_url=self.endpoint,
            headers={"Authorization": "Bearer " + self.token},
            timeout=httpx.Timeout(2, connect=1, read=2, write=1, pool=1),
            follow_redirects=False,
            trust_env=False,
        )

    def _json_request(self, method, path):
        """Bound receipts while READING, not after an unbounded response.read()."""
        with self._client() as client, client.stream(method, path) as response:
            if (
                response.status_code != 200
                or response.headers.get("content-type") != "application/json"
                or response.headers.get("content-encoding", "identity") != "identity"
            ):
                raise WorkError("invalid_fixture_receipt_response")
            length = response.headers.get("content-length")
            if length is not None and (
                not length.isascii()
                or not length.isdigit()
                or len(length) > 5
                or int(length) > 8192
            ):
                raise WorkError("fixture_receipt_byte_limit")
            data, deadline = bytearray(), time.monotonic() + 3
            for chunk in response.iter_raw():
                if time.monotonic() >= deadline or len(data) + len(chunk) > 8192:
                    raise WorkError("fixture_receipt_byte_or_time_limit")
                data.extend(chunk)
            return json.loads(
                data,
                object_pairs_hook=unique_object,
                parse_constant=lambda _x: (_ for _ in ()).throw(WorkError("nonfinite_receipt")),
            )

    @staticmethod
    def payload(row):
        return {
            "id": row["id"],
            "upper_minor": row["upper_minor"],
            "prompt": row["plan"].get("prompt", "owned-fixture"),
        }

    def run(self, work, task_id, *, authorize, on_event=lambda _event: None):
        row = work.get(task_id)
        if row is None:
            raise WorkError("unknown_run")
        fence = work.claim(task_id, "local-provider-fixture", lease=30)
        if fence is None:
            return {
                "status": work.get(task_id)["status"],
                "replayed": True,
                "provider_called": False,
            }
        if not work.before_effect(task_id, fence, row["spec_digest"], authorize=authorize):
            return {"status": work.get(task_id)["status"], "provider_called": False}
        decoder, correlator = SSEDecoder(), Correlator(task_id)
        last = None
        try:
            with (
                self._client() as client,
                client.stream(
                    "POST", "/turn", json=self.payload(row), headers={"Idempotency-Key": task_id}
                ) as response,
            ):
                if (
                    response.status_code != 200
                    or response.headers.get("content-type") != "text/event-stream"
                    or response.headers.get("content-encoding", "identity") != "identity"
                ):
                    raise WorkError("provider_not_accepted_as_stream")
                # No fixed-size buffering: one-byte trickles must reach the deadline
                # check immediately. The socket read itself also has a 2s idle bound.
                for raw in response.iter_raw():
                    for start in range(0, len(raw), 8192):
                        for event in decoder.feed(raw[start : start + 8192]):
                            if correlator.accept(event) and work.append_event(task_id, event):
                                on_event(event)  # only AFTER durable correlated storage
                            last = event
                decoder.finish()
                if not correlator.finished or not last or last["type"] != "RUN_FINISHED":
                    raise WorkError("no_provider_completion")
            finished = work.finish(
                task_id,
                fence,
                "completed",
                {
                    "provider": "local_fixture",
                    "text": correlator.text,
                    "usage_basis": "unreconciled",
                    "stop_confirmed": False,
                    "synthetic_fixture": True,
                },
            )
            if not finished:
                raise WorkError("stale_provider_result")
        except Exception:
            work.finish(
                task_id,
                fence,
                "uncertain",
                {
                    "code": "provider_or_stream_outcome_unknown",
                    "stop_confirmed": False,
                    "automatic_retry_allowed": False,
                    "synthetic_fixture": True,
                },
            )
        return {
            "status": work.get(task_id)["status"],
            "provider_called": True,
            "automatic_retry_allowed": False,
            "stop_confirmed": False,
            "cost_settled": False,
            "synthetic_fixture": True,
        }

    def reconcile(self, work, task_id, *, authorize):
        with work.tx() as cur:
            row = work._get(cur, task_id)
            if not row or not authorize(cur, row):
                raise WorkError("usage_authority_required")
            work.event(cur, row, "usage_requested", {"provider": "local_fixture"})
        usage = self._json_request("GET", "/usage/" + task_id)
        if (
            not isinstance(usage, dict)
            or set(usage)
            != {
                "fixture",
                "usage_final",
                "receipt_id",
                "id",
                "request_digest",
                "amount_minor",
                "upper_minor",
                "status",
            }
            or usage["fixture"] is not True
            or usage["usage_final"] is not True
            or usage["id"] != task_id
            or usage["request_digest"] != digest(self.payload(row))
            or usage["upper_minor"] != row["upper_minor"]
            or usage["status"] not in {"completed", "stopped"}
            or type(usage["amount_minor"]) is not int
        ):
            raise WorkError("usage_receipt_mismatch")
        work.reconcile(
            task_id, usage["receipt_id"], usage["amount_minor"], digest(usage), authorize=authorize
        )
        return {**usage, "money_settlement": False}

    def stop(self, work, task_id, *, authorize):
        with work.tx() as cur:
            row = work._get(cur, task_id)
            if not row or not row["attempted"] or not authorize(cur, row):
                raise WorkError("stop_authority_required")
            work.event(cur, row, "provider_stop_requested", {"stop_confirmed": False})
        confirmed = False
        try:
            receipt = self._json_request("POST", "/stop/" + task_id)
            confirmed = bool(
                isinstance(receipt, dict)
                and set(receipt) == {"fixture", "id", "status", "stop_confirmed"}
                and receipt["fixture"] is True
                and receipt["id"] == task_id
                and receipt["status"] == "stopped"
                and receipt["stop_confirmed"] is True
            )
        except (httpx.HTTPError, ValueError):
            pass
        if confirmed:
            # A separately observed stop receipt may resolve a concurrent stream-disconnect uncertainty.
            # It never releases usage liability or overwrites a completed result.
            with work.tx() as cur:
                current = work._get(cur, task_id)
                if current["fence"] == row["fence"] and current["status"] in {
                    "running",
                    "uncertain",
                }:
                    work.q(
                        cur,
                        "UPDATE work_v1_tasks SET result_json=? WHERE id=?",
                        ('{"stop_confirmed":true,"synthetic_fixture":true}', task_id),
                    )
                    work.status(cur, current, "cancelled")
                    work.event(
                        cur,
                        current,
                        "provider_stop_confirmed",
                        {"provider": "local_fixture", "stop_confirmed": True},
                    )
        else:
            work.finish(
                task_id,
                row["fence"],
                "uncertain",
                {
                    "stop_confirmed": False,
                    "synthetic_fixture": True,
                    "automatic_retry_allowed": False,
                },
            )
        return {"stop_confirmed": confirmed, "synthetic_fixture": True, "money_settlement": False}
