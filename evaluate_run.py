#!/usr/bin/env python3
"""Evaluate one run: pairs cases.jsonl with answers.jsonl (and the optional
<answers>_debug.jsonl), scores route/must_include/must_not_include, categorizes
failures, and writes reports/<run_name>/report.json + report.md.

Deterministic only -- no LLM inside the evaluator (see evaluation/categorize.py).

    python3 evaluate_run.py <cases.jsonl> <answers.jsonl> <run_name>
"""
from __future__ import annotations

import sys

from evaluation.evaluator import evaluate_run
from evaluation.report_json import write_json_report
from evaluation.report_markdown import write_markdown_report


def main() -> None:
    if len(sys.argv) != 4:
        print("usage: python3 evaluate_run.py <cases.jsonl> <answers.jsonl> <run_name>", file=sys.stderr)
        sys.exit(1)

    cases_path, answers_path, run_name = sys.argv[1], sys.argv[2], sys.argv[3]
    report = evaluate_run(cases_path, answers_path, run_name)

    out_dir = f"reports/{run_name}"
    write_json_report(report, f"{out_dir}/report.json")
    write_markdown_report(report, f"{out_dir}/report.md")

    m = report.metrics
    print(f"[{run_name}] route_accuracy={m.route_accuracy:.0%} "
          f"must_include={m.must_include_accuracy:.0%} "
          f"must_not_include={m.must_not_include_accuracy:.0%} "
          f"overall_pass_rate={m.overall_pass_rate:.0%}")
    print(f"wrote {out_dir}/report.json and {out_dir}/report.md")


if __name__ == "__main__":
    main()
