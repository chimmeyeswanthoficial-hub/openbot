"""Default-off authenticated owned-fixture work service, not device pairing or public auth.

Only a trusted host may provision opaque expiring sessions. Every mounted read,
review, cancel and effect derives identity from those records. No owner/actor,
program, provider endpoint, cost, policy or permission is accepted from JSON.
Legacy reference apps/transports are not mounted here. TLS, identity-provider,
hostile-code isolation and native pairing remain external gates.
"""

from __future__ import annotations

import hashlib
import json
import marshal
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from policy import contains_secret
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from work_store import WorkError, WorkUnavailable, canonical, digest


class AuthorityError(WorkError):
    pass


def token_hash(token):
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise AuthorityError("authentication_required")
    return hashlib.sha256(token.encode()).hexdigest()


def default_policy(_plan):
    return {"effect": "gate", "rule": "owned_qa.explicit_review"}


class WorkService:
    def __init__(self, work, *, enabled=False, policy=default_policy, operator_gate=None):
        if type(enabled) is not bool or not callable(policy):
            raise WorkError("explicit_configuration_required")
        if operator_gate is not None:
            from operational_controls import OperatorGate

            if type(operator_gate) is not OperatorGate or operator_gate.admin:
                raise WorkError("protected_read_only_operator_gate_required")
        self.work, self.enabled, self.policy = work, enabled, policy
        self.operator_gate = operator_gate

    def _require_running(self):
        if self.operator_gate is not None and not self.operator_gate.check():
            raise AuthorityError("operator_emergency_pause_or_state_unavailable")

    def _operator_current(self, row):
        if self.operator_gate is None:
            return True
        from operational_controls import OpsError

        try:
            current = self.operator_gate.binding()
            return not current["paused"] and current == row["plan"]["binding"].get("operator")
        except (OpsError, OSError):
            return False

    def issue_session(self, *, actor, venture, role, initiator, ttl=900):
        """Trusted host provisioning ONLY. There is deliberately no HTTP grant route."""
        if (
            not self.work.setup
            or role not in {"owner", "agent", "viewer"}
            or not re.fullmatch(r"(human|agent|service):[a-z0-9_-]{1,64}", actor)
            or (role == "owner" and not actor.startswith("human:"))
            or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,95}", venture)
            or set(initiator) != {"kind", "id"}
            or initiator["kind"] not in {"person", "routine", "event", "handoff", "memory"}
            or not isinstance(initiator["id"], str)
            or not 1 <= len(initiator["id"]) <= 128
            or type(ttl) is not int
            or not 1 <= ttl <= 3600
        ):
            raise AuthorityError("trusted_session_provisioning_required")
        token = secrets.token_urlsafe(32)
        with self.work.tx() as cur:
            self.work.q(
                cur,
                "INSERT INTO work_v1_sessions(token_hash,actor,venture,role,initiator_json,expires) VALUES(?,?,?,?,?,?)",
                (
                    token_hash(token),
                    actor,
                    venture,
                    role,
                    canonical(initiator),
                    int(self.work.clock()) + ttl,
                ),
            )
            # Grant audit contains no credential or credential digest.
            self.work.event(
                cur,
                {
                    "id": "session-grant",
                    "venture": venture,
                    "initiator": {"actor": actor, **initiator},
                },
                "session_issued",
                {"role": role, "ttl": ttl},
            )
        return token

    def revoke_session(self, token):
        if not self.work.setup:
            raise AuthorityError("trusted_session_revocation_required")
        with self.work.tx() as cur:
            session = self._session(cur, token_hash(token))
            self.work.q(
                cur,
                "UPDATE work_v1_sessions SET revoked=1 WHERE token_hash=?",
                (token_hash(token),),
            )
            self.work.event(
                cur,
                {
                    "id": "session-revoke",
                    "venture": session["venture"],
                    "initiator": session["initiator"],
                },
                "session_revoked",
                {"actor": session["actor"]},
            )

    def _session(self, cur, hashed):
        self.work.q(cur, "SELECT * FROM work_v1_sessions WHERE token_hash=?", (hashed,))
        rows = self.work.rows(cur)
        if not rows or rows[0]["revoked"] or rows[0]["expires"] <= int(self.work.clock()):
            raise AuthorityError("authentication_required")
        row = rows[0]
        row["initiator"] = {**json.loads(row["initiator_json"]), "actor": row["actor"]}
        return row

    def session(self, token):
        if not self.enabled:
            raise AuthorityError("work_service_disabled")
        with self.work.tx() as cur:
            return self._session(cur, token_hash(token))

    @staticmethod
    def _owns(session, row):
        return bool(
            row
            and session["venture"] == row["venture"]
            and (
                session["role"] in {"owner", "viewer"}
                or session["actor"] == row["initiator"]["actor"]
            )
        )

    def task(self, token, task_id, *, mutate=False):
        session = self.session(token)
        row = self.work.get(task_id)
        if not self._owns(session, row) or (mutate and session["role"] == "viewer"):
            raise AuthorityError("scoped_task_required")
        return session, row

    def bindings(self, cur=None):
        import isolation

        root = Path(__file__).resolve().parents[3]
        paths = [
            Path(__file__),
            root / "services/sentinel/work_store.py",
            root / "services/sentinel/policy.py",
            root / "services/sentinel/repository.py",
            Path(__file__).with_name("qa_workflow.py"),
            Path(__file__).with_name("qa_catalog.py"),
            Path(__file__).with_name("qa_fixture_worker.py"),
            Path(__file__).with_name("isolation.py"),
            Path(__file__).with_name("control_api.py"),
            Path(__file__).with_name("governed_skills.py"),
            Path(__file__).with_name("trust_crypto.py"),
            Path(__file__).with_name("operational_controls.py"),
            root / "requirements.control.lock.txt",
            root / "audit/first-party-tool-catalog.json",
            root / "services/worker/src/sse_protocol.py",
            root / "audit/isolation-runtime-lock.json",
        ]
        output = {}
        if self.operator_gate is not None:
            from operational_controls import OpsError

            try:
                output["operator"] = self.operator_gate.binding()
            except (OpsError, OSError) as exc:
                raise AuthorityError("operator_state_readback_required") from exc
        for path in paths:
            if any(p.is_symlink() for p in [path, *path.parents]):
                raise WorkError("symlinked_implementation")
            output[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        output["fixed_namespace_binary"] = hashlib.sha256(
            isolation.load_binary().read_bytes()
        ).hexdigest()
        for name, call in [("tool", self._invoke), ("policy", self.policy)]:
            code = getattr(call, "__code__", None)
            if code is None:
                raise WorkError("unreviewable_host_callable")
            # Marshal v3+ includes reference-count-dependent flags. A legitimate
            # concurrent invocation holding code constants must not invalidate
            # an exact review. v2 is stable for this pinned interpreter profile;
            # source/runtime-file digests remain independently bound above.
            output[name + "_code"] = hashlib.sha256(marshal.dumps(code, 2)).hexdigest()

        def limits(cursor):
            self.work.q(cursor, "SELECT scope,cap_minor FROM work_v1_limits ORDER BY scope")
            return digest(self.work.rows(cursor))

        if cur is None:
            with self.work.tx() as cursor:
                output["limits"] = limits(cursor)
        else:
            output["limits"] = limits(cur)
        return output

    def _policy(self, plan):
        try:
            result = self.policy(json.loads(canonical(plan)))
        except Exception:
            return {"effect": "deny", "rule": "policy_unavailable"}
        if (
            not isinstance(result, dict)
            or set(result) != {"effect", "rule"}
            or not isinstance(result["effect"], str)
            or result["effect"] not in {"allow", "deny", "gate"}
            or not isinstance(result["rule"], str)
        ):
            return {"effect": "deny", "rule": "unknown_policy_verdict"}
        return result

    def prepare(self, token, body):
        session = self.session(token)
        self._require_running()
        if session["role"] == "viewer":
            raise AuthorityError("proposal_permission_required")
        required = {
            "request_id",
            "fixture",
            "goal",
            "acceptance",
            "rights_ref",
            "ai_use_approved",
            "destination",
        }
        if not isinstance(body, dict) or set(body) != required:
            raise WorkError("exact_intake_fields_required")
        from qa_catalog import FIXTURES

        if (
            not isinstance(body["request_id"], str)
            or not re.fullmatch(r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}", body["request_id"])
            or not isinstance(body["fixture"], str)
            or body["fixture"] not in FIXTURES
            or type(body["ai_use_approved"]) is not bool
            or body["destination"] != "local-review"
        ):
            raise WorkError("owned_fixture_and_local_destination_required")
        for name in ("goal", "acceptance", "rights_ref"):
            text = body[name]
            if (
                not isinstance(text, str)
                or not text.strip()
                or len(text.encode()) > 1024
                or contains_secret(text)
                or any(ord(c) < 32 and c not in "\n\t" for c in text)
            ):
                raise WorkError("unsafe_or_missing_intake")
        questions = []
        if not body["rights_ref"].startswith("owned:"):
            questions.append("Confirm ownership/testing rights for the selected bundled sample.")
        if body["ai_use_approved"] is not True:
            questions.append("Approve the bounded AI-assisted QA/documentation method.")
        if questions:
            return {"status": "clarify", "questions": questions, "execution_authorized": False}
        # Content of goal/acceptance is untrusted report data, never authority or code.
        plan = {
            "tool": "owned.qa",
            "intake": json.loads(canonical(body)),
            "binding": self.bindings(),
            "upper_minor": 0,
            "currency": "usd",
            "outbound": False,
            "scope": "bundled_owned_sample_only",
        }
        verdict = self._policy(plan)
        plan["policy"] = verdict
        row, created = self.work.register(
            venture=session["venture"],
            routine="owned-qa",
            origin="manual",
            key=body["request_id"],
            when=datetime.fromtimestamp(self.work.clock(), UTC),
            initiator=session["initiator"],
            plan=plan,
            upper_minor=0,
            principal=token_hash(token),
        )
        if created or row["status"] == "preparing":
            # A crash between registration and reservation has no attempted effect.
            # Resume ONLY the identical intake/principal, with current governance,
            # on this same durable ID. No attempted/uncertain work enters this path.
            if verdict["effect"] == "deny":
                self.work.reject(row["id"], verdict["rule"], state="denied")
            else:
                self.work.reserve(row["id"], review=True)
        return self.public(self.work.get(row["id"]))

    @staticmethod
    def public(row):
        return {
            name: row[name]
            for name in (
                "id",
                "venture",
                "routine",
                "origin",
                "scheduled_utc",
                "initiator",
                "status",
                "spec_digest",
                "upper_minor",
                "held_minor",
                "spent_minor",
                "fence",
                "attempted",
                "cancel_requested",
                "plan",
                "result",
            )
        }

    def _active(self, cur, row, caller, *, owner=False, effect=False):
        try:
            session = self._session(cur, caller)
            if (owner or effect) and not self._operator_current(row):
                return False
            if (
                not self._owns(session, row)
                or session["role"] == "viewer"
                or (owner and session["role"] != "owner")
            ):
                return False
            if effect:
                if row["plan"]["binding"] != self.bindings(cur):
                    return False
                origin = self._session(cur, row["principal"])
                reviewer = self._session(cur, row["reviewer_principal"])
                if (
                    not self._owns(origin, row)
                    or reviewer["role"] != "owner"
                    or reviewer["venture"] != row["venture"]
                ):
                    return False
                if self._policy(row["plan"]) != row["plan"]["policy"]:
                    return False
            return True
        except AuthorityError:
            return False

    def approve(self, token, task_id, expected_digest, *, ttl=900):
        session, row = self.task(token, task_id, mutate=True)
        self._require_running()
        if session["role"] != "owner" or row["plan"]["binding"] != self.bindings():
            raise AuthorityError("current_exact_owner_review_required")
        return self.work.approve(
            task_id,
            expected_digest,
            session["actor"],
            ttl=ttl,
            reviewer_session=token_hash(token),
            authorize=lambda cur, row: self._active(cur, row, token_hash(token), owner=True),
        )

    def cancel(self, token, task_id):
        session, _row = self.task(token, task_id, mutate=True)
        return {
            "requested": self.work.cancel(
                task_id,
                session["actor"],
                authorize=lambda cur, row: self._active(cur, row, token_hash(token)),
            ),
            "stop_confirmed": False,
        }

    def _invoke(self, row):
        from qa_workflow import run_owned_qa

        return run_owned_qa(
            row["plan"]["intake"]["fixture"],
            run_id=row["id"],
            brief=row["plan"]["intake"],
            cancelled=lambda: (
                bool(self.work.get(row["id"])["cancel_requested"])
                or not self._operator_current(row)
            ),
        )

    def execute(self, token, task_id):
        _session, row = self.task(token, task_id, mutate=True)
        if row["status"] in {"completed", "failed", "cancelled", "uncertain", "blocked", "denied"}:
            return {**self.public(row), "replayed": True}
        self._require_running()
        if row["plan"].get("tool") != "owned.qa" or row["plan"].get("binding") != self.bindings():
            self.work.reject(task_id, "implementation_or_limits_changed")
            raise WorkError("new_exact_review_required")
        invoke = self._invoke  # freeze the reviewed host callable for this attempt
        fence = self.work.claim(task_id, "owned-qa-service")
        if fence is None:
            return {**self.public(self.work.get(task_id)), "replayed": True}
        allowed = self.work.before_effect(
            task_id,
            fence,
            row["spec_digest"],
            authorize=lambda cur, current: self._active(
                cur, current, token_hash(token), effect=True
            ),
        )
        if not allowed:
            return self.public(self.work.get(task_id))
        try:
            self._emit(row, "RUN_STARTED")
            self._emit(
                row,
                "TOOL_CALL_START",
                toolCallId=task_id + ":qa",
                toolName="owned.qa",
                args=canonical({"fixture": row["plan"]["intake"]["fixture"]}),
            )
            result = invoke(row)
            if not isinstance(result, dict):
                raise WorkError("untrusted_tool_result")
            status = (
                "cancelled" if result.get("terminal") in {"cancelled", "timed_out"} else "completed"
            )
            ending = [
                ("TOOL_CALL_END", {"toolCallId": task_id + ":qa"}),
                ("TEXT_MESSAGE_START", {"messageId": task_id + ":report"}),
                (
                    "TEXT_MESSAGE_CONTENT",
                    {
                        "messageId": task_id + ":report",
                        "delta": canonical({"artifact_digest": digest(result), "terminal": status}),
                    },
                ),
                ("TEXT_MESSAGE_END", {"messageId": task_id + ":report"}),
                ("RUN_FINISHED", {}),
            ]
            final_events = [
                {
                    "type": kind,
                    "runId": task_id,
                    "threadId": "thread_" + task_id,
                    "seq": index + 3,
                    **extra,
                }
                for index, (kind, extra) in enumerate(ending)
            ]
            if not self.work.finish(
                task_id,
                fence,
                status,
                result,
                outbox=status == "completed",
                final_events=final_events,
            ):
                raise WorkError("stale_completion")
            # Independent fixed-local/no-provider receipt, never a model-reported cost.
            self.work.reconcile(
                task_id,
                "local-no-provider:" + task_id,
                0,
                digest(
                    {"run": task_id, "result": digest(result), "basis": "fixed_owned_no_provider"}
                ),
            )
        except Exception:
            # Once authorized, a lost result cannot justify another attempt.
            self.work.finish(
                task_id, fence, "uncertain", {"code": "tool_or_persistence_outcome_unknown"}
            )
        return self.public(self.work.get(task_id))

    def _emit(self, row, kind, **extra):
        previous = self.work.events(row["id"])
        event = {
            "type": kind,
            "runId": row["id"],
            "threadId": "thread_" + row["id"],
            "seq": len(previous) + 1,
            **extra,
        }
        self.work.append_event(row["id"], event)

    def _artifact(self, cur, task):
        self.work.q(cur, "SELECT * FROM work_v1_outbox WHERE task_id=?", (task["id"],))
        rows = self.work.rows(cur)
        if not rows:
            return None
        row = rows[0]
        # The queue is mutable (review status changes); its digest is not its own
        # authority. Independently compare with the append-only staging audit.
        self.work.q(
            cur,
            "SELECT payload_json FROM work_v1_history WHERE task_id=? AND kind='outbox_staged'",
            (task["id"],),
        )
        attestations = self.work.rows(cur)
        try:
            value = json.loads(row["content_json"])
            expected = {
                "sha256": row["sha256"],
                "destination": "local-review:" + task["venture"],
                "external_delivery": False,
            }
            if (
                len(attestations) != 1
                or json.loads(attestations[0]["payload_json"]) != expected
                or row["destination"] != expected["destination"]
                or row["status"] not in {"review", "ready_local"}
                or digest(value) != row["sha256"]
            ):
                raise WorkError("artifact_readback_mismatch")
        except (ValueError, TypeError, KeyError) as exc:
            raise WorkError("artifact_readback_mismatch") from exc
        return {**row, "content": value, "external_delivery": False}

    def outbox(self, token, task_id):
        _session, task = self.task(token, task_id)
        with self.work.tx() as cur:
            return self._artifact(cur, task)

    def approve_outbox(self, token, task_id, expected_sha):
        session, _row = self.task(token, task_id, mutate=True)
        if session["role"] != "owner":
            raise AuthorityError("owner_required")
        with self.work.tx() as cur:
            row = self.work._get(cur, task_id)
            if (
                not self._active(cur, row, token_hash(token), owner=True)
                or row["status"] != "completed"
            ):
                return False
            item = self._artifact(cur, row)
            if not item or item["status"] != "review" or item["sha256"] != expected_sha:
                return False
            self.work.q(
                cur,
                "UPDATE work_v1_outbox SET status='ready_local',reviewer=? WHERE task_id=?",
                (session["actor"], task_id),
            )
            self.work.event(
                cur,
                row,
                "local_delivery_reviewed",
                {
                    "sha256": expected_sha,
                    "destination": item["destination"],
                    "external_delivery": False,
                    "reviewer": session["actor"],
                },
            )
            return True


class Intake(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    request_id: str
    fixture: str
    goal: str = Field(min_length=1, max_length=1024)
    acceptance: str = Field(min_length=1, max_length=1024)
    rights_ref: str = Field(min_length=1, max_length=1024)
    ai_use_approved: StrictBool
    destination: str


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    digest: str = Field(pattern="^[a-f0-9]{64}$")


def create_work_app(service):
    """No server starts here; explicit host construction, default-off service."""
    app = FastAPI(
        title="OpenBot owned-fixture local work API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    if not service.enabled:
        return app  # disabled means no execution/read/review routes are mounted

    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def bounded_body(request, call_next):
        value = bytearray()
        async for chunk in request.stream():
            if len(value) + len(chunk) > 16384:
                return JSONResponse({"detail": "request_too_large"}, status_code=413)
            value.extend(chunk)
        request._body = bytes(value)
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request, _exc):
        return JSONResponse({"detail": "invalid_work_request"}, status_code=422)

    @app.exception_handler(AuthorityError)
    async def authority_error(_request, _exc):
        from fastapi.responses import JSONResponse

        return JSONResponse({"detail": "authentication_or_scope_required"}, status_code=403)

    @app.exception_handler(WorkError)
    async def work_error(_request, _exc):
        from fastapi.responses import JSONResponse

        return JSONResponse({"detail": "work_contract_refused"}, status_code=409)

    @app.exception_handler(WorkUnavailable)
    async def storage_error(_request, _exc):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            {"detail": "work_store_unavailable; no automatic retry"}, status_code=503
        )

    def credential(header):
        if not service.enabled:
            raise HTTPException(404, "disabled")
        match = re.fullmatch(r"Bearer ([A-Za-z0-9_-]{43})", header or "")
        if not match:
            raise HTTPException(401, "authentication_required")
        return match[1]

    @app.post("/v3/work/tasks")
    def prepare(body: Intake, authorization: str | None = Header(default=None)):
        return service.prepare(credential(authorization), body.model_dump())

    @app.get("/v3/work/tasks")
    def tasks(authorization: str | None = Header(default=None)):
        token = credential(authorization)
        session = service.session(token)
        return [
            service.public(r)
            for r in service.work.list(session["venture"])
            if service._owns(session, r)
        ]

    @app.get("/v3/work/tasks/{task_id}")
    def task(task_id: str, authorization: str | None = Header(default=None)):
        _session, row = service.task(credential(authorization), task_id)
        return service.public(row)

    @app.post("/v3/work/tasks/{task_id}/approve")
    def approve(task_id: str, body: Review, authorization: str | None = Header(default=None)):
        return {"approved": service.approve(credential(authorization), task_id, body.digest)}

    @app.post("/v3/work/tasks/{task_id}/execute")
    def execute(task_id: str, authorization: str | None = Header(default=None)):
        return service.execute(credential(authorization), task_id)

    @app.post("/v3/work/tasks/{task_id}/cancel")
    def cancel(task_id: str, authorization: str | None = Header(default=None)):
        return service.cancel(credential(authorization), task_id)

    @app.get("/v3/work/tasks/{task_id}/outbox")
    def outbox(task_id: str, authorization: str | None = Header(default=None)):
        return service.outbox(credential(authorization), task_id)

    @app.post("/v3/work/tasks/{task_id}/outbox/approve")
    def approve_outbox(
        task_id: str, body: Review, authorization: str | None = Header(default=None)
    ):
        return {
            "approved_local_only": service.approve_outbox(
                credential(authorization), task_id, body.digest
            )
        }

    @app.get("/v3/work/tasks/{task_id}/events")
    def events(task_id: str, after: int = 0, authorization: str | None = Header(default=None)):
        token = credential(authorization)
        service.task(token, task_id)
        return service.work.events(task_id, after=after)

    return app
