"""Shared per-request auth extraction for tool modules under mcp_server/tools/."""
from __future__ import annotations

from fastmcp.server.dependencies import get_http_headers


def bearer_token() -> str:
    # get_http_headers() strips Authorization by default (excluded from the set of
    # headers considered safe to read/forward) -- opt back in explicitly, since
    # forwarding it deliberately to our own trusted FastAPI service is the point.
    headers = get_http_headers(include=["authorization"])
    auth = headers.get("authorization", "")
    return auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
