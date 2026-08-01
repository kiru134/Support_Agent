"""FastAPI app factory. `create_app` takes an injectable `embed_fn` so tests (and
`run_cases.py`) can control exactly when/whether real Ollama calls happen, and so
the app is constructed fresh per test run rather than relying on module-level
globals.
"""
from __future__ import annotations

from typing import Callable, Optional

from fastapi import FastAPI

from api.auth.routes import router as auth_router
from api.controllers.escalation_controller import router as escalation_router
from api.controllers.orders_controller import router as orders_router
from api.controllers.policy_controller import router as policy_router
from api.deps import configure_services
from api.services.escalation_service import EscalationService
from api.services.order_service import OrderService
from api.services.policy_service import PolicyService
from config.settings import settings
from orders_store import OrdersStore

EmbedFn = Callable[[list[str]], list[list[float]]]
RerankFn = Callable[[str, list[dict], int], list[dict]]


def create_app(
    embed_fn: Optional[EmbedFn] = None,
    persist_dir: Optional[str] = settings.chroma_persist_dir,
    store: Optional[OrdersStore] = None,
    rerank_fn: Optional[RerankFn] = None,
) -> FastAPI:
    if embed_fn is None:
        from ollama_client import embed as embed_fn  # deferred: avoid requiring Ollama at import time
    if rerank_fn is None:
        from reranker import llm_rerank as rerank_fn  # deferred: same reason, only used if enabled

    app = FastAPI(title="Sezzle Support Assistant API")

    order_service = OrderService(store or OrdersStore())
    policy_service = PolicyService(embed_fn=embed_fn, persist_dir=persist_dir, rerank_fn=rerank_fn)
    escalation_service = EscalationService()
    configure_services(order_service, policy_service, escalation_service)

    app.include_router(auth_router)
    app.include_router(orders_router)
    app.include_router(policy_router)
    app.include_router(escalation_router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app
