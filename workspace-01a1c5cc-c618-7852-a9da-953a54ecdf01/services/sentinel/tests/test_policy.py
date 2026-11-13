"""Tests for the Sentinel policy engine — the obligations from skills/sentinel-gate.

Run: pytest -q services/sentinel/tests
"""

from __future__ import annotations

import pytest
from policy import (
    Action,
    Effect,
    EgressMode,
    VenturePolicy,
    contains_secret,
    decide,
    is_protected_path,
    scrub,
)


def pol(**kw):
    base = dict(
        slug="media-api",
        egress_mode=EgressMode.ALLOWLIST_ONLY,
        allow_hosts=("api.stripe.com", "*.amazonaws.com"),
        auto_spend_usd=0.0,
        day_budget_usd=3.0,
        spend_today_usd=0.0,
        allowed_write_roots=("/sandboxes/media-api",),
        data_class="public",
    )
    base.update(kw)
    return VenturePolicy(**base)


# --- 1. safety rules: gated by NAME, not content ---------------------------


@pytest.mark.parametrize(
    "name",
    [
        "stripe.create_refund",
        "gmail.send_message",
        "github.delete_repo",
        "x.post_tweet",
        "vercel.change_plan",
        "notion.share_page",
        "auth.rotate_api_key",
    ],
)
def test_safety_rules_gate_by_name(name):
    d = decide(Action(kind="mcp.call", actor="agent:ceo", name=name), pol())
    assert d.effect is Effect.GATE, name
    assert d.approval_required


def test_drafting_is_not_sending():
    d = decide(Action(kind="mcp.call", actor="agent:ceo", name="gmail.create_draft"), pol())
    assert d.effect is Effect.ALLOW


@pytest.mark.parametrize("name", [
    "read_billing_portal", "get invoice", "list payments", "search refunds",
    "check subscription status", "download invoice pdf", "summarise billing history",
])
def test_reading_about_money_is_browsing_not_moving_money(name):
    """A read whose object happens to be money must not fill the approval queue with noise."""
    assert decide(Action(kind="mcp.call", actor="agent:ops", name=name), pol()).effect is Effect.ALLOW


@pytest.mark.parametrize("name", ["stripe.create_refund", "refund", "charge_customer", "pay invoice"])
def test_acting_on_money_still_gates(name):
    assert decide(Action(kind="mcp.call", actor="agent:ops", name=name), pol()).effect is Effect.GATE


@pytest.mark.parametrize("name", ["read password vault", "list api keys", "get 2fa settings",
                                  "view delete history"])
def test_a_read_cannot_skip_credentials_or_deletes(name):
    assert decide(Action(kind="mcp.call", actor="agent:ops", name=name), pol()).effect is Effect.GATE


def test_money_action_kind_always_gated():
    d = decide(Action(kind="money", actor="agent:ceo", name="anything", cost_usd=0.01), pol())
    assert d.effect is Effect.GATE and d.rule == "money.any"


# --- 2. egress ------------------------------------------------------------


def test_allowlisted_host_allowed():
    a = Action(kind="http.request", actor="agent:ceo", url="https://api.stripe.com/v1/prices")
    assert decide(a, pol()).effect is Effect.ALLOW


def test_wildcard_allowlist():
    a = Action(kind="http.request", actor="agent:ceo", url="https://s3.eu.amazonaws.com/x")
    assert decide(a, pol()).effect is Effect.ALLOW


def test_unlisted_host_denied():
    a = Action(kind="http.request", actor="agent:ceo", url="https://evil.example/x")
    d = decide(a, pol())
    assert d.effect is Effect.DENY and d.rule == "network.not_in_allowlist"


@pytest.mark.parametrize(
    "url",
    ["http://169.254.169.254/latest/meta-data/", "http://10.0.0.5/x", "http://127.0.0.1:5432/"],
)
def test_metadata_and_private_ips_denied_even_when_mode_is_allow_all(url):
    a = Action(kind="http.request", actor="agent:ceo", url=url)
    d = decide(a, pol(egress_mode=EgressMode.ALLOW_ALL))
    assert d.effect is Effect.DENY and d.rule == "network.metadata_or_internal"


def test_deny_all_mode_denies_everything():
    a = Action(kind="http.request", actor="agent:ceo", url="https://api.stripe.com/v1/prices")
    assert decide(a, pol(egress_mode=EgressMode.DENY_ALL)).effect is Effect.DENY


