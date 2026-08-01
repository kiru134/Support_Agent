# Decision Records

## 1. Retrieval: hybrid BM25 + vector, RRF-fused, reranking optional and off

**Options:** pure BM25 (precise, misses paraphrase); pure vector (closes paraphrase
gaps, drifts on short term-heavy queries); full-context stuffing (fine at 12 docs,
wasteful at scale); hybrid.
**Chosen:** BM25 (stdlib) + ChromaDB vector (Ollama-served embeddings, stays local)
fused via RRF, `k=4` since some cases need chunks from two docs. Optional LLM
reranker exists but ships **off by default** — one more Ollama round-trip per
search is a real cost against the p95≤3s/100k-per-day budget.
**Evidence that would change my mind:** hidden-set recall misses hybrid doesn't
catch — would justify enabling reranking for that slice.

## 2. Authorization, escalation & route: model declares, the system verifies

**Options:** trust the model's judgment alone (fails the hostile-input bar); a hard
pre-classifier (violates "LLM must be structurally load-bearing"); a purely-inferred
route with no visibility into the model's own stated intent.
**Chosen:** authorization enforced twice, independently — no `user_id` tool param,
plus FastAPI re-verifies against the JWT claim (now checked against real
`DATA-orders.json` ownership in the evaluator, not just a golden case's regex).
Route: the model *declares* it (`finalize_answer` tool) but the *verified* route
(from `call_trace`, unfakeable) stays authoritative — disagreement is itself a
detected category (Prompt Failure). Escalation is model-driven, backed by a regex
safety net that nudges a retry, not a silent override.
**Evidence that would change my mind:** a high safety-net trigger rate, or a high
declared/verified mismatch rate — either would mean the net, not the model, is
doing the real work.

## 3. Production architecture & cost/latency, built ahead of present need

**Options:** ship the lean batch script the contract actually requires; build the
full shape (FastAPI + stateless FastMCP + LangGraph) now, before a second consumer
exists.
**Chosen:** the full shape, at explicit direction — so a reviewer evaluating "swap
in a cloud model" has less work to do, a different justification from "multiple
consumers exist" (they don't yet). MCP is a protocol, not a security boundary; the
same auth property holds in-process or behind it. `run_cases.py` still launches
everything (real uvicorn + real FastMCP HTTP) in one process so grading stays one
command. At 100k q/day, ~$50/day → **$0.0005/question** — local CPU Ollama can't
hit p95≤3s at that scale; production needs a hosted model behind a batching server
with a cached system prompt.
**Evidence that would change my mind:** a second real MCP consumer appearing.
