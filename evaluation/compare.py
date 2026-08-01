"""Diffs two RunReports: per-metric deltas, cases that flipped pass/fail, and
category count shifts. Operates on already-generated report.json data -- no
re-scoring, so it's cheap and can't disagree with the underlying reports."""
from __future__ import annotations

from datetime import datetime, timezone

from evaluation.models import ComparisonReport, MetricDelta, RunReport

_METRIC_NAMES = [
    "route_accuracy",
    "must_include_accuracy",
    "must_not_include_accuracy",
    "overall_pass_rate",
]


def compare_runs(report_a: RunReport, report_b: RunReport) -> ComparisonReport:
    deltas = []
    for name in _METRIC_NAMES:
        va = getattr(report_a.metrics, name)
        vb = getattr(report_b.metrics, name)
        deltas.append(MetricDelta(metric=name, run_a=va, run_b=vb, delta=round(vb - va, 4)))

    pass_a = {c.id: c.case_pass for c in report_a.cases}
    pass_b = {c.id: c.case_pass for c in report_b.cases}
    all_ids = sorted(set(pass_a) | set(pass_b))

    improvements = [cid for cid in all_ids if not pass_a.get(cid, False) and pass_b.get(cid, False)]
    regressions = [cid for cid in all_ids if pass_a.get(cid, False) and not pass_b.get(cid, False)]
    still_failing = [cid for cid in all_ids if not pass_a.get(cid, False) and not pass_b.get(cid, False)]

    return ComparisonReport(
        run_a=report_a.run_name,
        run_b=report_b.run_name,
        generated_at=datetime.now(timezone.utc).isoformat(),
        metric_deltas=deltas,
        improvements=improvements,
        regressions=regressions,
        still_failing=still_failing,
        category_counts_a=report_a.failure_category_counts,
        category_counts_b=report_b.failure_category_counts,
    )


def render_comparison_markdown(cmp: ComparisonReport) -> str:
    lines: list[str] = []
    lines.append(f"# Comparison -- {cmp.run_a} vs {cmp.run_b}")
    lines.append("")
    lines.append(f"Generated: {cmp.generated_at}")
    lines.append("")

    lines.append("## Metric Deltas")
    lines.append("")
    lines.append(f"| Metric | {cmp.run_a} | {cmp.run_b} | Delta |")
    lines.append("|---|---|---|---|")
    for d in cmp.metric_deltas:
        sign = "+" if d.delta >= 0 else ""
        lines.append(f"| {d.metric} | {d.run_a*100:.0f}% | {d.run_b*100:.0f}% | {sign}{d.delta*100:.0f}pp |")
    lines.append("")

    lines.append("## Improvements (fail -> pass)")
    lines.append("")
    lines.append(", ".join(cmp.improvements) if cmp.improvements else "None.")
    lines.append("")

    lines.append("## Regressions (pass -> fail)")
    lines.append("")
    lines.append(", ".join(cmp.regressions) if cmp.regressions else "None.")
    lines.append("")

    lines.append("## Still Failing (fail -> fail)")
    lines.append("")
    lines.append(", ".join(cmp.still_failing) if cmp.still_failing else "None.")
    lines.append("")

    lines.append("## Failure Category Shifts")
    lines.append("")
    all_cats = sorted(set(cmp.category_counts_a) | set(cmp.category_counts_b))
    if all_cats:
        lines.append(f"| Category | {cmp.run_a} | {cmp.run_b} |")
        lines.append("|---|---|---|")
        for cat in all_cats:
            lines.append(f"| {cat} | {cmp.category_counts_a.get(cat, 0)} | {cmp.category_counts_b.get(cat, 0)} |")
    else:
        lines.append("No failures in either run.")
    lines.append("")

    return "\n".join(lines) + "\n"
