"""Optional LLM-based reranking pass over hybrid search candidates, reusing the
same Ollama chat model already in use elsewhere (no new dependency, no cross-encoder
model download). Gated by config.settings.retrieval_rerank_enabled (off by
default) -- see PolicyService and DECISIONS.md for why: it's one extra LLM call per
search_policy invocation, which trades against the p95<=3s / 100k-per-day latency
budget. Available to flip on where retrieval quality matters more than latency.
"""
from __future__ import annotations

import json

import ollama_client


def llm_rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    if not candidates:
        return candidates

    listing = "\n".join(
        f"[{i}] ({c['doc']} :: {c['heading']}) {c['text'][:200]}"
        for i, c in enumerate(candidates)
    )
    prompt = (
        f"Question: {query}\n\nCandidate policy passages:\n{listing}\n\n"
        f"Return a JSON array of the {top_k} most relevant passage indices, most "
        "relevant first. Only output the JSON array, nothing else."
    )
    # temperature=0.0 here is deliberate and independent of settings.ollama_temperature
    # -- reordering a fixed candidate list should be as deterministic as possible.
    result = ollama_client.chat([{"role": "user", "content": prompt}], temperature=0.0)
    content = result["message"].get("content", "")

    try:
        indices = json.loads(content[content.index("[") : content.rindex("]") + 1])
    except (ValueError, json.JSONDecodeError):
        return candidates[:top_k]

    out, seen = [], set()
    for i in indices:
        if isinstance(i, int) and 0 <= i < len(candidates) and i not in seen:
            out.append(candidates[i])
            seen.add(i)
        if len(out) >= top_k:
            break
    return out or candidates[:top_k]
