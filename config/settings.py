"""Single source of truth for all service configuration -- a typed Pydantic
Settings model instead of scattered `os.environ.get()` calls, read from `.env`
(see `.env.example`). Every other module (auth, ollama_client, mcp_server, the
LangGraph agent, PolicyService) imports `settings` from here rather than reading
the environment directly.
"""
from __future__ import annotations

import secrets
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Auth / JWT ---
    # Generated once per process if not set in .env -- fine for this take-home
    # (single process), but a real multi-instance deployment needs a stable shared
    # secret (vault/KMS-issued) so tokens issued by one instance verify on another.
    jwt_secret: str = Field(default_factory=lambda: secrets.token_hex(32))
    jwt_algorithm: str = "HS256"
    jwt_expiry_seconds: int = 1800

    # --- FastAPI service ---
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    @property
    def api_base_url(self) -> str:
        return f"http://{self.api_host}:{self.api_port}"

    # --- FastMCP server ---
    # Stateless, network-addressable, so multiple agent processes can connect
    # concurrently -- each brings its own bearer token as a per-connection header
    # rather than the server holding any per-client state.
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8100
    mcp_path: str = "/mcp"

    @property
    def mcp_base_url(self) -> str:
        return f"http://{self.mcp_host}:{self.mcp_port}{self.mcp_path}"

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3:8b"
    ollama_embed_model: str = "nomic-embed-text"
    # Low temperature + a fixed seed make iteration runs comparable (run-to-run
    # diffs shouldn't be confounded by sampling noise on top of real prompt/code
    # changes). Not zero: a touch of temperature avoids degenerate repetition on
    # some local models; 0.15 was picked empirically, adjust if evidence says otherwise.
    ollama_temperature: float = 0.15
    ollama_seed: int = 42

    # --- ChromaDB / retrieval ---
    chroma_persist_dir: str = ".chroma"
    chroma_collection_name: str = "sezzle_policy_chunks"

    # --- Hybrid retrieval fusion ---
    retrieval_bm25_k: int = 8
    retrieval_vector_k: int = 8
    retrieval_rrf_k: int = 60  # standard RRF smoothing constant
    # Floor on search_policy's k regardless of what the model requests -- found
    # during iteration that a model-requested k=1 can miss a second relevant chunk
    # from the same doc (see ITERATION.md and PolicyService.search).
    retrieval_min_k: int = 3

    # --- Optional LLM-based reranking pass over the fused hybrid candidates ---
    # Off by default: it's one extra Ollama chat call per search_policy invocation,
    # which trades directly against the p95<=3s / 100k-per-day latency budget (see
    # DECISIONS.md). Enable where retrieval quality matters more than latency.
    retrieval_rerank_enabled: bool = False
    retrieval_rerank_candidates: int = 8

    # --- LangSmith (tracing + evals) ---
    # Off unless both a key and the enable flag are set -- this repo has no
    # LangSmith account/key available, so tracing/evals are wired but inert by
    # default. Set LANGSMITH_TRACING_ENABLED=true and LANGSMITH_API_KEY in .env to
    # turn it on; see langsmith_setup.py and langsmith_eval.py.
    langsmith_tracing_enabled: bool = False
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "sezzle-support-agent"
    langsmith_endpoint: str = "https://api.smith.langchain.com"


settings = Settings()
