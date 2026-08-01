"""Pydantic schemas for the evaluator. These are the JSON schema for report.json
(FastAPI-style: the model definitions *are* the schema, no separate spec to drift
out of sync)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class PatternResult(BaseModel):
    pattern: str
    matched: bool


class CaseEval(BaseModel):
    id: str
    question: str
    expected_route: str
    actual_route: Optional[str]
    route_correct: bool
    must_include: list[PatternResult]
    must_not_include: list[PatternResult]
    must_include_ok: bool
    must_not_include_ok: bool
    case_pass: bool
    failure_categories: list[str]
    answer: str
    call_trace: Optional[list[str]] = None  # present only if debug side-channel was found
    tool_calls: Optional[list[dict]] = None  # richer debug format: [{"name","args","result"}]
    declared_route: Optional[str] = None  # from finalize_answer, if the agent called it
    unauthorized_order_refs: list[str] = []  # ground-truth authorization check, see evaluator.py


class Metrics(BaseModel):
    total_cases: int
    route_accuracy: float
    must_include_accuracy: float
    must_not_include_accuracy: float
    overall_pass_rate: float


class RunReport(BaseModel):
    run_name: str
    generated_at: str
    cases_path: str
    answers_path: str
    debug_path_used: Optional[str] = None
    metrics: Metrics
    failure_category_counts: dict[str, int]
    cases: list[CaseEval]


class MetricDelta(BaseModel):
    metric: str
    run_a: float
    run_b: float
    delta: float


class ComparisonReport(BaseModel):
    run_a: str
    run_b: str
    generated_at: str
    metric_deltas: list[MetricDelta]
    improvements: list[str]  # case ids: fail -> pass
    regressions: list[str]  # case ids: pass -> fail
    still_failing: list[str]  # case ids: fail -> fail
    category_counts_a: dict[str, int]
    category_counts_b: dict[str, int]