def test_missing_policy_denies():
    a = Action(kind="http.request", actor="agent:ceo", url="https://api.stripe.com/x")
    assert decide(a, None).effect is Effect.DENY  # type: ignore[arg-type]


# --- 3. secrets -----------------------------------------------------------


def test_secret_in_payload_is_gated_and_scrubbed():
    leaked = "sk_live_" + "a" * 24
    a = Action(kind="http.request", actor="agent:ceo",
                url="https://api.stripe.com/v1/charges", method="POST",
                payload=f'{{"key":"{leaked}"}}')
    d = decide(a, pol())
    assert d.effect is Effect.GATE and d.scrub is True
    assert scrub(a.payload).count("SCRUBBED") == 1
    assert leaked not in scrub(a.payload)


def test_secret_shapes_detected():
    for s in ["ghp_" + "b" * 24, "AKIA" + "A" * 16, "-----BEGIN RSA PRIVATE KEY-----",
              "Authorization: Bearer " + "c" * 30]:
        assert contains_secret(s), s


@pytest.mark.parametrize("path", ["~/.ssh/id_rsa", ".env", "/srv/app/.env", "secrets/prod.yaml"])
def test_protected_paths(path):
    assert is_protected_path(path)


def test_env_file_read_is_denied():
    d = decide(Action(kind="file.read", actor="agent:ceo", path=".env"), pol())
    assert d.effect is Effect.DENY and d.rule == "secret.path"


# --- 4. isolation ---------------------------------------------------------


def test_write_outside_venture_root_denied():
    a = Action(kind="file.write", actor="agent:ceo", path="/sandboxes/other-venture/x.py")
    d = decide(a, pol())
    assert d.effect is Effect.DENY and d.rule == "isolation.write_root"


def test_write_inside_root_allowed():
    a = Action(kind="file.write", actor="agent:ceo", path="/sandboxes/media-api/src/x.py")
    assert decide(a, pol()).effect is Effect.ALLOW


# --- 5. budget ------------------------------------------------------------


def test_spend_above_auto_spend_gated():
    a = Action(kind="http.request", actor="agent:ceo", name="provision",
                url="https://api.stripe.com/x", cost_usd=0.50)
    d = decide(a, pol(auto_spend_usd=0.0))
    assert d.effect is Effect.GATE and d.rule == "budget.above_auto_spend"


def test_spend_within_auto_spend_allowed():
    a = Action(kind="http.request", actor="agent:ceo", name="provision",
                url="https://api.stripe.com/x", cost_usd=0.02)
    assert decide(a, pol(auto_spend_usd=0.05)).effect is Effect.ALLOW


def test_daily_budget_denies_even_when_auto_spend_permits():
    a = Action(kind="http.request", actor="agent:ceo", name="provision",
                url="https://api.stripe.com/x", cost_usd=0.50)
    d = decide(a, pol(auto_spend_usd=1.0, day_budget_usd=3.0, spend_today_usd=2.8))
    assert d.effect is Effect.DENY and d.rule == "budget.daily_exceeded"


# --- 6. unattended runs ---------------------------------------------------


def test_unattended_pii_write_gated_but_person_write_allowed():
    a = dict(kind="file.write", actor="agent:ceo", path="/sandboxes/media-api/cust.csv")
    d_routine = decide(Action(**a, initiator="routine", initiator_id="scout-daily"),
                       pol(data_class="customer_pii"))
    d_person = decide(Action(**a, initiator="person"), pol(data_class="customer_pii"))
    assert d_routine.effect is Effect.GATE and d_routine.rule == "unattended.pii_write"
    assert d_person.effect is Effect.ALLOW


# --- 7. audit row shape ---------------------------------------------------


def test_audit_row_is_flat_and_names_the_initiator():
    a = Action(kind="http.request", actor="agent:ceo", initiator="routine",
               initiator_id="scout-daily", url="https://api.stripe.com/v1/prices",
               venture="media-api")
    row = decide(a, pol()).as_audit(a)
    assert row["decision"] == "allow"
    assert row["initiator"] == {"kind": "routine", "id": "scout-daily"}
    assert row["venture"] == "media-api"
    assert set(row) >= {"action", "actor", "target", "rule", "cost_usd", "scrubbed"}
