# Verified repair evidence

- `SOURCE_PROVENANCE.json`: pinned Git source, exact reported-archive reconstruction,
  no laptop ZIP received, Windows/root-cause claims attributed rather than certified.
- `parent-review.json`: previous independent branch review; its false metadata digest
  result identifies the **incoming** defect, not the corrected current manifest.
- `studio-python.log`: Linux 49 pass / 1 Windows-only skip (50 cases).
- `handoff-python.log`: 10 cases, including stale-metadata refusal/canonical ZIP mode.
- `studio-node.log`, `retained-node.log`: 45 / 25 cases.
- `native-packages.json`, `native-packages.log`: 27 binary/tool/asset/static facts,
  not native launch proof. SDK/signing/private caches are excluded.
- `hardlink-fallback-simulation.log`: forced PermissionError exercises mock fallback;
  explicit simulation, not evidence about actual Windows permissions or a real link.
- `ruff-initial.log`: two inherited nested-context style findings; combined without
  removing assertions. `ruff-final.log`: current clean check/14-file formatting.
- `PRESERVATION.json`: parent kernel/upstream/binary identities retained, no omissions.
- `EXPORT_AUDIT.json`: selection/cache and inherited test-literal triage boundary.

`result.md` at the root is the imported raw Antigravity report. Current facts and
limits are in `REPAIR_REVIEW.md`; older evidence remains under reference-interface/.
Final archive extraction/re-export receipt is external to avoid self-reference.
Public release false; accepted genuinely observed pilot days 0.
