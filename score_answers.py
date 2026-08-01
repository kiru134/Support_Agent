#!/usr/bin/env python3
"""Scores an answers.jsonl against a golden cases.jsonl.

    python3 score_answers.py <cases.jsonl> <answers.jsonl>

Checks each case's must_include / must_not_include regexes (any-of within each
inner list, per the golden set's format) and whether the derived route matches
expected_route. Prints a per-case table plus a summary. Regex-passing is
necessary but not sufficient -- always also read the actual answers by hand (see
ITERATION.md); the golden set's own v03 `why` field warns that substring checks
can't distinguish "quoting a rule" from "misapplying it."
"""
from __future__ import annotations

import json
import re
import sys


def _any_match(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def score(cases_path: str, answers_path: str) -> None:
    cases = {c["id"]: c for c in (json.loads(l) for l in open(cases_path) if l.strip())}
    answers = {a["id"]: a for a in (json.loads(l) for l in open(answers_path) if l.strip())}

    n_pass = 0
    n_route_match = 0
    rows = []
    for cid, case in cases.items():
        ans = answers.get(cid)
        if ans is None:
            rows.append((cid, "MISSING", "-", "-", "no answer produced"))
            continue

        text = ans.get("answer", "")
        route_ok = ans.get("route") == case["expected_route"]
        must_include_ok = all(_any_match([p], text) for p in case.get("must_include", []))
        must_not_ok = not any(_any_match([p], text) for p in case.get("must_not_include", []))
        case_pass = route_ok and must_include_ok and must_not_ok

        n_pass += int(case_pass)
        n_route_match += int(route_ok)

        detail = []
        if not route_ok:
            detail.append(f"route: got={ans.get('route')} want={case['expected_route']}")
        if not must_include_ok:
            missing = [p for p in case.get("must_include", []) if not _any_match([p], text)]
            detail.append(f"missing must_include: {missing}")
        if not must_not_ok:
            hit = [p for p in case.get("must_not_include", []) if _any_match([p], text)]
            detail.append(f"hit must_not_include: {hit}")

        rows.append((cid, "PASS" if case_pass else "FAIL", ans.get("route"), case["expected_route"], "; ".join(detail)))

    print(f"{'id':6s} {'result':6s} {'route':10s} {'expected':10s} detail")
    for cid, result, route, expected, detail in rows:
        print(f"{cid:6s} {result:6s} {str(route):10s} {str(expected):10s} {detail}")

    total = len(cases)
    print()
    print(f"regex pass: {n_pass}/{total}   route match: {n_route_match}/{total}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python3 score_answers.py <cases.jsonl> <answers.jsonl>", file=sys.stderr)
        sys.exit(1)
    score(sys.argv[1], sys.argv[2])
