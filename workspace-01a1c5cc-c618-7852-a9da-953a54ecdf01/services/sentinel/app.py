"""OpenBot OS — Sentinel service (FastAPI).

One place decides whether an agent may act, and one place a person answers it.

    POST /v1/decide          judge one outward action -> allow | deny | gate (+ audit row)
    GET  /v1/approvals       the human queue (pending by default)
    POST /v1/approvals/{id}  approve or deny exactly once
    GET  /v1/audit           the append-only trail
    GET  /v1/overview        everything the console renders, in one call
    POST /v1/ledger          revenue/cogs rows, idempotent on the provider event id
    GET  /v1/pnl             money derived from rows, never stored
    GET  /                   the console (single file, no external assets)

Run:  uvicorn app:app --host 0.0.0.0 --port 8090
Env:  SENTINEL_DB (default :memory:), SENTINEL_POLICY_DIR, SENTINEL_UI_TOKEN
"""

from __future__ import annotations

import calendar
import os
import pathlib
import sqlite3
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Literal

import yaml
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "services" / "ledger" / "src"))
sys.path.insert(0, str(ROOT / "services" / "worker" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "venture-sdk" / "src"))

import pnl as pnl_mod  # noqa: E402
from policy import Action, Decision, Effect, EgressMode, VenturePolicy, decide, scrub  # noqa: E402
from repository import Store  # noqa: E402

from company import CompanyError, load_company  # noqa: E402

POLICY_DIR = os.environ.get("SENTINEL_POLICY_DIR", str(HERE / "policy"))
DB_PATH = os.environ.get("SENTINEL_DB", ":memory:")
UI_TOKEN = os.environ.get("SENTINEL_UI_TOKEN", "").strip()
CONSOLE = HERE / "console.html"

_policies: dict[str, VenturePolicy] = {}
store: Store = Store(":memory:")


# --------------------------------------------------------------------------- policy loading
class PolicyFile(BaseModel):
    slug: str
    egress_mode: EgressMode = EgressMode.DENY_ALL
    allow_hosts: list[str] = Field(default_factory=list)
    auto_spend_usd: float = 0.0
    day_budget_usd: float = 0.0
    spend_today_usd: float = 0.0
    allowed_write_roots: list[str] = Field(default_factory=list)
    data_class: Literal["public", "customer_pii", "internal"] = "internal"


def load_policies(directory: str | None = None) -> dict[str, VenturePolicy]:
    """Load ``policy/*.yaml``. A malformed file stops the service (fail closed)."""
    directory = directory or POLICY_DIR
    loaded: dict[str, VenturePolicy] = {}
    for root, _, files in os.walk(directory):
        for name in sorted(files):
            if not name.endswith((".yaml", ".yml")):
                continue
            with open(os.path.join(root, name), encoding="utf-8") as fh:
                f = PolicyFile(**(yaml.safe_load(fh) or {}))
            loaded[f.slug] = VenturePolicy(
                slug=f.slug, egress_mode=f.egress_mode, allow_hosts=tuple(f.allow_hosts),
                auto_spend_usd=f.auto_spend_usd, day_budget_usd=f.day_budget_usd,
                spend_today_usd=f.spend_today_usd,
                allowed_write_roots=tuple(f.allowed_write_roots), data_class=f.data_class,
            )
    return loaded


def _ventures() -> list[dict[str, Any]]:
    p = ROOT / ".openbot" / "state" / "active_ventures.yaml"
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data.get("ventures", [])


def _budget() -> dict[str, Any]:
    p = ROOT / ".openbot" / "state" / "budget.json"
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


def _company_summary() -> dict[str, Any]:
    try:
        c = load_company(company_month_cap_usd=float(_budget().get("company_month_cap_usd") or 1e9))
        return {
            "ok": True, "trading_name": c.trading_name, "legal_name": c.legal_name,
            "formation": c.formation,
            "roles": [{"id": r.id, "kind": r.kind, "title": r.title,
                       "reports_to": r.reports_to, "may_not": sorted(r.may_not),
                       "ceiling_usd_month": r.cost_ceiling_usd_month} for r in c.roles],
            "duties": [{"id": d.id, "role": d.role, "cadence": d.cadence} for d in c.duties],
            "prohibitions": list(c.prohibitions),
        }
    except CompanyError as e:
        return {"ok": False, "error": str(e)}


def _routines() -> dict[str, Any]:
    from runner import cron_matches, next_fire
    from spec import SpecError, parse_file

    now = time.gmtime()
    from datetime import datetime
    clock = datetime(now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min)
    out, problems = [], []
    for path in sorted((ROOT / ".openbot" / "routines").glob("*.md")):
        try:
            s = parse_file(str(path))
        except SpecError as e:
            problems.append(str(e))
            continue
        nxt = next_fire(s.schedule, clock)
        out.append({
            "id": s.id, "bot": s.bot, "schedule": s.schedule,
            "every_min": s.interval_min, "budget_usd": s.budget_usd,
            "approval": s.approval, "venture": s.venture,
            "next_fire": nxt.strftime("%Y-%m-%d %H:%M") if nxt else None,
            "fires_now": cron_matches(s.schedule, clock),
            "outputs": list(s.outputs),
        })
    return {"routines": out, "problems": problems}


