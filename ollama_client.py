"""Low-level Ollama HTTP client -- stdlib only (urllib), no `requests` dependency.
Two raw operations: chat and embed. The LangGraph agent talks to Ollama through
`langchain_ollama.ChatOllama` directly (not this module) for its main chat loop;
this client is used by `api/services/policy_service.py` (embeddings) and
`reranker.py` (the optional LLM-based reranking pass), which have no reason to pull
in the LangChain message-object machinery for a single one-off call.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

from config.settings import settings

_READ_TIMEOUT = 60
_RETRIES = 2


def _post(path: str, payload: dict) -> dict:
    url = f"{settings.ollama_base_url}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    last_err: Optional[Exception] = None
    for attempt in range(_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=_READ_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
    raise ConnectionError(
        f"Could not reach Ollama at {settings.ollama_base_url} ({path}). "
        f"Is `ollama serve` running? Last error: {last_err}"
    )


def chat(
    messages: list[dict],
    tools: Optional[list[dict]] = None,
    model: str = None,
    temperature: Optional[float] = None,
    seed: Optional[int] = None,
) -> dict:
    payload = {
        "model": model or settings.ollama_chat_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": settings.ollama_temperature if temperature is None else temperature,
            "seed": settings.ollama_seed if seed is None else seed,
        },
    }
    if tools:
        payload["tools"] = tools
    return _post("/api/chat", payload)


def embed(texts: list[str], model: str = None) -> list[list[float]]:
    result = _post("/api/embed", {"model": model or settings.ollama_embed_model, "input": texts})
    return result["embeddings"]
