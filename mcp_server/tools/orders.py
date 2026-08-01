"""get_orders tool. No user_id parameter -- the model cannot ask for a different
identity; the caller's identity comes only from the request's bearer token (see
auth_context.bearer_token), forwarded to FastAPI where ownership is independently
re-verified.
"""
from __future__ import annotations

from mcp_server import api_client
from mcp_server.auth_context import bearer_token
from mcp_server.mcp_instance import mcp


@mcp.tool(
    description=(
        "Look up the authenticated shopper's own orders and installment "
        "schedules. Always returns pre-computed fields (unpaid balance, next "
        "upcoming installment, reschedules remaining, refund status) -- use "
        "these values directly rather than computing your own dates or sums. "
        "order_id also accepts a merchant name (e.g. 'Circuit City Lights') and "
        "will resolve it to that order if the shopper has exactly one order from "
        "that merchant -- prefer passing the merchant name directly if that's "
        "what the shopper gave you, rather than guessing an id-shaped string. If "
        "the shopper has MORE THAN ONE order from that merchant, this returns "
        "{'error': 'ambiguous', 'candidates': [...]} listing them with status/"
        "total/date -- if the shopper's own question already points at one "
        "candidate (e.g. they mention a missed/failed payment and exactly one "
        "candidate is payment_failed), proceed with that one but say plainly "
        "which order you assumed and why. Otherwise ask the shopper to clarify "
        "(mentioning the distinguishing details) as your final answer. If the "
        "lookup returns plain not_found instead (merchant "
        "not recognized), call again with NO order_id to list everything and "
        "match it yourself. Never invent a fake order_id like "
        "'MerchantName_order123' -- real ids look like 'ord_3006' and only ever "
        "come from a previous tool result. Only ever returns orders belonging to "
        "the current shopper; an order/merchant that doesn't match or belongs to "
        "someone else returns the same not_found result."
    )
)
async def get_orders(order_id: str = "") -> dict:
    token = bearer_token()
    if order_id:
        return await api_client.get_order(token, order_id)
    return await api_client.list_orders(token)
