"""Deterministic failure categorization -- rule-based heuristics over the signals
available in {expected_route, actual_route, must_include/must_not_include results,
answer text, optional call_trace, optional tool_calls, optional
unauthorized_order_refs, optional declared_route}. No LLM. These are best-effort
triage labels for grouping failures during iteration, not authoritative diagnoses --
a case can land in more than one category, and "Unknown" is a legitimate, expected
outcome when the available signal doesn't confidently explain the failure. Always
read the actual failing answers; don't treat this as ground truth.

Authorization Failure has two tiers: `unauthorized_order_refs` (from
evaluator.py, cross-referenced against real DATA-orders.json ownership -- this is
actual ground truth, not a proxy) takes priority when present; the pattern-based
must_not_include heuristic and the denied-lookup-plus-fabricated-figure heuristic
remain as fallbacks for when no debug data / no order ids are mentioned at all.

Chunking Failure vs. Retrieval Failure, properly split using the full policy corpus
(not just what this query's search_policy call retrieved): if a missing fact isn't
in what was retrieved, check whether it exists in ANY chunk in the whole corpus --
if yes, this query's retrieval simply missed it (Retrieval Failure); if it's not in
any produced chunk but IS present in the raw, un-chunked document text, the chunker
split it awkwardly across a boundary (Chunking Failure); if it's in neither, that's
still scored as Retrieval Failure rather than inventing a fourth "not in source at
all" category -- treat that combination conservatively.

Prompt Failure is scored only when `declared_route` is available (see
agent/graph_agent.py's finalize_answer tool) and disagrees with the verified
`actual_route` derived from call_trace -- a concrete, auto-detectable proxy for
"the model's own stated reasoning was inconsistent with what it actually did",
which is the one part of "prompt caused incorrect reasoning" that's safely
inferable without reading the transcript by hand. It is not a general-purpose
prompt-failure detector; genuinely wrong-but-self-consistent reasoning still needs
a human read.
"""
from __future__ import annotations

import re
from pathlib import Path

from evaluation.models import CaseEval, PatternResult
from retrieval import POLICY_DIR, get_index

_ROUTE_HAS_POLICY = {"policy", "both"}

# Heuristic signal that a matched must_not_include pattern encodes an
# authorization/scope-leak concern rather than a generic fabrication check.
_AUTH_LEAK_PATTERN_SIGNAL = re.compile(r"ord_|password|2fa|account.?number|\bssn\b", re.I)

# Shapes actually observed from this project's tool-call failures (FastMCP/HTTP
# exceptions surfaced through ToolNode), as opposed to a tool *correctly* returning
# {"error": "not_found"} for a nonexistent/not-owned order -- that's expected
# behavior, not a failure.
_TOOL_EXECUTION_ERROR_SIGNAL = re.compile(r"error calling tool|traceback|tool_call_failed", re.I)

_DOLLAR_FACT_SIGNAL = re.compile(r"\$\d")

_raw_policy_text_cache: str | None = None


def _raw_policy_text() -> str:
    """Un-chunked text of every policy doc, concatenated -- read once, cached.
    Used only for the Chunking Failure tier below."""
    global _raw_policy_text_cache
    if _raw_policy_text_cache is None:
        _raw_policy_text_cache = "\n".join(
            p.read_text() for p in sorted(Path(POLICY_DIR).glob("POLICY_-*.md"))
        )
    return _raw_policy_text_cache


def _tool_execution_errors(tool_calls: list[dict]) -> list[dict]:
    return [tc for tc in tool_calls if _TOOL_EXECUTION_ERROR_SIGNAL.search(str(tc.get("result", "")))]


def _search_policy_text(tool_calls: list[dict]) -> str:
    return " ".join(
        str(tc.get("result", "")) for tc in tool_calls if tc.get("name") == "search_policy"
    )


