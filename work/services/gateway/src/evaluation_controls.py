"""Protected-evaluation and observed-day contracts, NOT a completed S12 pilot.

Default fixture-only mode can NEVER accept independent evaluation or a pilot.
Unit clock jumps/synthetic signer metadata are not observed days. No evaluator
changes source, budgets, policy, corpus, release thresholds or release authority.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import UTC, datetime

from operational_controls import HEX, OpsError, _private, _sqlite_input, _write_new
from trust_crypto import canonical, digest, verify


class AssessmentError(ValueError):
    pass


def _integer(value, minimum=0, maximum=2**63 - 1):
    return type(value) is int and minimum <= value <= maximum


def _hex(value):
    return isinstance(value, str) and re.fullmatch(HEX, value) is not None


class Assessment:
    def __init__(
        self,
        root,
        *,
        policy,
        policy_sha256,
        trusted,
        fixture_only=True,
        initialize=False,
        clock=time.time,
    ):
        fields = {
            "schema",
            "workflow",
            "min_tasks",
            "min_days",
            "min_quality",
            "max_human_minutes",
            "max_cost_minor",
            "oncall_ref",
        }
        if (
            type(fixture_only) is not bool
            or type(initialize) is not bool
            or (not fixture_only and clock is not time.time)
            or set(policy) != fields
            or policy["schema"] != "openbot.assessment-policy/1"
            or policy["workflow"] not in {"qa-docs", "owned-media"}
            or not _integer(policy["min_tasks"], 20, 1000)
            or not _integer(policy["min_days"], 30, 180)
            or not _integer(policy["min_quality"], 1, 100)
            or not _integer(policy["max_human_minutes"], 1)
            or not _integer(policy["max_cost_minor"])
            or not _hex(policy["oncall_ref"])
            or digest(policy) != policy_sha256
        ):
            raise AssessmentError("out_of_band_pinned_evaluation_policy_required")
        self.policy = json.loads(canonical(policy))
        self.policy_sha = policy_sha256
        self.trusted = trusted
        self.fixture_only = fixture_only
        self.clock = clock
        self._creating = initialize
        self.root = _private(root, initialize)
        self._config = canonical(
            {"schema": 1, "policy_sha256": policy_sha256, "fixture_only": fixture_only}
        ).decode()
        self.path = self.root / "assessment.sqlite3"
        if initialize:
            if self.path.exists():
                raise AssessmentError("existing_assessment_refused")
            _write_new(self.path, b"")
            with self.connection() as conn:
                conn.executescript("""CREATE TABLE configuration(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL);
                  CREATE TABLE frozen(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL,accepted INTEGER NOT NULL);
                  CREATE TABLE reports(source TEXT PRIMARY KEY,body TEXT NOT NULL);
                  CREATE TABLE pilot(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL,started INTEGER,stopped INTEGER);
                  CREATE TABLE days(day TEXT PRIMARY KEY,evidence TEXT UNIQUE,body TEXT NOT NULL);
                  CREATE TRIGGER frozen_u BEFORE UPDATE ON frozen BEGIN SELECT RAISE(ABORT,'immutable'); END;
                  CREATE TRIGGER frozen_d BEFORE DELETE ON frozen BEGIN SELECT RAISE(ABORT,'immutable'); END;
                  CREATE TRIGGER reports_u BEFORE UPDATE ON reports BEGIN SELECT RAISE(ABORT,'immutable'); END;
                  CREATE TRIGGER reports_d BEFORE DELETE ON reports BEGIN SELECT RAISE(ABORT,'immutable'); END;
                  CREATE TRIGGER days_u BEFORE UPDATE ON days BEGIN SELECT RAISE(ABORT,'immutable'); END;
                  CREATE TRIGGER days_d BEFORE DELETE ON days BEGIN SELECT RAISE(ABORT,'immutable'); END;
                  CREATE TRIGGER pilot_body BEFORE UPDATE OF body,started ON pilot BEGIN SELECT RAISE(ABORT,'immutable'); END;
                  CREATE TRIGGER pilot_delete BEFORE DELETE ON pilot BEGIN SELECT RAISE(ABORT,'immutable'); END;
                  CREATE TRIGGER pilot_stop BEFORE UPDATE OF stopped ON pilot WHEN OLD.stopped=1 AND NEW.stopped<>1 BEGIN SELECT RAISE(ABORT,'latched'); END;
                  CREATE TRIGGER config_u BEFORE UPDATE ON configuration BEGIN SELECT RAISE(ABORT,'immutable'); END;
                  CREATE TRIGGER config_d BEFORE DELETE ON configuration BEGIN SELECT RAISE(ABORT,'immutable'); END;""")
                conn.execute("INSERT INTO configuration VALUES(1,?)", (self._config,))
        self._creating = False
        with self.connection() as conn:
            conn.execute("SELECT body FROM frozen LIMIT 0")

    @contextmanager
    def connection(self):
        try:
            _private(self.root)
            _sqlite_input(self.path, 4 << 20)
            conn = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=2)
            try:
                conn.execute("BEGIN IMMEDIATE")
                with conn:
                    if not self._creating and (
                        conn.execute("SELECT body FROM configuration WHERE id=1").fetchone()
                        != (self._config,)
                        or digest(self.policy) != self.policy_sha
                    ):
                        raise AssessmentError("pinned_profile_policy_and_fixture_mode_required")
                    yield conn
            finally:
                conn.close()
        except (sqlite3.Error, OpsError) as exc:
            raise AssessmentError("protected_assessment_state_required") from exc

    def _signed(self, envelope, role):
        try:
            if len(canonical(envelope)) > 512000:
                raise AssessmentError("evidence_bound")
            body = verify(envelope, self.trusted, role)
            entry = self.trusted[envelope["key_id"]]
            if (
                not isinstance(body, dict)
                or body.get("synthetic") is not self.fixture_only
                or entry.get("independent") is not True
                or (
                    role in {"independent-evaluator", "pilot-observer"}
                    and entry.get("qualified") is not True
                )
                or (role == "pilot-owner" and entry.get("human") is not True)
            ):
                raise AssessmentError("independent_current_qualified_role_required")
            if role in {"independent-evaluator", "pilot-observer"} and any(
                other.get("public_key") == entry["public_key"]
                and set(other.get("roles", [])) & {"agent", "pilot-owner"}
                for other in self.trusted.values()
            ):
                raise AssessmentError("owner_agent_and_independent_reviewer_keys_must_differ")
            return body
        except (ValueError, KeyError, TypeError) as exc:
            raise AssessmentError("current_bound_external_signature_required") from exc

    def _frozen(self):
        with self.connection() as conn:
            row = conn.execute("SELECT body FROM frozen WHERE id=1").fetchone()
        if not row:
            raise AssessmentError("freeze_before_evaluation_required")
        envelope = json.loads(row[0])
        return envelope, self._signed(envelope, "evaluation-custodian")

    def freeze_sha(self):
        return digest(self._frozen()[0])

    def freeze(self, envelope):
        body = self._signed(envelope, "evaluation-custodian")
        fields = {
            "schema",
            "policy_sha256",
            "workflow",
            "baseline_sha256",
            "candidate_sha256",
            "suite_sha256",
            "criteria_sha256",
            "task_hashes",
            "frozen_at",
            "corpus_kind",
            "synthetic",
        }
        if (
            set(body) != fields
            or body["schema"] != "openbot.protected-suite/1"
            or body["policy_sha256"] != self.policy_sha
            or body["workflow"] != self.policy["workflow"]
            or body["corpus_kind"] != "sealed-held-out"
            or not _integer(body["frozen_at"], 0, int(self.clock()))
            or not all(
                _hex(body[k])
                for k in ["baseline_sha256", "candidate_sha256", "suite_sha256", "criteria_sha256"]
            )
            or body["baseline_sha256"] == body["candidate_sha256"]
            or not isinstance(body["task_hashes"], list)
            or not self.policy["min_tasks"] <= len(body["task_hashes"]) <= 1000
            or not all(_hex(x) for x in body["task_hashes"])
            or len(set(body["task_hashes"])) != len(body["task_hashes"])
            or digest(body["task_hashes"]) != body["suite_sha256"]
        ):
            raise AssessmentError("unique_prefrozen_held_out_corpus_and_criteria_required")
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO frozen VALUES(1,?,?)",
                (canonical(envelope).decode(), int(self.clock())),
            )
        return {
            "frozen": True,
            "task_count": len(body["task_hashes"]),
            "independent_evaluation_accepted": False,
            "fixture_only": self.fixture_only,
        }

    def _report(self, envelope, frozen, freeze_sha):
        body = self._signed(envelope, "independent-evaluator")
        with self.connection() as conn:
            accepted = conn.execute("SELECT accepted FROM frozen WHERE id=1").fetchone()[0]
        fields = {
            "schema",
            "freeze_sha256",
            "source_sha256",
            "policy_sha256",
            "issued",
            "results",
            "synthetic",
        }
        if (
            set(body) != fields
            or body["schema"] != "openbot.assessment-report/1"
            or body["freeze_sha256"] != freeze_sha
            or body["source_sha256"] not in {frozen["baseline_sha256"], frozen["candidate_sha256"]}
            or body["policy_sha256"] != self.policy_sha
            or not _integer(body["issued"], max(frozen["frozen_at"], accepted), int(self.clock()))
            or not isinstance(body["results"], list)
            or len(body["results"]) != len(frozen["task_hashes"])
        ):
            raise AssessmentError("prefrozen_exact_source_and_complete_evaluation_required")
        names = []
        for row in body["results"]:
            required = {
                "task_sha256",
                "evidence_sha256",
                "quality",
                "critical_errors",
                "permission_failures",
                "data_loss",
                "recovery_ok",
                "injection_ok",
                "human_minutes",
                "cpu_millis",
                "peak_rss_bytes",
                "cost_minor",
            }
            if (
                not isinstance(row, dict)
                or set(row) != required
                or not _hex(row["task_sha256"])
                or not _hex(row["evidence_sha256"])
                or any(
                    type(row[k]) is not bool for k in ["data_loss", "recovery_ok", "injection_ok"]
                )
                or any(
                    not _integer(v)
                    for k, v in row.items()
                    if k
                    not in {
                        "task_sha256",
                        "evidence_sha256",
                        "data_loss",
                        "recovery_ok",
                        "injection_ok",
                    }
                )
                or row["quality"] > 100
            ):
                raise AssessmentError("exact_integer_measures_required")
            names.append(row["task_sha256"])
        if len(set(names)) != len(names) or set(names) != set(frozen["task_hashes"]):
            raise AssessmentError("every_frozen_task_once_required")
        return body

    def evaluate(self, envelope):
        original, frozen = self._frozen()
        body = self._report(envelope, frozen, digest(original))
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO reports VALUES(?,?)",
                (body["source_sha256"], canonical(envelope).decode()),
            )
        return self.status()

    def _measures(self, body):
        rows = body["results"]
        return {
            "quality_total": sum(x["quality"] for x in rows),
            "task_count": len(rows),
            "cost_minor": sum(x["cost_minor"] for x in rows),
            "human_minutes": sum(x["human_minutes"] for x in rows),
            "cpu_millis": sum(x["cpu_millis"] for x in rows),
            "peak_rss_bytes": max(x["peak_rss_bytes"] for x in rows),
            "critical_errors": sum(x["critical_errors"] for x in rows),
            "permission_failures": sum(x["permission_failures"] for x in rows),
            "data_loss": any(x["data_loss"] for x in rows),
            "recovery_ok": all(x["recovery_ok"] for x in rows),
            "injection_ok": all(x["injection_ok"] for x in rows),
            "min_quality": min(x["quality"] for x in rows),
        }

    def status(self):
        candidate_ok = False
        comparison = {}
        valid = True
        try:
            original, frozen = self._frozen()
            with self.connection() as conn:
                reports = [json.loads(x[0]) for x in conn.execute("SELECT body FROM reports")]
            observed = {
                body["source_sha256"]: self._measures(body)
                for env in reports
                for body in [self._report(env, frozen, digest(original))]
            }
            if set(observed) == {frozen["baseline_sha256"], frozen["candidate_sha256"]}:
                baseline = observed[frozen["baseline_sha256"]]
                candidate = observed[frozen["candidate_sha256"]]
                comparison = {"baseline": baseline, "candidate": candidate}
                candidate_ok = (
                    candidate["critical_errors"] == candidate["permission_failures"] == 0
                    and not candidate["data_loss"]
                    and candidate["recovery_ok"]
                    and candidate["injection_ok"]
                    and candidate["min_quality"] >= self.policy["min_quality"]
                    and candidate["quality_total"] >= baseline["quality_total"]
                    and candidate["cost_minor"] <= self.policy["max_cost_minor"]
                    and candidate["human_minutes"] <= self.policy["max_human_minutes"]
                )
        except AssessmentError:
            valid = False
        with self.connection() as conn:
            pilot = conn.execute("SELECT body,started,stopped FROM pilot WHERE id=1").fetchone()
            days = [json.loads(x[0]) for x in conn.execute("SELECT body FROM days ORDER BY day")]
        elapsed = False
        stopped = bool(pilot and pilot[2])
        consecutive = True
        if pilot:
            try:
                grant = self._signed(json.loads(pilot[0]), "pilot-owner")
                if not pilot[1] <= int(self.clock()) < grant["expires"]:
                    stopped = True
                elapsed = int(self.clock()) - pilot[1] >= self.policy["min_days"] * 86400
                previous = datetime.fromtimestamp(pilot[1], UTC).date()
                last_usage = 0
                for index, envelope in enumerate(days):
                    day = self._signed(envelope, "pilot-observer")
                    current = datetime.fromisoformat(day["day"]).date()
                    if (current - previous).days != (0 if index == 0 else 1):
                        consecutive = False
                    if (
                        day["usage_minor"] < last_usage
                        or day["usage_minor"] > grant["budget_minor"]
                        or day["critical_errors"]
                        or day["data_loss"]
                        or not day["healthy"]
                        or not day["usage_verified"]
                    ):
                        stopped = True
                    previous = current
                    last_usage = day["usage_minor"]
                if (datetime.fromtimestamp(self.clock(), UTC).date() - previous).days > (
                    1 if days else 0
                ):
                    consecutive = False
            except (AssessmentError, ValueError, KeyError, TypeError):
                stopped = True
        stopped = stopped or not consecutive or (bool(pilot) and not candidate_ok)
        if pilot and stopped and not pilot[2]:
            with self.connection() as conn:
                conn.execute("UPDATE pilot SET stopped=1 WHERE id=1")
        return {
            "fixture_only": self.fixture_only,
            "candidate_thresholds_met": candidate_ok,
            "comparison": comparison,
            "independent_report_signatures_valid": candidate_ok and valid,
            "independent_evaluation_accepted": False,
            "pilot_ledger_initialized": bool(pilot),
            "pilot_started": False,
            "observed_days": len(days),
            "elapsed_requirement_met": elapsed,
            "stopped": stopped,
            "observation_contract_thresholds_met": bool(pilot)
            and not self.fixture_only
            and candidate_ok
            and not stopped
            and elapsed
            and len(days) >= self.policy["min_days"],
            "pilot_gate_accepted": False,
            "release_authorized": False,
            "earnings": "not_measured",
        }

    def start(self, envelope, *, host_gate=None, staging_witness=None, staging_owner=None):
        body = self._signed(envelope, "pilot-owner")
        now = int(self.clock())
        fields = {
            "schema",
            "source_sha256",
            "policy_sha256",
            "freeze_sha256",
            "starts_at",
            "expires",
            "oncall_ref",
            "consent_ref",
            "budget_minor",
            "synthetic",
        }
        frozen = self._frozen()[1]
        if (
            set(body) != fields
            or body["schema"] != "openbot.pilot-grant/1"
            or body["source_sha256"] != frozen["candidate_sha256"]
            or body["policy_sha256"] != self.policy_sha
            or body["freeze_sha256"] != self.freeze_sha()
            or not _integer(body["starts_at"], max(0, now - 300), now)
            or not _integer(
                body["expires"],
                body["starts_at"] + self.policy["min_days"] * 86400,
                body["starts_at"] + 180 * 86400,
            )
            or body["oncall_ref"] != self.policy["oncall_ref"]
            or not _hex(body["consent_ref"])
            or not _integer(body["budget_minor"], 0, self.policy["max_cost_minor"])
            or not self.status()["candidate_thresholds_met"]
        ):
            raise AssessmentError(
                "current_owner_scope_consent_oncall_budget_and_evaluation_required"
            )
        if not self.fixture_only:
            from staging_readiness import ExternalGate

            if (
                type(host_gate) is not ExternalGate
                or not host_gate.evaluate(staging_witness, staging_owner)[
                    "approved_host_and_security_gate"
                ]
            ):
                raise AssessmentError("live_external_staging_security_acceptance_required")
        with self.connection() as conn:
            conn.execute("INSERT INTO pilot VALUES(1,?,?,0)", (canonical(envelope).decode(), now))
        return self.status()

    def observe(self, envelope):
        body = self._signed(envelope, "pilot-observer")
        now = int(self.clock())
        status = self.status()
        if not status["pilot_ledger_initialized"] or status["stopped"]:
            raise AssessmentError("active_nonstopped_observation_ledger_required")
        fields = {
            "schema",
            "source_sha256",
            "grant_sha256",
            "day",
            "observed_at",
            "evidence_sha256",
            "usage_minor",
            "usage_verified",
            "critical_errors",
            "data_loss",
            "healthy",
            "synthetic",
        }
        frozen = self._frozen()[1]
        with self.connection() as conn:
            grant_json, started = conn.execute(
                "SELECT body,started FROM pilot WHERE id=1"
            ).fetchone()
        if (
            set(body) != fields
            or body["schema"] != "openbot.pilot-day/1"
            or body["grant_sha256"] != digest(json.loads(grant_json))
            or body["source_sha256"] != frozen["candidate_sha256"]
            or body["day"] != datetime.fromtimestamp(now, UTC).date().isoformat()
            or not _integer(body["observed_at"], max(started, now - 300), now)
            or datetime.fromtimestamp(body["observed_at"], UTC).date().isoformat() != body["day"]
            or not _hex(body["evidence_sha256"])
            or not _integer(body["usage_minor"])
            or not _integer(body["critical_errors"])
            or any(type(body[k]) is not bool for k in ["usage_verified", "data_loss", "healthy"])
        ):
            raise AssessmentError("fresh_current_utc_day_exact_source_evidence_required")
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO days VALUES(?,?,?)",
                (body["day"], body["evidence_sha256"], canonical(envelope).decode()),
            )
        result = self.status()
        if result["stopped"]:
            with self.connection() as conn:
                conn.execute("UPDATE pilot SET stopped=1 WHERE id=1")
        return result
