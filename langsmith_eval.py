#!/usr/bin/env python3
"""Runs the golden visible cases as a LangSmith evaluation: uploads/reuses a
dataset, runs our LangGraph agent as the target, and scores each example with the
same must_include / must_not_include / route-match logic as score_answers.py --
but through LangSmith, so runs are traced and the eval report is viewable in the
LangSmith UI (not just a local table).

Requires LANGSMITH_API_KEY and langsmith_tracing_enabled=true in .env -- this repo
has no LangSmith account available, so this is wired and structurally correct but
UNVERIFIED against a real account; score_answers.py remains the actual eval
mechanism this project's iteration evidence is built on.

    python3 langsmith_eval.py
"""
from __future__ import annotations

import asyncio
import json
import re
import sys

from langsmith import Client
from langsmith.evaluation import aevaluate

from agent import graph_agent
from bootstrap import start_stack
from langsmith_setup import apply_langsmith_env

CASES_PATH = "sezzleaiengineertakehomechallenge/CASES_-_golden_visible.jsonl"
DATASET_NAME = "sezzle-support-agent-golden-visible"


def _load_cases() -> list[dict]:
    with open(CASES_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def _ensure_dataset(client: Client, cases: list[dict]) -> str:
    if client.has_dataset(dataset_name=DATASET_NAME):
        return DATASET_NAME
    dataset = client.create_dataset(
        DATASET_NAME, description="Sezzle support agent -- golden visible cases"
    )
    client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {
                "inputs": {"question": c["question"], "user_id": c["user_id"]},
                "outputs": {
                    "expected_route": c["expected_route"],
                    "must_include": c.get("must_include", []),
                    "must_not_include": c.get("must_not_include", []),
                },
                "metadata": {"case_id": c["id"]},
            }
            for c in cases
        ],
    )
    return DATASET_NAME


async def _target(inputs: dict) -> dict:
    result = await graph_agent.run(inputs["question"], inputs["user_id"])
    return {"route": result["route"], "answer": result["answer"]}


def _any_match(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def route_match(run, example) -> dict:
    got = run.outputs.get("route")
    want = example.outputs.get("expected_route")
    return {"key": "route_match", "score": int(got == want), "comment": f"got={got} want={want}"}


def must_include_ok(run, example) -> dict:
    text = run.outputs.get("answer", "")
    patterns = example.outputs.get("must_include", [])
    return {"key": "must_include", "score": int(all(_any_match([p], text) for p in patterns))}


def must_not_include_ok(run, example) -> dict:
    text = run.outputs.get("answer", "")
    patterns = example.outputs.get("must_not_include", [])
    return {"key": "must_not_include", "score": int(not any(_any_match([p], text) for p in patterns))}


async def main() -> None:
    if not apply_langsmith_env():
        print(
            "LangSmith tracing is not enabled -- set LANGSMITH_TRACING_ENABLED=true "
            "and LANGSMITH_API_KEY in .env first.",
            file=sys.stderr,
        )
        sys.exit(1)

    cases = _load_cases()
    client = Client()
    dataset_name = _ensure_dataset(client, cases)

    stack = await start_stack()
    try:
        results = await aevaluate(
            _target,
            data=dataset_name,
            evaluators=[route_match, must_include_ok, must_not_include_ok],
            experiment_prefix="sezzle-agent",
        )
        print(results)
    finally:
        await stack.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
