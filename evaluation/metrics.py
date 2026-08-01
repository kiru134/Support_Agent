"""Aggregate metrics over a list of CaseEval. All metrics are case-level pass/fail
rates (not per-pattern), matching how "Overall Pass Rate" is naturally read --
per-pattern detail is still available in each CaseEval for drill-down."""
from __future__ import annotations

from collections import Counter

from evaluation.models import CaseEval, Metrics


def compute_metrics(cases: list[CaseEval]) -> Metrics:
    n = len(cases)
    if n == 0:
        return Metrics(
            total_cases=0,
            route_accuracy=0.0,
            must_include_accuracy=0.0,
            must_not_include_accuracy=0.0,
            overall_pass_rate=0.0,
        )
    return Metrics(
        total_cases=n,
        route_accuracy=sum(c.route_correct for c in cases) / n,
        must_include_accuracy=sum(c.must_include_ok for c in cases) / n,
        must_not_include_accuracy=sum(c.must_not_include_ok for c in cases) / n,
        overall_pass_rate=sum(c.case_pass for c in cases) / n,
    )


def compute_category_counts(cases: list[CaseEval]) -> dict[str, int]:
    counter: Counter = Counter()
    for c in cases:
        counter.update(c.failure_categories)
    return dict(sorted(counter.items(), key=lambda kv: -kv[1]))
