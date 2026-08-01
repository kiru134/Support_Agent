"""escalate tool -- a no-op signaling tool; calling it *is* the escalation
decision. No mutating tools exist anywhere in this package (no pause/waive/
reschedule/refund action) -- see DECISIONS.md for why that absence is what makes
certain false claims structurally impossible rather than merely discouraged.
"""
from __future__ import annotations

from mcp_server import api_client
from mcp_server.auth_context import bearer_token
from mcp_server.mcp_instance import mcp


@mcp.tool(
    description=(
        "Hand this conversation off to a human agent. Call this INSTEAD of "
        "answering yourself whenever the request involves: hardship/financial "
        "difficulty, a fraud or unauthorized-account report, a request for an "
        "exact decline reason or exact spending limit, or actually filing a "
        "dispute. Do not attempt to resolve these yourself, promise an "
        "outcome, or state specific numbers you don't have -- just escalate."
    )
)
async def escalate(reason: str = "") -> dict:
    token = bearer_token()
    return await api_client.escalate(token, reason)
