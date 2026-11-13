# Security

## The boundary, in one paragraph

Every outward action an agent takes is judged by `services/sentinel/policy.py` before it happens:
safety (money, credentials, delete, send, publish, share) → venture policy (egress allowlist,
isolation, protected paths) → budget → default. The decision and the audit row are written in the
same request. There is no code path in this repository that performs an agent action without passing
through that function, and the store has no update or delete method for the audit table.

Bypasses that are *architecturally* possible and known:

1. **A process that ignores the proxy and opens a raw socket** is not stopped by this layer. That is a
   network-policy job (Kubernetes NetworkPolicy / host firewall) and is documented in `plan.md` §8.
2. **Prompts are not a boundary.** Anything enforced only by words in a routine is not enforced.
   Rules belong in `policy.py` or in a test.
3. **The control plane trusts its own filesystem.** `company/`, `.openbot/` and `policy/` are read at
   boot; anyone who can write them can change the rules. Protect the repository and the box.

## Reporting

Email the owner privately with: the failing input, the rule you expected, and what happened. Do not
open a public issue. We will:

1. reproduce it as a test in `services/sentinel/tests/` (a test that fails on `main`),
2. add a prevention rule to `.openbot/post_mortems/error_registry.jsonl` with `rule_kind: policy`
   or `test`,
3. ship the fix with the test and the ledger entry in the same PR.

## Secret handling

- Never commit `.env`, keys, or traces. `.gitignore` blocks the common shapes; the Sentinel's scrubber
  catches `sk-`, `ghp_`, `AKIA`, `xox[baprs]-`, private-key headers and bearer tokens in outgoing
  payloads, and escalates to an approval when it does.
- Protected paths (`~/.ssh`, `~/.aws`, `.env`, `secrets/`, `keyring/`) are denied for every agent in
  every egress mode.
- `KEY_ENCRYPTION_KEY` (OpenBot substrate) encrypts stored credentials: back it up before first use
  or a rotation orphans every stored key.