def _incidents(limit: int = 20) -> list[dict[str, Any]]:
    p = ROOT / ".openbot" / "post_mortems" / "error_registry.jsonl"
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines()[-limit:]:
        if line.strip():
            import json
            rows.append(json.loads(line))
    return rows


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _policies, store
    _policies = load_policies()
    store = Store(DB_PATH)
    yield


app = FastAPI(title="OpenBot OS Sentinel", version="0.2.3", lifespan=lifespan)
_policies = load_policies()


def require_ui_token(x_openbot_token: str | None = Header(default=None)) -> None:
    """Writes are open on loopback for the demo; set SENTINEL_UI_TOKEN for anything public."""
    if UI_TOKEN and x_openbot_token != UI_TOKEN:
        raise HTTPException(401, "console token required")


# --------------------------------------------------------------------------- models
class ActionIn(BaseModel):
    kind: Literal["http.request", "file.write", "file.read", "shell.exec",
                  "mcp.call", "browser.action", "deploy", "money", "routine.run"]
    venture: str
    actor: str = "agent:system"
    initiator: Literal["person", "deployment", "routine",
                       "responsibility", "memory", "handoff"] = "person"
    initiator_id: str | None = None
    name: str = ""
    method: str = "GET"
    url: str | None = None
    path: str | None = None
    command: str | None = None
    payload: str = ""
    cost_usd: float = 0.0


class DecisionOut(BaseModel):
    run_id: str
    effect: Literal["allow", "deny", "gate"]
    rule: str
    reason: str
    approval_id: str | None = None
    scrubbed_payload: str | None = None
    audit: dict[str, Any]


class Verdict(BaseModel):
    decision: Literal["approved", "denied"]
    by: str = "human:owner"
    note: str | None = None


class LedgerIn(BaseModel):
    venture: str
    kind: Literal["revenue", "refund", "cogs", "agent_cost", "marketing", "fee", "adjustment"]
    amount_usd: float
    source: str = "manual"
    external_id: str | None = None
    idempotency_key: str
    meta: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- routes
def _must_persist(fn, *args, **kwargs):
    """No audit row, no action.

    The core invariant of this service is that every decision is recorded *before* it is returned
    to the caller. If the store cannot be written, the caller must not proceed, so this raises 503
    instead of letting a decision leak out unrecorded.
    """
    try:
        return fn(*args, **kwargs)
    except (sqlite3.Error, OSError) as e:
        raise HTTPException(
            503, f"audit store unavailable ({e.__class__.__name__}); every action is refused "
                 "until it can be recorded again") from e


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    store_ok = True
    try:
        store.audit_count()
    except (sqlite3.Error, OSError):
        store_ok = False
    return {"ok": store_ok, "store": "ok" if store_ok else "unavailable",
            "policies": sorted(_policies), "audit_rows": store.audit_count() if store_ok else -1,
            "db": DB_PATH, "console": CONSOLE.exists(), "ui_token_required": bool(UI_TOKEN)}


@app.post("/v1/decide", response_model=DecisionOut)
def decide_endpoint(body: ActionIn) -> DecisionOut:
    started = time.time()
    policy = _policies.get(body.venture)
    action = Action(kind=body.kind, actor=body.actor, initiator=body.initiator,
                    initiator_id=body.initiator_id, name=body.name, method=body.method,
                    url=body.url, path=body.path, command=body.command,
                    payload=body.payload, cost_usd=body.cost_usd, venture=body.venture)
    if policy is None:
        d = Decision(Effect.DENY, "policy.unknown_venture",
                     f"no policy for venture {body.venture!r}; denied")
    else:
        d = decide(action, policy)

    run_id = f"r_{uuid.uuid4().hex[:16]}"
    approval_id = None
    if d.effect is Effect.GATE:
        approval_id = f"ap_{uuid.uuid4().hex[:12]}"

    row = {"run_id": run_id, "venture": body.venture, "actor": body.actor,
           "action": body.kind, "decision": d.effect.value, "rule": d.rule, "reason": d.reason,
           "initiator": {"kind": body.initiator, "id": body.initiator_id},
           "approval_id": approval_id, "cost_usd": body.cost_usd,
           "scrubbed": d.scrub, "target": {"method": body.method, "url": body.url,
                                           "path": body.path, "name": body.name},
           "latency_ms": round((time.time() - started) * 1000, 2)}
    _must_persist(store.audit, row)
    if approval_id:
        _must_persist(store.create_approval,
                      {"id": approval_id, "run_id": run_id, "venture": body.venture,
                       "rule": d.rule, "reason": d.reason, "action": row["target"],
                       "cost_usd": body.cost_usd})
    return DecisionOut(run_id=run_id, effect=d.effect.value, rule=d.rule, reason=d.reason,
                       approval_id=approval_id,
                       scrubbed_payload=scrub(body.payload) if d.scrub else None, audit=row)


