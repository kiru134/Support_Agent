#!/usr/bin/env python3
"""The one contract: reads a JSONL of {id, question, user_id}, writes a JSONL of
{id, route, answer}.

    python3 run_cases.py <cases.jsonl> <answers.jsonl>

Orchestrates the full production-shaped stack (FastAPI service + stateless FastMCP
server + LangGraph RAG agent) in a single process. `bootstrap.start_stack()` runs
real uvicorn and real FastMCP HTTP servers as background tasks -- not mocks, the
exact same code a real deployment runs -- which is what keeps this one command
reliable for grading regardless of how many services the production architecture
has (see DECISIONS.md, "Grading robustness").

Also writes an OPTIONAL debug side-channel next to answers.jsonl --
<answers_path stem>_debug.jsonl with {id, call_trace, tool_calls, declared_route}
per case (tool_calls includes each call's actual result, not just its name;
declared_route is what the model itself said via finalize_answer, which may be
empty if it never called that tool). This is strictly additive: the required
answers.jsonl contract above is unchanged in shape or content. evaluation/ uses the
debug file when present for finer-grained failure categorization (e.g. a tool
erroring vs. the wrong tool being chosen vs. the model ignoring context a tool
actually returned vs. the model's own stated routing disagreeing with what it did);
it degrades gracefully without it, and also reads older debug formats for backward
compatibility.

Requires Ollama running locally (`ollama serve`) with a tool-calling chat model and
an embedding model pulled -- see README.md.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from agent import graph_agent
from bootstrap import start_stack


def _debug_path(answers_path: str) -> Path:
    p = Path(answers_path)
    return p.with_name(f"{p.stem}_debug{p.suffix}")


async def _run_all(cases_path: str, answers_path: str) -> None:
    with open(cases_path) as f:
        cases = [json.loads(line) for line in f if line.strip()]

    stack = await start_stack()  # real Ollama chat + embeddings by default
    answers = []
    debug_rows = []
    try:
        for case in cases:
            try:
                result = await graph_agent.run(case["question"], case["user_id"])
                answers.append(
                    {"id": case["id"], "route": result["route"], "answer": result["answer"]}
                )
                debug_rows.append(
                    {
                        "id": case["id"],
                        "call_trace": result["call_trace"],
                        "tool_calls": result["tool_calls_detail"],
                        "declared_route": result.get("declared_route"),
                    }
                )
                print(f"[{case['id']}] route={result['route']} calls={result['call_trace']}", file=sys.stderr)
            except Exception as e:  # noqa: BLE001 -- one bad case must not kill the whole batch
                answers.append(
                    {"id": case["id"], "route": "escalate", "answer": f"[error running case: {e}]"}
                )
                debug_rows.append({"id": case["id"], "call_trace": [], "error": str(e)})
                print(f"[{case['id']}] FAILED: {e}", file=sys.stderr)
    finally:
        await stack.shutdown()

    with open(answers_path, "w") as f:
        for a in answers:
            f.write(json.dumps(a) + "\n")

    debug_path = _debug_path(answers_path)
    with open(debug_path, "w") as f:
        for d in debug_rows:
            f.write(json.dumps(d) + "\n")

    print(f"wrote {len(answers)} answers to {answers_path}", file=sys.stderr)
    print(f"wrote debug side-channel to {debug_path}", file=sys.stderr)


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: python3 run_cases.py <cases.jsonl> <answers.jsonl>", file=sys.stderr)
        sys.exit(1)
    asyncio.run(_run_all(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    main()
