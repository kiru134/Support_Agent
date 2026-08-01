"""Thin httpx wrapper the MCP tools use to call the FastAPI service, forwarding the
caller's bearer token as a real Authorization header on every request -- so FastAPI
independently re-verifies ownership regardless of what the MCP layer does.

A single shared httpx.AsyncClient (connection-pooled, pointed at
settings.api_base_url) is reused across all requests; the per-caller bearer token is
passed as a header on each individual call, not baked into a per-client instance --
that's what keeps this compatible with a stateless MCP server serving concurrent
callers with different identities.
"""
from __future__ import annotations

import httpx

from config.settings import settings

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=settings.api_base_url, timeout=30.0)
    return _client


async def aclose_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


async def list_orders(token: str) -> dict:
    client = get_http_client()
    r = await client.get("/orders", headers=_auth_headers(token))
    r.raise_for_status()
    return r.json()


async def get_order(token: str, order_id: str) -> dict:
    client = get_http_client()
    r = await client.get(f"/orders/{order_id}", headers=_auth_headers(token))
    if r.status_code == 404:
        detail = r.json().get("detail", "not_found")
        # FastAPI's HTTPException.detail is either a bare string ("not_found") or
        # the richer {"error": "ambiguous", "candidates": [...]} dict from
        # orders_controller.py -- forward whichever it is as-is.
        return detail if isinstance(detail, dict) else {"error": detail}
    r.raise_for_status()
    return r.json()


async def search_policy(token: str, query: str, k: int = 4) -> dict:
    client = get_http_client()
    r = await client.get(
        "/policy/search", params={"q": query, "k": k}, headers=_auth_headers(token)
    )
    r.raise_for_status()
    return r.json()


async def escalate(token: str, reason: str) -> dict:
    client = get_http_client()
    r = await client.post(
        "/escalate", json={"reason": reason}, headers=_auth_headers(token)
    )
    r.raise_for_status()
    return r.json()
