"""OpenBot OS — Sentinel policy engine (reference implementation).

Purpose: a *deterministic, fail-closed* decision function for outward actions.
This is deliberately small and side-effect free: the FastAPI service, the worker,
and the OpenBot gateway adapter all call `decide()` so one reviewer can read one
file and know what the company is allowed to do.

Vocabulary mirrors OpenBot's own approvals engine (safety -> rules -> auto-review ->
default) so its docs/approvals.md stays the shared reference.
"""

from __future__ import annotations

import fnmatch
import ipaddress
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal
from urllib.parse import urlsplit

# ---------------------------------------------------------------------------
# Enums / data classes
# ---------------------------------------------------------------------------


class Effect(str, Enum):  # noqa: UP042 — str+Enum keeps json.dumps working without a default
    ALLOW = "allow"
    DENY = "deny"
    GATE = "gate"  # human must approve before the action executes


class EgressMode(str, Enum):  # noqa: UP042 — see Effect
    DENY_ALL = "deny_all"
    ALLOWLIST_ONLY = "allowlist_only"
    DEFAULTS_PLUS_ALLOWLIST = "defaults_plus_allowlist"
    ALLOW_ALL = "allow_all"


Initiator = Literal["person", "deployment", "routine", "responsibility", "memory", "handoff"]

#: Verbs that mean "look, don't touch". A read of a billing portal is browsing, not a payment —
#: OpenBot's own rule is that the action is its first verb, and a word that only names what it acts
#: on doesn't count. Without this, `read billing portal` asks a human 200 times a day and the queue
#: becomes noise, which is how real approvals get ignored.
READ_VERBS: frozenset[str] = frozenset({
    "read", "get", "list", "view", "search", "fetch", "query", "check", "scan", "inspect",
    "describe", "count", "preview", "show", "download", "export", "draft", "summarise", "summarize",
})

#: Any initiator in this set means nobody was watching when the action happened.
UNATTENDED: frozenset[str] = frozenset({"routine", "responsibility", "memory", "handoff"})

#: Actions whose *name* (not content) makes them always gated. Order matters only
#: for the audit row's `rule` field.
SAFETY_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("money.payment", re.compile(
        r"\b(pay|payment|checkout|purchase|refund|transfer|payout|withdraw|charge|"
        r"invoice|payroll|subscribe|subscription|plan[_\s-]?(upgrade|change)|"
        r"change[_\s-]?plan|downgrade|billing)\b", re.I)),
    # Plurals matter: `list api keys` is a credential surface, `list api key` is not a phrase
    # anyone writes. Every noun here takes an optional plural.
    ("credentials.change", re.compile(
        r"\b(passwords?|passwd|2fa|mfa|two[_\s-]?factors?|api[_\s-]?keys?|secrets?|tokens?|"
        r"credentials?|rotate|regenerate|permissions?|sharing[_\s-]?polic(y|ies))\b", re.I)),
    ("data.delete", re.compile(
        r"\b(delete|remove|destroy|erase|purge|wipe|discard|archive|trash)\b", re.I)),
    ("comms.outbound", re.compile(
        r"\b(send|reply|forward|respond|notify|broadcast|invite|comment|dm|email|"
        r"sms|whatsapp|call)\b", re.I)),
    ("content.publish", re.compile(
        r"\b(publish|post|tweet|repost|release|go[_\s-]?live|deploy[_\s-]?public)\b", re.I)),
    ("sharing.external", re.compile(
        r"\b(share|collaborator|add[_\s-]?people|public[_\s-]?link|grant[_\s-]?access)\b", re.I)),
)

#: Reading these is never allowed, in any mode, for any agent.
#: A bare name (no slash) matches any path segment; a path matches itself and below.
PROTECTED_PATHS: tuple[str, ...] = (
    "~/.ssh", "~/.aws", "~/.config/gcloud", "~/.netrc", "~/.muse", "/etc/shadow",
    ".env", ".env.local", ".env.production", "secrets", "keyring", ".ssh",
)

#: Outbound requests to these are refused before policy is even consulted.
DENY_HOSTS: tuple[str, ...] = (
    "169.254.169.254",          # AWS/GCP IMDS
    "metadata.google.internal",
    "100.100.100.200",          # Alibaba metadata
    "fd00:ec2::254",
)

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"sk_live_[A-Za-z0-9]{16,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}"),
)


@dataclass(frozen=True)
class Action:
    """One thing an agent wants to do. Keep the field names identical to the audit row."""

    kind: Literal["http.request", "file.write", "file.read", "shell.exec",
                  "mcp.call", "browser.action", "deploy", "money"]
    actor: str                     # "agent:ceo"
    initiator: Initiator = "person"
    initiator_id: str | None = None
    name: str = ""                 # tool/action name; what safety rules read
    method: str = "GET"
    url: str | None = None
    path: str | None = None
    command: str | None = None
    payload: str = ""              # serialized body, for secret scrubbing
    cost_usd: float = 0.0
    venture: str = ""


@dataclass(frozen=True)
class VenturePolicy:
    slug: str
    egress_mode: EgressMode = EgressMode.DENY_ALL
    allow_hosts: tuple[str, ...] = ()
    auto_spend_usd: float = 0.0
    day_budget_usd: float = 0.0
    spend_today_usd: float = 0.0
    allowed_write_roots: tuple[str, ...] = ()
    data_class: Literal["public", "customer_pii", "internal"] = "internal"


