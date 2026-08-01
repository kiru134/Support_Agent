"""Human-readable Markdown report -- Summary, Metrics, Failure Categories, Failed
Cases, Suggested Improvements. The suggestions are generated from which categories
actually appear, not a static checklist."""
from __future__ import annotations

from pathlib import Path

from evaluation.models import RunReport

_SUGGESTIONS = {
    "Escalation Failure": (
        "Escalation misses/over-escalations found -- re-check the system prompt's "
        "escalation category list against the failing questions' exact wording, "
        "and consider whether guardrails.py's safety-net regex needs a new signal."
    ),
    "Tool Selection Failure": (
        "Wrong tool combination chosen -- strengthen the system prompt's grounding "
        "rule (when to call get_orders vs search_policy vs both) and review the "
        "tool descriptions themselves for ambiguity."
    ),
    "Retrieval Failure": (
        "The needed fact exists in some chunk of the corpus but wasn't retrieved "
        "for this query -- check retrieval.py's synonym map for a lexical gap "
        "between the question's phrasing and the policy doc's wording, or inspect "
        "hybrid search's fused ranking for this query."
    ),
    "Chunking Failure": (
        "The needed fact exists in the raw policy document but no single produced "
        "chunk contains it -- the chunk boundary split it awkwardly. Check "
        "retrieval.py's chunking logic (heading/paragraph splitting) for this "
        "specific document."
    ),
    "Grounding Failure": (
        "The needed fact WAS present in a retrieved tool result, but the model "
        "didn't use it -- this is a prompting issue, not a retrieval one. Consider "
        "a few-shot exemplar closer to this case's shape."
    ),
    "Tool Execution Failure": (
        "A tool call itself errored (not just \"chose the wrong tool\") -- check "
        "the call_trace's raw result for the actual exception; this is often an "
        "infrastructure issue (auth propagation, transport) rather than an LLM "
        "reasoning failure."
    ),
    "Hallucination": (
        "The model stated something it should never state (a must_not_include hit) "
        "-- verify the output-validation guardrail's regex bank covers this phrasing; "
        "if it does and still slipped through, the corrective-retry budget may need review."
    ),
    "Authorization Failure": (
        "A scope/identity-leak was found -- if ground-truth-verified (an order id "
        "belonging to a different real user was mentioned), this is critical: "
        "re-verify the authorization boundary is actually being hit on this case. "
        "If only pattern-based, still treat as high priority pending verification."
    ),
    "Prompt Failure": (
        "The model's declared route (from finalize_answer) disagreed with what it "
        "actually did (call_trace) -- its own reasoning was self-inconsistent. "
        "Read the full transcript for this case; this proxy only flags the "
        "divergence, not the root cause."
    ),
    "Output Formatting": (
        "Case produced no usable answer (empty, or a system error marker) -- this "
        "is likely an infrastructure/exception issue, not an LLM reasoning failure; "
        "check the run's stderr log for this case id."
    ),
    "Unknown": (
        "Some failures didn't match any heuristic category -- read these by hand; "
        "the automatic categorization has genuine limits (see evaluation/categorize.py)."
    ),
}


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def render_markdown(report: RunReport) -> str:
    lines: list[str] = []
    lines.append(f"# Evaluation Report -- {report.run_name}")
    lines.append("")
    lines.append(f"Generated: {report.generated_at}  ")
    lines.append(f"Cases file: `{report.cases_path}`  ")
    lines.append(f"Answers file: `{report.answers_path}`  ")
    if report.debug_path_used:
        lines.append(f"Debug side-channel: `{report.debug_path_used}` (used for finer categorization)  ")
    else:
        lines.append("Debug side-channel: not found -- categorization used answer/route signal only.  ")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    n_pass = sum(c.case_pass for c in report.cases)
    lines.append(
        f"Overall pass rate: **{_fmt_pct(report.metrics.overall_pass_rate)}** "
        f"({n_pass}/{report.metrics.total_cases} cases)."
    )
    lines.append("")
    lines.append(
        "Categories here are heuristic triage labels inferred from route/regex "
        "signals, not authoritative diagnoses -- always read failing cases directly."
    )
    lines.append("")

    lines.append("## Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Route Accuracy | {_fmt_pct(report.metrics.route_accuracy)} |")
    lines.append(f"| Must-Include Accuracy | {_fmt_pct(report.metrics.must_include_accuracy)} |")
    lines.append(f"| Must-Not-Include Accuracy | {_fmt_pct(report.metrics.must_not_include_accuracy)} |")
    lines.append(f"| Overall Pass Rate | {_fmt_pct(report.metrics.overall_pass_rate)} |")
    lines.append("")

    lines.append("## Failure Categories")
    lines.append("")
    if report.failure_category_counts:
        lines.append("| Category | Count |")
        lines.append("|---|---|")
        for cat, count in report.failure_category_counts.items():
            lines.append(f"| {cat} | {count} |")
    else:
        lines.append("None -- all cases passed.")
    lines.append("")

    lines.append("## Failed Cases")
    lines.append("")
    failed = [c for c in report.cases if not c.case_pass]
    if not failed:
        lines.append("None.")
    for c in failed:
        cats = ", ".join(c.failure_categories) or "Unknown"
        lines.append(f"### {c.id} -- {cats}")
        lines.append("")
        lines.append(f"**Question:** {c.question}")
        lines.append("")
        lines.append(f"**Expected route:** `{c.expected_route}` | **Actual route:** `{c.actual_route}`")
        lines.append("")
        missing = [r.pattern for r in c.must_include if not r.matched]
        if missing:
            lines.append(f"**Missing must_include:** {missing}")
            lines.append("")
        hit = [r.pattern for r in c.must_not_include if r.matched]
        if hit:
            lines.append(f"**Hit must_not_include:** {hit}")
            lines.append("")
        if c.call_trace is not None:
            lines.append(f"**Call trace:** {c.call_trace}")
            lines.append("")
        lines.append(f"**Answer:** {c.answer}")
        lines.append("")

    lines.append("## Suggested Improvements")
    lines.append("")
    seen_categories = list(report.failure_category_counts.keys())
    if not seen_categories:
        lines.append("None -- all cases passed.")
    for cat in seen_categories:
        suggestion = _SUGGESTIONS.get(cat)
        if suggestion:
            lines.append(f"- **{cat}** ({report.failure_category_counts[cat]}): {suggestion}")

    return "\n".join(lines) + "\n"


def write_markdown_report(report: RunReport, out_path: str) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(render_markdown(report))
