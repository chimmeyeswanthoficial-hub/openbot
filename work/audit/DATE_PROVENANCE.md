# Date provenance, not backdating

The authoritative task/session date supplied to this assistant is **2026-11-10**.
The workspace runner's UTC clock and filesystem/JUnit timestamps observe
**2026-11-13** during the HQ installation and **2026-11-14** during the execution follow-up.
These are different sources of metadata;
no chronology is inferred by silently substituting one for the other.

Existing incident IDs/history and explicitly dated earlier reports are retained.
Their use of a session date is not proof of an event's exact wall-clock timestamp.
New verification receipts derive `measurement_date` from the recorded JUnit
`runner_timestamp`; the recorder no longer embeds a fixed session date. New
installation/handoff receipts distinguish authoritative task date from observed
runner timestamps. This fixes future hardcoded-date drift without rewriting history.
