# Order: add /healthz to the media-api venture service

## Outcome
`GET /healthz` on services/media-api returns 200 `{"ok":true,"ffmpeg":true,"version":"0.1.0"}`
within 50ms, and returns 503 with `ffmpeg:false` when the ffmpeg binary is missing.

## Context you must read first
- .claude/skills/sentinel-gate/SKILL.md (this service is behind the Sentinel)
- .openbot/ventures/media-api/venture.yaml (budget and isolation rules)
- .openbot/post_mortems/error_registry.jsonl, class `policy-name-normalisation`

## Constraints
- Work only inside services/media-api. Do not touch other ventures or repos/.
- No new dependencies.
- Boring over clever. No placeholders, no TODO, no `pass`.

## Acceptance
1. `pytest -q services/media-api/tests` green, including test_healthz_ok and test_healthz_no_ffmpeg.
2. The PR body contains the real curl output pasted.
3. One paragraph: "what I would break next".

## Stop and ask when
- You need a real credential or a paid API.
- Acceptance cannot pass without changing an existing public contract.
- Two attempts at the same failing step.

## Report back
Files changed, tests run by name, anything you could not do, and the reproduce command.
