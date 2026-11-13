"""The release contract: the documents must not claim more than the code does.

A project goes public once and then rots in public. These tests are the anti-rot: they compare
`aboutme.md`'s capability tags against the tests that exist, the changelog against reality, and the
console against the endpoints it calls. They fail loudly and point at the sentence to fix.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

ROOT = pathlib.Path(__file__).parents[3]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


# --------------------------------------------------------------------- capability tags
def test_every_capability_line_carries_a_tag():
    """Every bullet in aboutme.md §3 must say what grounds it."""
    text = _read("aboutme.md")
    start = text.index("## 3. What I can do today")
    end = text.index("## 4. What I cannot do")
    section = text[start:end]
    tags = ("`[shipped]`", "`[M1", "`[human]`", "`[never]`", "`[M2]`", "`[M3]`")
    untagged = []
    for line in section.splitlines():
        if line.startswith("- "):
            # a bullet's evidence may be on the same line or the next continuation line
            idx = section.index(line)
            span = section[idx: idx + 700]
            if not any(t in span.split("\n- ")[0] for t in tags):
                untagged.append(line[:70])
    assert not untagged, "capability bullets with no evidence tag:\n  " + "\n  ".join(untagged)


def test_shipped_claims_have_a_matching_test():
    """`[shipped]` sections name a mechanism; the mechanism must have tests on disk."""
    text = _read("aboutme.md")
    shipped = text.count("`[shipped]`")
    assert shipped >= 8, f"only {shipped} shipped claims — did a section get deleted?"
    suites = {
        "policy": ROOT / "services/sentinel/tests/test_policy.py",
        "endpoints": ROOT / "services/sentinel/tests/test_app.py",
        "store": ROOT / "services/sentinel/repository.py",
        "worker": ROOT / "services/worker/tests/test_runner.py",
        "spec": ROOT / "services/worker/tests/test_spec.py",
        "ledger": ROOT / "services/ledger/tests/test_pnl.py",
        "company": ROOT / "services/sentinel/tests/test_company.py",
    }
    missing = [k for k, p in suites.items() if not p.exists()]
    assert not missing, f"claims are backed by missing modules: {missing}"


# --------------------------------------------------------------------- docs consistency
def test_no_document_promises_a_never_capability():
    """A `[never]` limit must not appear as a feature anywhere a buyer reads first."""
    never = [ln.strip("- ").strip().lower() for ln in _read("aboutme.md").splitlines()
             if "`[never]`" in ln]
    assert never, "aboutme.md lists no hard limits — that is the document lying by omission"
    readme = _read("README.md").lower()
    for phrase in ("sign contracts", "hold money for you", "file your taxes", "physical"):
        assert phrase not in readme, f"README claims {phrase!r}, which aboutme.md lists as never"


def test_readme_shows_a_working_quickstart():
    readme = _read("README.md")
    assert "make install" in readme and "make demo" in readme
    for target in ("install", "demo", "test", "smoke", "verify"):
        assert (ROOT / "Makefile").read_text().count(f"{target}:") >= 1, f"Makefile lacks {target}"


def test_changelog_latest_version_matches_the_service():
    version = re.search(r'version="([0-9.]+)"', _read("services/sentinel/app.py")).group(1)
    changelog = _read("CHANGELOG.md")
    assert f"[{version}]" in changelog, f"app.py is {version} but CHANGELOG has no [{version}] entry"


_COLLECTED = None


def _collected() -> int:
    """The number pytest would actually run — asked, not guessed.

    Counting `def test_` lines undercounts parametrised cases (162 collected vs 95 definitions), and
    a guard with the wrong arithmetic is the same rot it is meant to prevent. So we run the
    collector in a subprocess and add up the per-file counts it prints.
    """
    global _COLLECTED
    if _COLLECTED is None:
        suites = ["services/sentinel/tests", "services/worker/tests",
                  "services/ledger/tests", "packages/venture-sdk/tests",
                  "services/gateway/tests", "services/media-api/tests",
                  "scripts/tests"]
        out = subprocess.run(
            [sys.executable, "-m", "pytest", *suites, "--collect-only", "-q", "-p", "no:warnings"],
            cwd=ROOT, capture_output=True, text=True, check=False).stdout
        _COLLECTED = sum(int(n) for n in re.findall(r":\s*(\d+)\s*$", out, re.MULTILINE))
        assert _COLLECTED > 0, f"could not count the suite:\n{out[-800:]}"
    return _COLLECTED


def test_no_document_claims_a_test_count_the_suite_contradicts():
    """A number typed into prose goes stale the next time a test is added — it already has.

    Every "N passed" claim must match what pytest actually collects. A claim above the suite is a
    lie about the build; a claim below it means the document undersells it. A changelog's *older*
    entries are a dated record of what was true then, so only the newest release note is checked.
    """
    actual = _collected()
    lines = _read("CHANGELOG.md").splitlines()
    latest: list[str] = []
    for line in lines:
        if line.startswith("## ["):
            if latest:
                break
            continue
        latest.append(line)
    for name, text in (("CHANGELOG.md (latest entry)", "\n".join(latest)),
                       ("README.md", _read("README.md")),
                       ("PROJECT_STATE.md", _read("PROJECT_STATE.md"))):
        for claimed in re.findall(r"(\d+) passed", text):
            assert int(claimed) == actual, (
                f"{name} claims {claimed} passed but pytest collects {actual}; "
                "regenerate the number or remove it")


# --------------------------------------------------------------------- the console is real
def test_console_only_calls_endpoints_that_exist():
    console = _read("services/sentinel/console.html")
    app = _read("services/sentinel/app.py")
    called = set(re.findall(r'fetch\("(/v1/[^"?]+)', console))
    assert called, "the console calls no endpoints — is it static?"
    for endpoint in called:
        stem = endpoint.rstrip("/").split("/")[1]
        assert f'"{endpoint}"' in app or f"/{stem}" in app, f"console calls {endpoint}, app.py has no route"


def test_console_cannot_break_on_a_script_tag_inside_json():
    """A literal `</script>` inside an inline JSON block ends the script element early."""
    console = _read("services/sentinel/console.html")
    assert "application/json" in console
    assert "</script>" not in console.split('<script type="application/json"')[1].split("</script>")[0]


def test_console_escapes_everything_it_renders():
    console = _read("services/sentinel/console.html")
    assert "function esc(" in console
    # every template interpolation of a server value must go through esc()
    raw = re.findall(r"\+\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)*)\s*\+", console)
    unsafe = [v for v in raw if v not in ("pctUsed", "filter", "cls")
              and not v.startswith("esc")]
    assert not unsafe, f"unescaped server values rendered: {set(unsafe)}"


# --------------------------------------------------------------------- the org stays honest
def test_company_prohibitions_cover_the_five_dangerous_actions():
    text = _read("company/company.yaml").lower()
    for action in ("money", "contract", "impersonate", "another venture", "audit row"):
        assert action in text, f"no prohibition mentions {action!r}"


def test_skills_index_lists_every_skill_on_disk():
    index = _read(".claude/skills/README.md")
    for path in (ROOT / ".claude/skills").glob("*/SKILL.md"):
        assert path.parent.name in index, f"skill {path.parent.name} is not in the index"


# --------------------------------------------------------------------- docs mirror
def test_docs_mirror_matches_the_root_documents():
    """A published docs site must never serve a stale claim."""
    drifted = []
    for p in (ROOT / "docs").glob("*.md"):
        root = ROOT / p.name
        if not root.exists() or p.name == "README.md":
            continue          # docs/README.md is the docs index, not a mirror
        if p.read_text(encoding="utf-8") != root.read_text(encoding="utf-8"):
            drifted.append(p.name)
    assert not drifted, f"docs/ is stale for {drifted}; run `scripts/sync-docs.sh`"
