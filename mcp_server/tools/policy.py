"""search_policy tool -- hybrid (BM25 + vector) retrieval over the 12 policy docs,
served through FastAPI's /policy/search endpoint (see api/services/policy_service.py).
"""
from __future__ import annotations

from mcp_server import api_client
from mcp_server.auth_context import bearer_token
from mcp_server.mcp_instance import mcp


@mcp.tool(
    description=(
        "Search Sezzle's shopper policy documents (payment schedules, "
        "rescheduling, failed payments, refunds/returns, disputes, account "
        "reactivation, Sezzle Up credit reporting, virtual card, hardship "
        "assistance, fees, account security/fraud, merchant limits). Use this "
        "before stating any general policy rule -- do not rely on your own "
        "prior knowledge of BNPL policies, which may not match Sezzle's actual "
        "rules."
    )
)
async def search_policy(query: str, k: int = 4) -> dict:
    token = bearer_token()
    return await api_client.search_policy(token, query, k)
