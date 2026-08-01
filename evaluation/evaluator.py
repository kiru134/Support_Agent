"""Orchestrates a single evaluation run: pairs cases with answers (and the optional
debug side-channel), scores each case, categorizes failures, aggregates metrics --
produces a RunReport. No LLM anywhere in this module or the ones it calls.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from evaluation.categorize import categorize
from evaluation.matching import (
    eval_must_include,
    eval_must_not_include,
    must_include_ok as _must_include_ok,
    must_not_include_ok as _must_not_include_ok,
)
from evaluation.metrics import compute_category_counts, compute_metrics
from evaluation.models import CaseEval, RunReport
from orders_store import OrdersStore

_ORDER_ID_PATTERN = re.compile(r"\bord_\d+\b")


def _read_jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _unauthorized_order_refs(answer: str, user_id: str, store: OrdersStore) -> list[str]:
    """Ground-truth authorization check: any real order id mentioned in the answer
    that does NOT belong to this case's user_id. Uses the same DATA-orders.json
    ownership data the actual system enforces against -- not a proxy, a direct
    cross-reference. An id that doesn't exist in the dataset at all is ignored here
    (that's either a hallucinated id, already caught by other checks, or just not
    a security-relevant signal on its own)."""
    mentioned = set(_ORDER_ID_PATTERN.findall(answer))
    return [oid for oid in mentioned if store.owner_of(oid) not in (None, user_id)]


def _debug_path_for(answers_path: str) -> Path:
    p = Path(answers_path)
    return p.with_name(f"{p.stem}_debug{p.suffix}")


def evaluate_run(cases_path: str, answers_path: str, run_name: str) -> RunReport:
    cases = {c["id"]: c for c in _read_jsonl(cases_path)}
    answers = {a["id"]: a for a in _read_jsonl(answers_path)}
    store = OrdersStore()  # ground truth for the Authorization Failure check below

    debug_path = _debug_path_for(answers_path)
    call_traces: dict[str, list[str]] = {}
    tool_calls_by_id: dict[str, list[dict]] = {}
    declared_routes: dict[str, str] = {}
    debug_path_used: Optional[str] = None
    if debug_path.exists():
        debug_path_used = str(debug_path)
        for row in _read_jsonl(str(debug_path)):
            call_traces[row["id"]] = row.get("call_trace", [])
            if "tool_calls" in row:  # richer format; absent in older debug files
                tool_calls_by_id[row["id"]] = row["tool_calls"]
            if row.get("declared_route"):  # only present once finalize_answer is in use
                declared_routes[row["id"]] = row["declared_route"]

    case_evals: list[CaseEval] = []
    for case_id, case in cases.items():
        answer_row = answers.get(case_id)
        actual_route = answer_row.get("route") if answer_row else None
        answer_text = answer_row.get("answer", "") if answer_row else ""

        must_include_results = eval_must_include(case.get("must_include", []), answer_text)
        must_not_include_results = eval_must_not_include(case.get("must_not_include", []), answer_text)
        route_correct = actual_route == case["expected_route"]
        m_ok = _must_include_ok(must_include_results)
        mn_ok = _must_not_include_ok(must_not_include_results)
        # Ground-truth authorization check, independent of whether this golden
        # case's own must_not_include regex happens to test for it -- a real
        # cross-account order reference is a failure regardless.
        unauthorized_refs = _unauthorized_order_refs(answer_text, case["user_id"], store)
        case_pass = route_correct and m_ok and mn_ok and not unauthorized_refs

        failure_categories: list[str] = []
        if answer_row is None:
            failure_categories = ["Output Formatting"]
        elif not case_pass:
            failure_categories = categorize(
                expected_route=case["expected_route"],
                actual_route=actual_route,
                answer=answer_text,
                must_include_results=must_include_results,
                must_not_include_results=must_not_include_results,
                call_trace=call_traces.get(case_id),
                tool_calls=tool_calls_by_id.get(case_id),
                unauthorized_order_refs=unauthorized_refs,
                declared_route=declared_routes.get(case_id),
            )

        case_evals.append(
            CaseEval(
                id=case_id,
                question=case["question"],
                expected_route=case["expected_route"],
                actual_route=actual_route,
                route_correct=route_correct,
                must_include=must_include_results,
                must_not_include=must_not_include_results,
                must_include_ok=m_ok,
                must_not_include_ok=mn_ok,
                case_pass=case_pass,
                failure_categories=failure_categories,
                answer=answer_text,
                call_trace=call_traces.get(case_id),
                tool_calls=tool_calls_by_id.get(case_id),
                declared_route=declared_routes.get(case_id),
                unauthorized_order_refs=unauthorized_refs,
            )
        )

    return RunReport(
        run_name=run_name,
        generated_at=datetime.now(timezone.utc).isoformat(),
        cases_path=cases_path,
        answers_path=answers_path,
        debug_path_used=debug_path_used,
        metrics=compute_metrics(case_evals),
        failure_category_counts=compute_category_counts(case_evals),
        cases=case_evals,
    )
