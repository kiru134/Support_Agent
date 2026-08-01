"""The shared FastMCP server instance. Split out from server.py so tool modules
under mcp_server/tools/ can import and register against it (`@mcp.tool()`) without
a circular import back to server.py, which owns run_async()/transport concerns.
"""
from __future__ import annotations

from fastmcp import FastMCP

mcp = FastMCP(name="sezzle-support-tools")
