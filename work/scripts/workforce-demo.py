#!/usr/bin/env python3
"""Run an OFFLINE workbench demonstration. No customer, social action, model or income.

Default QA XML, consent and human-review capability are explicitly synthetic fixtures.
Optional --junit packages a real operator-supplied report; it does not execute it.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "services/gateway/src"), str(ROOT / "services/sentinel")]
from local_executor import Authority, Owner  # noqa: E402
from workbench import FeedbackBook, qa_packet, triage  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path)
    parser.add_argument("--brief-sha256")
    parser.add_argument("--revision")
    parser.add_argument("--run-ref")
    parser.add_argument("--exit-code", type=int)
    parser.add_argument("--required-case", action="append")
    args = parser.parse_args()
    now = datetime.now(UTC).replace(microsecond=0)
    if args.junit:
        if any(x is None for x in (args.brief_sha256, args.revision, args.run_ref, args.exit_code, args.required_case)):
            parser.error("real JUnit needs explicit brief digest, revision, run ref, exit code and required cases")
        if args.junit.is_symlink() or not args.junit.is_file():
            parser.error("operator JUnit must be a regular non-symlink file")
        with args.junit.open("rb") as stream:
            xml = stream.read(2_000_001)
        packet = qa_packet(xml, brief_sha256=args.brief_sha256, revision=args.revision,
                           run_ref=args.run_ref, exit_code=args.exit_code,
                           required_cases=tuple(args.required_case))
        qa_source = "Operator-supplied JUnit; origin/exit code/revision are host attestations, not authenticated by parser."
    else:
        xml = b'<testsuite tests="1"><testcase classname="fixture" name="sample"/></testsuite>'
        packet = qa_packet(xml, brief_sha256="b" * 64, revision="a" * 64,
                           run_ref="synthetic-demo", exit_code=0, required_cases=("fixture::sample",))
        qa_source = "SYNTHETIC XML and brief/revision identifiers; not a real test run."
    brief = {"title": "Synthetic bounded QA brief", "source_url": "https://example.org/demo-only",
             "checked_at": now.isoformat(), "service": "qa", "work_kind": "deliverable",
             "location": "permitted", "ai_use": "permitted", "source_permission": "manual_metadata",
             "customer_permission": "granted"}
    cache = ROOT / ".cache/workforce"
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="offline-demo-", dir=cache) as temp:
        authority = Authority("agent:qa", "qa-pilot", "person", "synthetic-demo")
        book = FeedbackBook(Path(temp), authority)
        body = {"service": "qa", "source_kind": "direct_consented", "source_ref": "synthetic-ticket",
                "rights_ref": "synthetic-consent-not-real", "consent_to_reuse": True,
                "text": "Demonstration only: include exact reproduction evidence with a QA finding.",
                "expires_at": (now + timedelta(days=1)).isoformat()}
        created = book.submit(body, now=now)
        pending_count = len(book.lessons("qa", now=now))
        preview = book.preview(created["id"], now=now)
        # A fixture capability demonstrates code flow; it is NOT a real human review.
        fixture_owner = Owner("human:synthetic-fixture")
        book.review(created["id"], preview["sha256"], fixture_owner, now=now)
        reviewed_count = len(FeedbackBook(Path(temp), authority).lessons("qa", now=now))
        book.revoke(created["id"], fixture_owner, now=now)
        revoked_count = len(book.lessons("qa", now=now))
        social_rejected = False
        try:
            book.submit({**body, "source_kind": "linkedin"}, now=now)
        except ValueError:
            social_rejected = True
        assert (pending_count, reviewed_count, revoked_count) == (0, 1, 0) and social_rejected
        print(json.dumps({"observed_runner_utc": now.isoformat(), "mode": "offline disposable demonstration",
                          "intake": triage(brief, now=now), "qa_source": qa_source, "qa_packet": packet,
                          "feedback_fixture": {"real_consent_or_human_review": False,
                              "pending_visible": pending_count, "fixture_review_visible_after_restart": reviewed_count,
                              "visible_after_revocation": revoked_count, "social_import_refused": social_rejected},
                          "network_or_provider_calls": 0, "external_deliveries": 0, "income_usd": 0}, indent=2))


if __name__ == "__main__":
    main()
