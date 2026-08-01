# Sezzle Support Agent

An LLM-powered support assistant for Sezzle (BNPL) shopper questions, built to a
production-representative shape: a FastAPI service (auth + REST), a stateless
FastMCP tool server, a LangGraph RAG agent over local Ollama, ChromaDB hybrid
retrieval, and a guardrail layer.

- **`DECISIONS.md`** — the three decisions worth defending in the follow-up interview.
- **`PROMPTS.md`** — the prompts used to build this, and the prompts inside the system.
- **`ITERATION.md`** — first run → diagnosis → change → measured delta.
- This file — how to actually run everything.

## 1. Prerequisites

- **Python 3.10+**. This repo was built and is verified against **3.11**, installed
  via [`uv`](https://docs.astral.sh/uv/) (`uv python install 3.11`) — needed because
  `fastmcp`/`mcp` require ≥3.10 and this machine's system Python was 3.9.
- **[Ollama](https://ollama.com)**, running locally, with two models pulled:
  ```
  ollama pull qwen3:8b            # tool-calling chat model
  ollama pull nomic-embed-text    # embedding model for policy retrieval
  ```
  Any tool-calling-capable chat model works — set `OLLAMA_CHAT_MODEL` in `.env` if
  you use a different one (e.g. `qwen2.5:7b-instruct`, `llama3.1:8b`). Verify Ollama
  is actually reachable before running anything:
  ```
  curl http://localhost:11434/api/tags
  ```

## 2. Install

```
uv sync
```
This creates `.venv/` and installs everything pinned in `uv.lock` (generated from
`pyproject.toml`). If you'd rather not use `uv`: create a venv with Python 3.10+
yourself and `pip install` the packages listed under `[project.dependencies]` in
`pyproject.toml`.

```
cp .env.example .env
```
Optional — every setting has a working default in `config/settings.py`; `.env` only
needs entries for what you want to override (model names, ports, LangSmith key, etc).

## 3. Run the one contract

```
source .venv/bin/activate
python3 run_cases.py sezzleaiengineertakehomechallenge/CASES_-_golden_visible.jsonl runs/answers.jsonl
```

This single command starts the **entire stack** — a real `uvicorn` FastAPI server
and a real FastMCP HTTP server, both launched as background tasks inside this one
process (`bootstrap.py`) — runs each case through the LangGraph agent, and writes
`answers.jsonl` in the required `{id, route, answer}` shape. It also writes an
**optional** `<name>_debug.jsonl` alongside it (e.g. `answers_debug.jsonl`) with
each case's tool-call trace *and* each tool call's actual result — used by the
evaluator for finer-grained failure categorization. Nothing about the required
contract depends on that file existing.

Expect roughly 1–1.5 minutes per case on CPU-only local inference for an 8B model
(10 cases ≈ 10–15 minutes) — this is a stated, honest limitation, see
`DECISIONS.md` §3 on what changes at production scale.

## 4. Evaluate a run

```
python3 evaluate_run.py sezzleaiengineertakehomechallenge/CASES_-_golden_visible.jsonl runs/answers.jsonl my_run
# writes reports/my_run/report.json and reports/my_run/report.md
```
Scores route accuracy, `must_include`/`must_not_include` regex compliance, and
categorizes failures (Retrieval Failure, Tool Selection Failure, Hallucination,
Grounding Failure, Authorization Failure, Escalation Failure, Tool Execution
Failure, Output Formatting, Unknown) deterministically — no LLM inside the
evaluator. Read `reports/my_run/report.md` for the human-readable version.

**Compare two runs** (e.g. first vs. final):
```
python3 compare_runs.py reports/run1/report.json reports/final/report.json
# writes reports/run1_vs_final/comparison.json and comparison.md
```
Metric deltas, which cases flipped pass→fail or fail→pass, and failure-category
shifts between the two.

A lighter, older scorer (`score_answers.py <cases.jsonl> <answers.jsonl>`) still
exists alongside the full evaluator for a quick pass/fail table without reports.

## 5. Running the services standalone (the actual production shape)

`run_cases.py` runs everything in one process for grading reliability (see
`DECISIONS.md` §3), but the exact same code also runs as real, independent
processes — this is how it would actually deploy:

```
# terminal 1
uvicorn api.main:app --host 127.0.0.1 --port 8000

# terminal 2
python3 -m mcp_server.server

# terminal 3 -- exercise it directly
curl -X POST http://127.0.0.1:8000/auth/token -d '{"user_id":"u002"}' -H 'Content-Type: application/json'
```
The FastMCP server is stateless (`stateless_http=True`) — any number of agent
processes can connect to the one running instance concurrently, each bringing its
own bearer token as a per-connection header.

## 6. LangSmith (optional — tracing + hosted evals)

Wired but **inert by default** — no LangSmith account/API key exists in this
environment. To turn it on:

1. Sign up at [smith.langchain.com](https://smith.langchain.com) and create an API key.
2. Add to `.env`:
   ```
   LANGSMITH_TRACING_ENABLED=true
   LANGSMITH_API_KEY=ls__your_key_here
   LANGSMITH_PROJECT=sezzle-support-agent
   ```
3. Run `run_cases.py` as normal — traces upload automatically (`bootstrap.py` calls
   `langsmith_setup.apply_langsmith_env()` at startup, no code changes needed).
4. For a hosted eval experiment (dataset + evaluators, not just traces):
   ```
   python3 langsmith_eval.py
   ```
   Uploads the golden cases as a LangSmith dataset and runs the same
   route/must_include/must_not_include evaluators there, viewable under
   **Datasets & Experiments** in your LangSmith project.

## 7. Project layout

```
run_cases.py          the one contract
bootstrap.py           starts real uvicorn + real FastMCP HTTP in-process
config/settings.py      typed config, reads .env
orders_store.py         DATA-orders.json -> Pydantic models + derived fields
retrieval.py            BM25 index (also the chunking source for Chroma)
ollama_client.py         low-level Ollama HTTP client (embed, + chat for reranker)
reranker.py             optional LLM-based reranking pass (off by default)

api/                    FastAPI service -- Model-Controller-Service
  main.py auth/ models/ controllers/ services/

mcp_server/              stateless FastMCP tool server
  server.py mcp_instance.py auth_context.py api_client.py tools/

agent/                   the RAG agent
  graph_agent.py (LangGraph StateGraph) finalize_tool.py guardrails.py prompts.py

evaluation/               deterministic eval framework (no LLM inside it)
  evaluator.py categorize.py matching.py metrics.py report_json.py report_markdown.py compare.py
evaluate_run.py compare_runs.py score_answers.py

runs/                    answers.jsonl + debug side-channel per run
reports/                  evaluator output (report.json/.md per run, comparisons)
```

## 8. Troubleshooting

- **`ConnectionError: Could not reach Ollama`** — `ollama serve` isn't running, or
  `OLLAMA_BASE_URL` in `.env` doesn't match where it's listening.
- **`chromadb.errors.InvalidArgumentError: ... dimension of X, got Y`** — the
  persisted `.chroma/` collection was built with a different embedding model than
  the one currently configured. Delete `.chroma/` and re-run; it rebuilds from the
  policy docs automatically on first use.
- **`ImportError` for `fastmcp`/`mcp`** — you're on Python <3.10. Use `uv python
  install 3.11` and rebuild the venv against it (see Prerequisites).
- **A single case fails but the run keeps going** — `run_cases.py` catches
  per-case exceptions so one bad case doesn't kill the batch; check stderr for
  `[<id>] FAILED: ...` and the corresponding entry in `answers.jsonl` will have
  `route: "escalate"` and an `[error running case: ...]` answer, which
  `evaluate_run.py` categorizes as **Output Formatting**.

## What was fixed during iteration (previously listed here as unfinished)

- **Route is now declared, not just inferred.** The agent has a local
  `finalize_answer(route, answer)` tool (`agent/finalize_tool.py`) the model calls
  as its last step, explicitly stating which route it used. The *verified* route
  (derived from `call_trace`, which the model can't fake) is still authoritative in
  `answers.jsonl` — but the declared route is recorded in the debug side-channel,
  and a disagreement between the two is now an auto-detected **Prompt Failure**
  signal in the evaluator: concrete evidence the model's own stated reasoning
  didn't match its behavior.
- **Authorization Failure detection is now ground-truth-based**, not just a regex
  proxy. `evaluation/evaluator.py` cross-references any order id mentioned in an
  answer against the real `DATA-orders.json` ownership data for that case's
  `user_id` — a genuine cross-account reference fails the case outright, regardless
  of whether the golden case's own `must_not_include` pattern happened to test for it.
- **Chunking Failure is now auto-detected**, split from Retrieval Failure using the
  full policy corpus: if a missing fact exists in some chunk but wasn't retrieved
  for this query, that's Retrieval Failure; if it exists in the raw document but no
  single produced chunk contains it, that's Chunking Failure (a chunk-boundary
  problem). Prompt Failure (above) is the one concrete signal available for that
  category without reading transcripts by hand.
- **Multi-order ambiguity is now handled.** `get_orders` distinguishes "doesn't
  exist / not yours" (generic `not_found`, no oracle) from "matches more than one
  of your own orders" (`{"error": "ambiguous", "candidates": [...]}` — safe to
  disclose, since it never crosses accounts) and the system prompt instructs the
  model to ask a clarifying question rather than guess or give up.

## What's still honestly unfinished

- **`escalate` is a logging no-op** — no real ticketing system behind it.
- **Reranking is implemented but off by default** (`RETRIEVAL_RERANK_ENABLED=true`
  to try it) — an extra Ollama call per policy search is a real latency cost against
  the stated p95≤3s budget.
- **Prompt Failure is a narrow proxy**, not a general detector: it only fires on
  declared-vs-verified route disagreement. A model that reasons badly but stays
  internally consistent (declares the same wrong route it acted on) won't be caught
  by this — that still needs a human transcript read.
- **`finalize_answer` isn't force-called.** Some models won't reliably call it every
  turn; the graph falls back to treating plain text as the answer with no declared
  route recorded, rather than looping forever waiting for a tool call that may never
  come. This is a robustness tradeoff, not a bug — see `agent/graph_agent.py`.
- **Local model quality is the single biggest open risk.** An 8B model on CPU is
  slower and less reliable than a hosted model at the traps that matter most — see
  `ITERATION.md` for exactly where this showed up and what was changed in response.
