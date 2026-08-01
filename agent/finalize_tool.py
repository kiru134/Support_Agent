"""finalize_answer: a local (non-MCP) tool the model calls to declare its final
answer AND its own routing decision explicitly, instead of route being purely
reconstructed after the fact from call_trace.

This directly addresses a real critique raised during the build (see
DECISIONS.md/PROMPTS.md/ITERATION.md): deriving route only from which tools got
called means the model never explicitly commits to a routing decision, so its
"intent" and its "behavior" are indistinguishable -- there's no way to tell "chose
policy-only on purpose" from "never reasoned about routing at all."

This tool does NOT replace the verified route. graph_agent.py still computes
`route` from call_trace (the structural, unspoofable signal -- the model can't lie
about what it actually did) and treats the declared route as signal, not authority:
if they disagree, that disagreement itself becomes visible (declared_route is
recorded in the debug output, and evaluation/categorize.py flags a mismatch as a
Prompt Failure -- a concrete, auto-detectable proxy for "the model's own reasoning
was self-inconsistent").

Local rather than an MCP tool: it needs no backend data access, it's purely a
structural mechanism for capturing the model's own decision, so a network
round-trip through the stateless MCP server would be pure overhead.
"""
from __future__ import annotations

from typing import Literal

from langchain_core.tools import tool

FINALIZE_ANSWER_TOOL_NAME = "finalize_answer"


@tool
def finalize_answer(route: Literal["policy", "tool", "both", "escalate"], answer: str) -> str:
    """Call this LAST, once you have everything you need and are ready to give
    your final answer to the shopper. Declare which route this response actually
    used: 'policy' if you only called search_policy, 'tool' if you only called
    get_orders, 'both' if you called both, or 'escalate' if you called escalate.
    Put your complete final answer text in `answer` -- this is what the shopper
    sees. Always call this as your last step instead of just writing plain text."""
    return "recorded"
