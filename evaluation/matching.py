"""Deterministic regex matching -- no LLM anywhere in this package, per spec.
Mirrors the semantics already established by score_answers.py and the golden
cases' own format: each pattern in must_include/must_not_include is itself often
an alternation (`a|b|c`), and is evaluated as a single regex search, case-insensitive.
"""
from __future__ import annotations

import re

from evaluation.models import PatternResult


def _search(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text, re.I))


def eval_must_include(patterns: list[str], answer: str) -> list[PatternResult]:
    return [PatternResult(pattern=p, matched=_search(p, answer)) for p in patterns]


def eval_must_not_include(patterns: list[str], answer: str) -> list[PatternResult]:
    return [PatternResult(pattern=p, matched=_search(p, answer)) for p in patterns]


def must_include_ok(results: list[PatternResult]) -> bool:
    return all(r.matched for r in results)


def must_not_include_ok(results: list[PatternResult]) -> bool:
    # "ok" means none of the forbidden patterns matched.
    return not any(r.matched for r in results)
