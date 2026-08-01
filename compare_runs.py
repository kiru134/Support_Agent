#!/usr/bin/env python3
"""Diffs two already-generated report.json files: metric deltas, improvements,
regressions, category shifts. Writes reports/<run_a>_vs_<run_b>/comparison.json
and comparison.md.

    python3 compare_runs.py reports/run1/report.json reports/final/report.json
"""
from __future__ import annotations

import sys

from evaluation.compare import compare_runs, render_comparison_markdown
from evaluation.models import RunReport


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: python3 compare_runs.py <report_a.json> <report_b.json>", file=sys.stderr)
        sys.exit(1)

    report_a = RunReport.model_validate_json(open(sys.argv[1]).read())
    report_b = RunReport.model_validate_json(open(sys.argv[2]).read())

    cmp = compare_runs(report_a, report_b)

    out_dir = f"reports/{report_a.run_name}_vs_{report_b.run_name}"
    import os

    os.makedirs(out_dir, exist_ok=True)
    with open(f"{out_dir}/comparison.json", "w") as f:
        f.write(cmp.model_dump_json(indent=2))
    with open(f"{out_dir}/comparison.md", "w") as f:
        f.write(render_comparison_markdown(cmp))

    print(f"improvements={len(cmp.improvements)} regressions={len(cmp.regressions)} still_failing={len(cmp.still_failing)}")
    print(f"wrote {out_dir}/comparison.json and {out_dir}/comparison.md")


if __name__ == "__main__":
    main()
