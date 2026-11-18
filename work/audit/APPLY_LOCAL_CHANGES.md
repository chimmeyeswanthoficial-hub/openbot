# Applying the reviewed local overlay safely

The public owner repository was reviewed at `a67fb041763bdfd16ed8b77f0ad24edd8e154f20`, with its
project nested in `workspace-01a1c5cc-c618-7852-a9da-953a54ecdf01`. These corrections are local,
not committed or pushed. `openbot-reviewed-overlay.tar.gz` is a source-only handoff, NOT an updater.

1. Fetch actual current remote HEAD into a separate clean review branch. Preserve later Antigravity
   work; compare to the reviewed SHA before any overwrite. Back up work and runtime data separately.
2. List/extract the overlay into a **separate empty directory**, inspect its manifest and diff
   against the nested project root. Its entries are relative project paths. Do not extract it
   blindly over a newer checkout. No root `.git` history is supplied.
3. Apply reviewed source/doc/notice hunks only. No `.openbot` runtime state, donor tree, credentials,
   uploads, databases or run/log evidence is in the overlay. The pre-intake source archive is just
   a local rollback reference, not current remote state.
4. `audit/incident-additions.jsonl` contains the records missing from the reviewed remote registry.
   Compare IDs with the actual registry and append only absent IDs after review. Never replace a
   live registry or rewrite its existing rows. Run `.claude/skills/postmortem/check.sh` afterward.
5. Preserve executable bits, MIT notices and Bot HQ artwork exclusions/local skill policies.
   Run the full checks and record ACTUAL JUnit outcomes; no skip-to-pass arithmetic. A different
   current HEAD/dependency resolution may give different results—investigate rather than falsify.
6. Only an authorized human-controlled review can approve a later commit/push/deployment. The
   overlay does not configure accounts, widen permissions or authorize the product launch/pilot.

`archive/PROJECT_MEMORY-before-public-intake.md` and the pre-intake source tar are historical,
not current directions. AGENTS → current memory → ADOPTION_REVIEW governs resumption.
