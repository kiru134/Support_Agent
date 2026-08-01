"""Starts the FastAPI service (real uvicorn, real TCP port) and the FastMCP server
(real Streamable HTTP transport, stateless) as background tasks inside the current
process, so `run_cases.py` stays a single command with no manual multi-process
setup, while both servers are genuinely network-addressable -- not ASGI-in-memory
shortcuts. See DECISIONS.md, "Grading robustness vs. production shape".
"""
from __future__ import annotations

import asyncio
from typing import Callable, Optional

import httpx
import uvicorn

from api.main import create_app
from config.settings import settings
from langsmith_setup import apply_langsmith_env
from mcp_server import api_client
from mcp_server.server import run_async as run_mcp_async

EmbedFn = Callable[[list[str]], list[list[float]]]
RerankFn = Callable[[str, list[dict], int], list[dict]]


class RunningStack:
    def __init__(self, api_server: uvicorn.Server, api_task: asyncio.Task, mcp_task: asyncio.Task):
        self.api_server = api_server
        self.api_task = api_task
        self.mcp_task = mcp_task

    async def shutdown(self) -> None:
        self.api_server.should_exit = True
        await self.api_task
        self.mcp_task.cancel()
        try:
            await self.mcp_task
        except asyncio.CancelledError:
            pass
        await api_client.aclose_http_client()


async def _wait_for_health(url: str, timeout: float = 20.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    async with httpx.AsyncClient() as client:
        while True:
            try:
                r = await client.get(url, timeout=2.0)
                if r.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            if asyncio.get_event_loop().time() > deadline:
                raise TimeoutError(f"{url} did not become healthy in {timeout}s")
            await asyncio.sleep(0.2)


async def start_stack(
    embed_fn: Optional[EmbedFn] = None,
    rerank_fn: Optional[RerankFn] = None,
    persist_dir: Optional[str] = settings.chroma_persist_dir,
) -> RunningStack:
    """`persist_dir=None` uses an ephemeral in-memory Chroma collection -- pass
    that explicitly from tests/experiments using a non-default embed_fn (e.g. a
    fake embedding function), so they can't silently write mismatched-dimension
    vectors into the real persistent store other runs (and run_cases.py) share."""
    if apply_langsmith_env():
        print("LangSmith tracing enabled (project=%s)" % settings.langsmith_project)

    app = create_app(embed_fn=embed_fn, rerank_fn=rerank_fn, persist_dir=persist_dir)
    config = uvicorn.Config(
        app, host=settings.api_host, port=settings.api_port, log_level="warning"
    )
    api_server = uvicorn.Server(config)
    api_task = asyncio.create_task(api_server.serve())

    mcp_task = asyncio.create_task(run_mcp_async())

    await _wait_for_health(f"{settings.api_base_url}/health")
    # FastMCP has no bare /health path by default; give it a moment to bind its
    # socket rather than polling an endpoint that doesn't exist.
    await asyncio.sleep(0.5)

    return RunningStack(api_server, api_task, mcp_task)