@app.get("/v1/approvals")
def list_approvals(status: str = "pending") -> list[dict[str, Any]]:
    if status == "pending":
        store.expire_approvals(older_than_seconds=int(os.environ.get("APPROVAL_TTL_S", 86400)))
    return store.list_approvals(status)


@app.post("/v1/approvals/{approval_id}")
def resolve_approval(approval_id: str, verdict: Verdict,
                     _: None = Depends(require_ui_token)) -> dict[str, Any]:
    row = store.get_approval(approval_id)
    if row is None:
        raise HTTPException(404, "no such approval")
    if row["status"] != "pending":
        raise HTTPException(409, f"already {row['status']}")
    if not _must_persist(store.resolve_approval, approval_id, verdict.decision,
                         verdict.by, verdict.note):
        raise HTTPException(409, "already resolved (lost a race)")
    updated = store.get_approval(approval_id) or {}
    _must_persist(store.audit, {"run_id": row["run_id"], "venture": row["venture"], "actor": verdict.by,
                 "action": "approval.resolve", "decision": verdict.decision,
                 "rule": "hitl", "approval_id": approval_id,
                 "initiator": {"kind": "person", "id": verdict.by},
                 "target": {"name": f"approval {approval_id}"}})
    return updated


@app.get("/v1/audit")
def audit_tail(limit: int = 50, decision: str | None = None,
               venture: str | None = None) -> list[dict[str, Any]]:
    return store.audit_tail(limit, decision=decision, venture=venture)


@app.post("/v1/ledger")
def post_ledger(body: LedgerIn, _: None = Depends(require_ui_token)) -> JSONResponse:
    try:
        row = pnl_mod.validate_row(body.model_dump())
    except pnl_mod.LedgerError as e:
        raise HTTPException(422, str(e)) from e
    created = _must_persist(store.post_ledger, row)
    return JSONResponse({"created": created, "idempotency_key": body.idempotency_key},
                        status_code=201 if created else 200)


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> JSONResponse:
    import json
    import webhook as wh_mod

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    if secret:
        if not wh_mod.verify_stripe_signature(payload, sig_header, secret):
            raise HTTPException(400, "invalid stripe webhook signature")

    try:
        event = json.loads(payload.decode("utf-8"))
    except Exception as e:
        raise HTTPException(400, "malformed json payload") from e

    row = wh_mod.map_stripe_event_to_ledger_row(event)
    if not row:
        return JSONResponse({"status": "ignored", "event": event.get("type")}, status_code=200)

    try:
        validated_row = pnl_mod.validate_row(row)
    except pnl_mod.LedgerError as e:
        raise HTTPException(422, str(e)) from e

    created = _must_persist(store.post_ledger, validated_row)
    return JSONResponse(
        {"status": "recorded", "created": created, "idempotency_key": row["idempotency_key"]},
        status_code=201 if created else 200,
    )



@app.get("/v1/pnl")
def get_pnl(venture: str | None = None) -> dict[str, Any]:
    rows = store.ledger_rows(venture)
    per = pnl_mod.compute(rows)
    return {"as_of": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "portfolio": pnl_mod.portfolio(per),
            "ventures": [v.as_row() for v in per.values()],
            "rows": len(rows)}


def _approvals_pending_max_age_hours(pending: list[dict[str, Any]]) -> float:
    if not pending:
        return 0.0
    now = time.time()
    oldest_age_s = 0.0
    for a in pending:
        created_str = a.get("created")
        if created_str:
            try:
                t = calendar.timegm(time.strptime(created_str, "%Y-%m-%dT%H:%M:%SZ"))
                age = max(0.0, now - t)
                if age > oldest_age_s:
                    oldest_age_s = age
            except Exception:
                pass
    return round(oldest_age_s / 3600.0, 1)


@app.get("/v1/overview")
def overview() -> dict[str, Any]:
    """Everything the console needs, in one call. No aggregation is invented here."""
    per = pnl_mod.compute(store.ledger_rows())
    pending = store.list_approvals("pending")
    return {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "health": healthz(),
        "company": _company_summary(),
        "ventures": _ventures(),
        "budget": _budget(),
        "routines": _routines(),
        "approvals": pending,
        "approvals_pending_max_age_hours": _approvals_pending_max_age_hours(pending),
        "audit": store.audit_tail(40),
        "runs": store.runs(25),
        "pnl": {"portfolio": pnl_mod.portfolio(per), "ventures": [v.as_row() for v in per.values()]},
        "incidents": _incidents(12),
    }


@app.get("/", response_class=HTMLResponse)
def console() -> HTMLResponse:
    if not CONSOLE.exists():
        return HTMLResponse("<h1>console.html is missing</h1>", status_code=500)
    return HTMLResponse(CONSOLE.read_text(encoding="utf-8"))


def main() -> None:  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8090")))