@dataclass(frozen=True)
class Decision:
    effect: Effect
    rule: str
    reason: str
    scrub: bool = False
    approval_required: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def as_audit(self, action: Action) -> dict[str, Any]:
        return {
            "action": action.kind,
            "actor": action.actor,
            "initiator": {"kind": action.initiator, "id": action.initiator_id},
            "target": {"method": action.method, "url": action.url,
                       "path": action.path, "name": action.name},
            "venture": action.venture,
            "decision": self.effect.value,
            "rule": self.rule,
            "reason": self.reason,
            "cost_usd": action.cost_usd,
            "scrubbed": self.scrub,
        }


def _gate(rule: str, reason: str, **kw: Any) -> Decision:
    return Decision(Effect.GATE, rule, reason, approval_required=True, **kw)


def _deny(rule: str, reason: str, **kw: Any) -> Decision:
    return Decision(Effect.DENY, rule, reason, **kw)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def contains_secret(text: str) -> bool:
    return any(p.search(text or "") for p in SECRET_PATTERNS)


def scrub(text: str) -> str:
    out = text or ""
    for p in SECRET_PATTERNS:
        out = p.sub("[SCRUBBED]", out)
    return out


def is_protected_path(path: str) -> bool:
    """True for credential-bearing locations. Bare names match a path segment."""
    probe = (path or "").replace("\\", "/").rstrip("/")
    if not probe:
        return False
    segments = [s for s in probe.split("/") if s]
    for pat in PROTECTED_PATHS:
        if "/" in pat:
            target = pat.replace("~", os.path.expanduser("~"), 1) \
                if pat.startswith("~") else pat
            if probe in (target, pat) or probe.startswith(target.rstrip("/") + "/") \
                    or probe.startswith(pat + "/"):
                return True
        else:
            if pat in segments:
                return True
    return False


def _host_of(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host


def _is_ip_denied(host: str) -> bool:
    if host in DENY_HOSTS:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_link_local or ip.is_private or ip.is_loopback or ip.is_reserved


def host_allowed(host: str, policy: VenturePolicy) -> bool:
    if policy.egress_mode is EgressMode.DENY_ALL:
        return False
    if policy.egress_mode is EgressMode.ALLOW_ALL:
        return True
    return any(fnmatch.fnmatch(host, pattern) for pattern in policy.allow_hosts)


# ---------------------------------------------------------------------------
# The decision ladder: safety -> policy -> budget -> default
# ---------------------------------------------------------------------------


def decide(action: Action, policy: VenturePolicy) -> Decision:
    # 0. Fail closed: no policy, no action.
    if policy is None:                                     # pragma: no cover - defensive
        return _deny("policy.missing", "no policy loaded; deny everything")

    # 1. Safety — never switchable off.
    #    Names arrive as `gmail.send_message`, `POST v1/charges` or "Delete repo", so
    #    separators are normalised to spaces before matching. The rule reads the action's
    #    *name*, never what the action carries: a draft is not a send.
    probe = " ".join(filter(None, [
        (action.name or "").replace("_", " ").replace("-", " ").replace(".", " ")
                            .replace("/", " ").replace(":", " "),
        (action.command or "")[:200],
    ]))
    first_verb = probe.split()[0].lower() if probe.split() else ""
    read_only = first_verb in READ_VERBS
    for rule_name, pattern in SAFETY_RULES:
        if read_only and rule_name not in ("credentials.change", "data.delete"):
            # a read still cannot change a credential or destroy something
            continue
        if pattern.search(probe):
            return _gate(rule_name, f"the action's name matches {rule_name}; a person decides")

    if action.kind == "money":
        return _gate("money.any", "money movement always needs a person")

    if action.path and action.kind in ("file.read", "file.write") and is_protected_path(action.path):
        return _deny("secret.path", f"{action.path} is a protected path")

    if action.kind == "http.request":
        host = _host_of(action.url or "")
        if not host:
            return _deny("network.malformed", "no host in URL")
        if _is_ip_denied(host) and host not in policy.allow_hosts:
            return _deny("network.metadata_or_internal",
                         f"{host} is link-local/private/reserved; refused in every mode")
        if contains_secret(action.payload) or contains_secret(action.url or ""):
            return _gate("secret.in.payload",
                         "payload carried a secret shape; scrubbed and escalated", scrub=True)
        if not host_allowed(host, policy):
            return _deny("network.not_in_allowlist",
                         f"{host} not allowed in mode {policy.egress_mode.value}")

    if action.kind == "file.write" and policy.allowed_write_roots:
        p = (action.path or "").replace("\\", "/")
        if not any(p.startswith(root.rstrip("/") + "/") or p == root.rstrip("/")
                   for root in policy.allowed_write_roots):
            return _deny("isolation.write_root",
                         f"{p} is outside {policy.slug}'s write roots")

    if contains_secret(action.payload):
        return _gate("secret.in.payload", "payload carried a secret shape; scrubbed", scrub=True)

    # 2. Budget.
    if action.cost_usd > 0:
        if action.cost_usd > policy.auto_spend_usd:
            return _gate("budget.above_auto_spend",
                         f"${action.cost_usd:.2f} > auto_spend ${policy.auto_spend_usd:.2f}")
        if policy.spend_today_usd + action.cost_usd > policy.day_budget_usd:
            return _deny("budget.daily_exceeded",
                         f"spend today ${policy.spend_today_usd:.2f} + "
                         f"${action.cost_usd:.2f} > day budget ${policy.day_budget_usd:.2f}")

    # 3. Unattended runs get no quiet writes on customer data.
    if action.initiator in UNATTENDED and policy.data_class == "customer_pii" \
            and action.kind in ("file.write", "deploy", "mcp.call"):
        return _gate("unattended.pii_write",
                     "nobody is watching and the data class is customer_pii")

    # 4. Default.
    return Decision(Effect.ALLOW, "default.allow", "read-only / in-bounds / in-budget")
