"""Entrypoint for the stateless FastMCP server: imports the shared `mcp` instance,
imports mcp_server.tools (registers get_orders / search_policy / escalate against
it), and runs it over the Streamable HTTP transport with stateless_http=True -- no
per-connection session state held server-side, so any number of agent processes (or
concurrent requests from one agent) can connect to the same running server. Identity
travels as a request-scoped Authorization header (see mcp_server/auth_context.py),
not as a tool parameter -- the model can never ask for a different identity because
no tool schema has one.
"""
from __future__ import annotations

from mcp_server import tools  # noqa: F401 -- import registers tools against `mcp`
from mcp_server.mcp_instance import mcp
from config.settings import settings


async def run_async() -> None:
    await mcp.run_async(
        transport="http",
        host=settings.mcp_host,
        port=settings.mcp_port,
        path=settings.mcp_path,
        stateless_http=True,
        show_banner=False,
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_async())
