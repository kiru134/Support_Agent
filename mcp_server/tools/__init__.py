"""Importing this package registers all tools against mcp_server.mcp_instance.mcp
(each submodule's @mcp.tool() decorator runs on import) -- server.py imports this
package for that side effect before starting the transport.
"""
from mcp_server.tools import escalation, orders, policy  # noqa: F401
