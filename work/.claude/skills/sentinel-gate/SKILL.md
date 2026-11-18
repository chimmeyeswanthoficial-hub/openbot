---
name: sentinel-gate
description: Design rules for the Sentinel layer — the FastAPI/policy boundary that sits between agents and everything outside the sandbox (network egress, credentials, money, messaging, deletes). Use when adding any outbound call, storing or using a secret, adding a payment/spend path, reviewing a tool that acts in the world, or writing a policy rule (CEL/YAML) and its audit row.
---

# Sentinel gate

Two implementations of one idea. OpenBot's server gateway already governs **tool and browser
actions** (resolve target → evaluate policy → write audit row → act → audit failures). `services/sentinel`
governs **raw egress**: any HTTP the agent's own code makes, and it is where the money and secret
rules live. Keep one policy vocabulary across both.

## The five questions before any outward action

1. **Who asked?** `actor.id` (whose authority) *and* `initiator.kind` (person / routine /
   responsibility / handoff / memory / deployment). Unattended runs get stricter rules.
2. **Where does it go?** `page.host`, `url.host`, `mcp.server`, `file.path`. Deny-list of
   metadata endpoints (169.254.169.254, fd00:ec2::254), payment hosts, prod secrets host.
3. **What does it touch?** money, credentials, other people's data, production, other ventures.
4. **What is the worst case?** If the answer is "a stranger gets a message" or "we lose $X",
   the rule is a **gate**, not a log line.
5. **Who is watching?** If nobody, the action gets `approval: gate` or is denied outright.

## Decision ladder (first match wins — same shape as OpenBot's approvals)

| Order | Layer | Can it be turned off? |
|---|---|---|
| 1 | **Safety** (hard-coded): money movement, credential/2FA change, delete, publish, send-to-others, share-externally, cross-venture access, sandbox escape, metadata endpoints | never |
| 2 | **Policy** (YAML/CEL per venture): network allowlist mode, spend ceiling, data class | per venture only by a human PR |
| 3 | **Budget**: `budget_usd` of the run, venture daily cap, company monthly cap | raised only by a human |
| 4 | **Auto-review** (model reviewer on low-risk writes **inside** the sandbox) | per-venture switch |
| 5 | **Default**: allow read-only inside sandbox | — |

Fail closed. A missing policy permits nothing. A broken deny rule denies. A broken allow rule does
not permit.

## What always interrupts (HITL queue)

Serialise state, write a `pending_approvals` row, push the AG-UI interrupt, and **block the run** —
never poll-and-continue, never "assume yes after 60s".

- any payment, checkout, refund, transfer, payout, invoice, subscription change, plan upgrade;
- any spend above `ventures[x].auto_spend_usd` (default **$0** for new ventures, $5 company-wide
  until revenue exists);
- credential read/write, OAuth grant, 2FA change, key rotation;
- send/reply/post/publish to anyone outside the company, or to a customer alias;
- delete/archive outside the venture's sandbox;
- writing production config, migrations, DNS, or the Sentinel's own policy file;
- any access to another venture's paths, DB schema, or credentials.

Recognition is by **the action's name**, not by the content it carries (a draft email is not a
send). This mirrors OpenBot's `docs/approvals.md` — reuse that vocabulary verbatim so one reviewer
can read both.

## Secret handling

- Agents never hold a real key. Sentinel injects a **per-run, per-venture, TTL-bounded** credential
  at the edge, and logs `{venture, tool, key_alias, ttl}` — never the value, never a prefix + hash
  that lets you confirm a guess.
- Requests leave with `X-OpenBot-Run: <run_id>` and the alias, not the secret.
- Any payload containing a pattern matching a known secret shape (`sk-`, `ghp_`, `AKIA`,
  `-----BEGIN * PRIVATE KEY`) is scrubbed **and** raised as an incident — a leak attempt is a bug in
  the agent's prompt, and the prompt is code.
- Reading `.env`, `~/.ssh`, cloud metadata, or another venture's keyring is denied at the tool
  layer, not the prompt layer. Prompts are suggestions; the boundary is code.

## Egress modes (per venture, per agent)

| Mode | Meaning | Use for |
|---|---|---|
| `deny_all` | nothing leaves; only the local model gateway answers | untrusted/just-learned skills |
| `allowlist_only` | exact hosts, no wildcards on eTLD+1 | production ventures |
| `defaults_plus_allowlist` | vendor APIs we already pay for + allowlist | normal operation |
| `allow_all` | nothing but safety rules | human-driven debugging only, never a routine |

The newly-learned-skill path is always: learn in `deny_all` → test in a throwaway sandbox in
`allowlist_only` with mock keys → promote to `defaults_plus_allowlist` by PR.

## Audit row (one per decision, append-only)

```json
{"ts":"2026-11-10T06:00:03.412Z","run_id":"r_01J...","venture":"media-api",
 "actor":"agent:ceo","initiator":{"kind":"routine","id":"scout-daily"},
 "action":"http.request","target":{"method":"POST","host":"api.stripe.com","path":"/v1/prices"},
 "decision":"gate","rule":"money.payment_intent","cost_usd":0,
 "approval_id":"ap_01J...","latency_ms":12}
```

Aggregate views come from rows only. If a number is not in the ledger, it did not happen.

## Test obligations (a policy without tests is a comment)

1. Table test every safety rule: the same action with a benign label must still be gated when the
   *effect* is money/credential/outbound-message.
2. Property test the scrubber: generated payloads with random secret shapes never reach the wire.
3. Replay test: given a recorded audit log, the policy engine's decisions reproduce exactly
   (determinism matters because Muse Code replays sessions).
4. Fail-closed test: delete the policy file → everything except loopback is denied and server
   refuses to serve.
