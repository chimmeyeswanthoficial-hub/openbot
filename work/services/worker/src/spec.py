"""Markdown routine → RoutineSpec.

The interface is a document; the contract is this parser. A routine that does not parse is not a
routine, and the worker refuses to schedule it (fail closed, like everything else here).

Front-matter keys are strict: an unknown key is an error, not a silently ignored typo. That is
deliberate — `budget_usd` misspelled as `budget` would otherwise produce an unbudgeted run.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Literal

import yaml

MIN_INTERVAL_MIN = 15
MAX_INTERVAL_FIELDS = 5
REQUIRED = ("id", "bot", "schedule", "budget_usd", "max_runtime_min", "initiator")
OPTIONAL = ("timezone", "retry", "approval", "outputs", "tags", "goal", "venture")
ALLOWED = frozenset(REQUIRED + OPTIONAL)

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
CRON_RE = re.compile(r"^[0-9*/,\-]+( [0-9*/,\-]+){4}$")


class SpecError(ValueError):
    """The routine document cannot be scheduled as written."""


@dataclass(frozen=True)
class RoutineSpec:
    id: str
    bot: str
    schedule: str
    budget_usd: float
    max_runtime_min: int
    initiator: Literal["routine"]
    body: str
    timezone: str = "Asia/Kolkata"
    retry: int = 1
    approval: Literal["gate", "auto", "never"] = "gate"
    outputs: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    goal: str | None = None
    venture: str | None = None
    source_path: str | None = None

    @property
    def body_hash(self) -> str:
        """Stable hash of what the model actually reads, so re-embedding can be skipped."""
        return hashlib.sha256(self.body.encode("utf-8")).hexdigest()[:16]

    @property
    def interval_min(self) -> int | None:
        return cron_min_interval(self.schedule)

    def run_plan(self) -> dict[str, Any]:
        """What a run of this routine would look like. Used by `dry_run.py` and the console."""
        return {
            "routine": self.id,
            "bot": self.bot,
            "venture": self.venture,
            "schedule": self.schedule,
            "every_min": self.interval_min,
            "budget_usd": self.budget_usd,
            "max_runtime_min": self.max_runtime_min,
            "approval": self.approval,
            "retry": self.retry,
            "initiator": {"kind": self.initiator, "id": self.id},
            "outputs": list(self.outputs),
            "body_sha": self.body_hash,
            "leaves_network": self.approval != "never",
            "worst_case_monthly_cost_usd": (
                round(self.budget_usd * (30 * 24 * 60 / self.interval_min), 2)
                if self.interval_min else None
            ),
        }


def cron_min_interval(expr: str) -> int | None:
    """Smallest gap between fires, for the simple shapes a routine is allowed to use."""
    parts = expr.split()
    if len(parts) != MAX_INTERVAL_FIELDS:
        return None
    minute, hour, dom, month, dow = parts
    m = re.fullmatch(r"\*/(\d+)", minute)
    if m and hour == dom == month == dow == "*":
        return int(m.group(1))
    if minute.isdigit() and hour == "*" and dom == month == dow == "*":
        return 60
    if minute.isdigit() and hour.isdigit() and dom == month == dow == "*":
        return 24 * 60
    if minute.isdigit() and hour.isdigit() and dom == "*" and month == "*" and dow != "*":
        return 24 * 60                    # a weekday pattern: still one fire a day
    return None


def _front_matter(text: str, source: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        raise SpecError(f"{source}: must start with a '---' front-matter block")
    end = text.find("\n---", 3)
    if end == -1:
        raise SpecError(f"{source}: unterminated front-matter")
    try:
        meta = yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError as e:
        raise SpecError(f"{source}: front-matter is not valid YAML: {e}") from e
    if not isinstance(meta, dict):
        raise SpecError(f"{source}: front-matter must be a mapping")
    body = text[end + 4:].lstrip("\n")
    return meta, body


OUTPUT_KINDS = ("channel", "page", "url")


def _normalise_outputs(raw: Any, source: str) -> tuple[str, ...]:
    """Accept both shapes a person actually writes:

        outputs: ["#ops-daily", "page:Reviews/{{year}}-W{{week}}"]
        outputs:
          - channel: "#ops-daily"
          - page: "Reviews/{{year}}-W{{week}}"

    and store one canonical form, `kind:target`, so the worker never guesses.
    """
    if raw in (None, "", []):
        return ()
    if isinstance(raw, (str, dict)):
        raw = [raw]
    if not isinstance(raw, list):
        raise SpecError(f"{source}: outputs must be a list")
    out: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            if len(item) != 1:
                raise SpecError(f"{source}: each output takes exactly one key, got {item!r}")
            (kind, target), = item.items()
        else:
            text = str(item)
            if text.startswith("#"):
                kind, target = "channel", text
            elif ":" in text:
                kind, target = text.split(":", 1)
            else:
                raise SpecError(f"{source}: output {text!r} has no kind (use channel:/page:/url:)")
        kind, target = str(kind).strip().lower(), str(target).strip()
        if kind not in OUTPUT_KINDS:
            raise SpecError(f"{source}: output kind {kind!r} must be one of {OUTPUT_KINDS}")
        if not target:
            raise SpecError(f"{source}: output {kind} has an empty target")
        out.append(f"{kind}:{target}")
    return tuple(out)


def parse(text: str, source: str = "<string>") -> RoutineSpec:
    meta, body = _front_matter(text, source)

    unknown = sorted(set(meta) - ALLOWED)
    if unknown:
        raise SpecError(f"{source}: unknown front-matter key(s) {unknown}; allowed: {sorted(ALLOWED)}")
    missing = [k for k in REQUIRED if meta.get(k) in (None, "")]
    if missing:
        raise SpecError(f"{source}: missing required key(s) {missing}")

    rid = str(meta["id"])
    if not ID_RE.match(rid):
        raise SpecError(f"{source}: id {rid!r} must be kebab-case, 3–64 chars")

    schedule = str(meta["schedule"])
    if len(schedule.split()) != MAX_INTERVAL_FIELDS or not CRON_RE.match(schedule):
        raise SpecError(f"{source}: schedule {schedule!r} is not a 5-field cron expression")
    interval = cron_min_interval(schedule)
    if interval is not None and interval < MIN_INTERVAL_MIN:
        raise SpecError(f"{source}: fires every {interval} min, below the {MIN_INTERVAL_MIN} min floor")

    if meta["initiator"] != "routine":
        raise SpecError(f"{source}: initiator must be 'routine' — a scheduled run is unattended, "
                        "and the audit row must say so")

    try:
        budget = float(meta["budget_usd"])
    except (TypeError, ValueError) as e:
        raise SpecError(f"{source}: budget_usd must be a number") from e
    if budget <= 0:
        raise SpecError(f"{source}: budget_usd must be > 0 (a run that may spend must declare a ceiling)")
    if budget > 50:
        raise SpecError(f"{source}: budget_usd {budget} exceeds the per-run ceiling of $50")

    try:
        runtime = int(meta["max_runtime_min"])
    except (TypeError, ValueError) as e:
        raise SpecError(f"{source}: max_runtime_min must be an integer") from e
    if not 1 <= runtime <= 240:
        raise SpecError(f"{source}: max_runtime_min must be 1–240")

    approval = str(meta.get("approval") or "gate")
    if approval not in ("gate", "auto", "never"):
        raise SpecError(f"{source}: approval must be gate|auto|never")
    retry = int(meta.get("retry") or 0)
    if not 0 <= retry <= 3:
        raise SpecError(f"{source}: retry must be 0–3 (three failures is a stop, not a fourth try)")

    outputs = _normalise_outputs(meta.get("outputs"), source)
    if any(o.startswith("channel:") for o in outputs) and not body.strip():
        raise SpecError(f"{source}: a routine that posts to a channel needs a body to post")

    if "spend" in body.lower() and approval == "never":
        raise SpecError(f"{source}: body talks about spending but approval is 'never'")

    return RoutineSpec(
        id=rid, bot=str(meta["bot"]), schedule=schedule, budget_usd=budget,
        max_runtime_min=runtime, initiator="routine", body=body,
        timezone=str(meta.get("timezone") or "Asia/Kolkata"), retry=retry,
        approval=approval,                    # type: ignore[arg-type]
        outputs=tuple(str(o) for o in outputs), tags=tuple(meta.get("tags") or ()),
        goal=meta.get("goal"), venture=meta.get("venture"), source_path=source,
    )


def parse_file(path: str) -> RoutineSpec:
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        raise SpecError(f"cannot read {path}: {e}") from e
    return parse(text, source=path)


def parse_dir(directory: str) -> tuple[list[RoutineSpec], list[str]]:
    """Parse every routine in a directory. Returns (specs, problems) — never raises, so a broken
    file cannot stop the other routines from running."""
    import glob
    import os

    specs: list[RoutineSpec] = []
    problems: list[str] = []
    ids: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(directory, "**", "*.md"), recursive=True)):
        try:
            spec = parse_file(path)
        except SpecError as e:
            problems.append(str(e))
            continue
        if spec.id in ids:
            problems.append(f"{path}: duplicate routine id {spec.id!r} (also {ids[spec.id]})")
            continue
        ids[spec.id] = path
        specs.append(spec)
    return specs, problems