def _get_orders_denied(tool_calls: list[dict]) -> bool:
    """True only if EVERY get_orders call was denied -- i.e. the model never once
    got real data. A single denied call followed by a successful retry (e.g. the
    model guessed an order_id, got not_found, then correctly listed all orders) is
    normal self-correction, not a security-relevant signal; flagging on ANY denial
    produced a false positive here during iteration (see ITERATION.md).

    Specifically checks for "not_found" -- NOT the bare substring "error", which
    also appears in the legitimate {"error": "ambiguous", "candidates": [...]}
    shape (multiple of the user's own orders matched). That's a successful,
    non-denied lookup that happens to need disambiguation, not a security-relevant
    denial; treating it as one produced a second false positive here during
    iteration (see ITERATION.md)."""
    get_orders_calls = [tc for tc in tool_calls if tc.get("name") == "get_orders"]
    if not get_orders_calls:
        return False
    return all('"not_found"' in str(tc.get("result", "")) for tc in get_orders_calls)


def _grounding_category(missing_include: list[PatternResult], tool_calls: list[dict] | None) -> str:
    if not tool_calls:
        return "Retrieval Failure"

    retrieved_text = _search_policy_text(tool_calls)
    if any(re.search(r.pattern, retrieved_text, re.I) for r in missing_include):
        return "Grounding Failure"

    full_corpus_chunks = [c.text for c in get_index().chunks]
    if any(re.search(r.pattern, chunk, re.I) for r in missing_include for chunk in full_corpus_chunks):
        return "Retrieval Failure"

    if any(re.search(r.pattern, _raw_policy_text(), re.I) for r in missing_include):
        return "Chunking Failure"

    return "Retrieval Failure"


def categorize(
    expected_route: str,
    actual_route: str | None,
    answer: str,
    must_include_results: list[PatternResult],
    must_not_include_results: list[PatternResult],
    call_trace: list[str] | None = None,
    tool_calls: list[dict] | None = None,
    unauthorized_order_refs: list[str] | None = None,
    declared_route: str | None = None,
) -> list[str]:
    categories: list[str] = []

    if not answer.strip() or answer.startswith("[error running case:"):
        categories.append("Output Formatting")
        # A system-level failure like this makes every other heuristic below
        # unreliable (there's no real answer content to reason about) -- stop here.
        return categories

    if unauthorized_order_refs:
        # Ground truth, not a proxy -- an order id belonging to a different real
        # user was mentioned in this answer.
        categories.append("Authorization Failure")

    hit_not_include = [r for r in must_not_include_results if r.matched]
    if hit_not_include and "Authorization Failure" not in categories:
        if any(_AUTH_LEAK_PATTERN_SIGNAL.search(r.pattern) for r in hit_not_include):
            categories.append("Authorization Failure")
        else:
            categories.append("Hallucination")
    elif hit_not_include:
        # Ground truth already caught it as Authorization Failure -- still record
        # Hallucination separately if the matched pattern isn't auth-shaped, since
        # they're not mutually exclusive.
        if not any(_AUTH_LEAK_PATTERN_SIGNAL.search(r.pattern) for r in hit_not_include):
            categories.append("Hallucination")

    if (
        tool_calls
        and "Authorization Failure" not in categories
        and _get_orders_denied(tool_calls)
        and _DOLLAR_FACT_SIGNAL.search(answer)
    ):
        # A lookup was denied/not-found, yet the answer still states a specific
        # dollar figure -- the model fabricated an order fact it was never given.
        categories.append("Authorization Failure")

    if tool_calls and _tool_execution_errors(tool_calls):
        categories.append("Tool Execution Failure")

    route_correct = actual_route == expected_route
    if not route_correct:
        if expected_route == "escalate" or actual_route == "escalate":
            categories.append("Escalation Failure")
        else:
            categories.append("Tool Selection Failure")

    missing_include = [r for r in must_include_results if not r.matched]
    if missing_include and route_correct:
        # Only attribute a grounding-shaped category when routing itself was
        # right -- if routing was already wrong, missing facts are a downstream
        # symptom of that, not a separate root cause (avoid double-counting).
        if tool_calls:
            categories.append(_grounding_category(missing_include, tool_calls))
        elif expected_route in _ROUTE_HAS_POLICY and (
            actual_route in _ROUTE_HAS_POLICY if actual_route else False
        ):
            categories.append("Retrieval Failure")
        else:
            categories.append("Grounding Failure")

    if declared_route and actual_route is not None and declared_route != actual_route:
        categories.append("Prompt Failure")

    if not categories:
        categories.append("Unknown")

    return categories
