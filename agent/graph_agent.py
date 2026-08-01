"""The RAG agent, as a LangGraph StateGraph.

Nodes:
  agent      -- ChatOllama (bound to the MCP tools + finalize_answer) proposes the
                next step: a tool call, or a call to finalize_answer.
  tools      -- executes any MCP tool calls via the stateless FastMCP server (over
                langchain-mcp-adapters), records them into call_trace.
  finalize   -- runs when the model calls finalize_answer: extracts its declared
                route + answer text into state, then always proceeds to guardrail.
  guardrail  -- runs once the model is done: escalation safety net + output
                validation. Either finalizes (route VERIFIED from call_trace, not
                just taken on the model's word) or appends a corrective nudge and
                loops back to `agent`, bounded by MAX_CORRECTIVE_ROUNDS.

`route` in the final output is still derived from call_trace -- which tools the
model actually called -- never trusted purely from what it declared. The model's
declared route (via finalize_answer) is recorded alongside it as a *second*
signal: agreement is unremarkable, but disagreement means the model's own stated
reasoning didn't match its behavior, which is exactly the gap a purely-inferred
route couldn't see (see DECISIONS.md/ITERATION.md). If the model never calls
finalize_answer at all (some models won't reliably do this), the graph falls back
to treating its plain-text response as the answer with no declared_route --
robustness over forcing tool use that isn't guaranteed.
"""
from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StreamableHttpConnection
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from agent.finalize_tool import FINALIZE_ANSWER_TOOL_NAME, finalize_answer
from agent.guardrails import (
    ESCALATION_FALLBACK_TEMPLATE,
    detect_escalation_signal,
    validate_output,
)
from agent.prompts import FEW_SHOTS, SYSTEM_PROMPT
from config.settings import settings

MAX_TOOL_ROUNDS = 4
MAX_CORRECTIVE_ROUNDS = 2


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    call_trace: list[str]
    tool_calls_detail: list[dict]  # [{"name", "args", "result"}, ...] -- richer than
    # call_trace's names-only list; feeds the evaluator's finer failure
    # categorization (tool errors vs. wrong tool chosen vs. context ignored).
    question: str
    rounds: int
    corrective_rounds: int
    route: str
    answer: str
    declared_route: str  # from finalize_answer, empty if never called


def _derive_route(call_trace: list[str], question: str) -> str:
    if "escalate" in call_trace:
        return "escalate"
    has_policy = "search_policy" in call_trace
    has_orders = "get_orders" in call_trace
    if has_policy and has_orders:
        return "both"
    if has_policy:
        return "policy"
    if has_orders:
        return "tool"
    return "escalate" if detect_escalation_signal(question) else "policy"


async def _get_token(user_id: str) -> str:
    import httpx

    async with httpx.AsyncClient(base_url=settings.api_base_url) as client:
        r = await client.post("/auth/token", json={"user_id": user_id})
        r.raise_for_status()
        return r.json()["access_token"]


def _build_graph(llm, llm_with_tools, tools_node: ToolNode):
    async def agent_node(state: AgentState) -> dict:
        rounds = state["rounds"] + 1
        if rounds > MAX_TOOL_ROUNDS:
            # Round cap reached and the model was still calling tools -- drop tool-
            # calling ability so it's forced to answer with what it already has,
            # bounding worst-case latency instead of looping forever.
            forced = state["messages"] + [
                HumanMessage(content="Please answer now, using only the information you've already gathered.")
            ]
            response = await llm.ainvoke(forced)
        else:
            response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response], "rounds": rounds}

    async def tools_call_node(state: AgentState) -> dict:
        last = state["messages"][-1]
        pending_calls = getattr(last, "tool_calls", [])
        names = [tc["name"] for tc in pending_calls]
        result = await tools_node.ainvoke(state)

        # Pair each new ToolMessage (in the same order as the tool_calls that
        # produced them) with its originating name/args, so the evaluator can see
        # not just *that* a tool was called but *what it returned*.
        detail = []
        for tc, msg in zip(pending_calls, result["messages"]):
            detail.append(
                {"name": tc["name"], "args": tc.get("args", {}), "result": str(getattr(msg, "content", ""))}
            )

        return {
            "messages": result["messages"],
            "call_trace": state["call_trace"] + names,
            "tool_calls_detail": state["tool_calls_detail"] + detail,
        }

    def route_after_agent(state: AgentState) -> Literal["tools", "finalize", "guardrail"]:
        # Hard ceiling regardless of what the model returned: the forced-final-
        # answer call (rounds > MAX_TOOL_ROUNDS) is expected to omit tool_calls
        # since it's made without bound tools, but that's a property of the model,
        # not something this graph should trust blindly -- a structural cap here
        # is what actually bounds worst-case latency.
        if state["rounds"] > MAX_TOOL_ROUNDS:
            return "guardrail"
        last = state["messages"][-1]
        pending = getattr(last, "tool_calls", None) if isinstance(last, AIMessage) else None
        if pending and any(tc["name"] == FINALIZE_ANSWER_TOOL_NAME for tc in pending):
            return "finalize"
        if pending:
            return "tools"
        # No tool calls at all -- plain-text response. Some models won't reliably
        # call finalize_answer every time; fall back to treating this as the
        # answer directly (declared_route stays unset) rather than looping forever
        # waiting for a tool call that may never come.
        return "guardrail"

    def finalize_node(state: AgentState) -> dict:
        last = state["messages"][-1]
        call = next(tc for tc in last.tool_calls if tc["name"] == FINALIZE_ANSWER_TOOL_NAME)
        args = call.get("args", {})
        return {"answer": args.get("answer", ""), "declared_route": args.get("route", "")}

    async def guardrail_node(state: AgentState) -> dict:
        last = state["messages"][-1]
        # If finalize_node already set an answer (the model called
        # finalize_answer), use that; otherwise fall back to the last plain-text
        # AIMessage content (finalize_answer was never called).
        answer = state.get("answer") or ((last.content or "").strip() if isinstance(last, AIMessage) else "")
        question = state["question"]
        call_trace = state["call_trace"]
        corrective_rounds = state["corrective_rounds"]

        # Escalation safety net: model-driven judgment is primary; this only nudges
        # if a strong category signal was missed, never silently overrides.
        signal = detect_escalation_signal(question)
        signal_missed = bool(signal) and "escalate" not in call_trace
        budget_left = corrective_rounds < MAX_CORRECTIVE_ROUNDS

        if signal_missed and budget_left:
            nudge = SystemMessage(
                content=(
                    f"(System note: this request matches the '{signal}' category, "
                    "which policy requires escalating to a human agent. Call the "
                    "escalate tool now instead of answering directly.)"
                )
            )
            # Clear answer/declared_route: without this, a stale finalize_answer
            # from before the nudge could leak through as the final answer if the
            # model's next turn produces plain text instead of calling
            # finalize_answer again.
            return {"messages": [nudge], "corrective_rounds": corrective_rounds + 1, "answer": "", "declared_route": ""}

        violations = validate_output(answer)
        if violations and budget_left:
            nudge = SystemMessage(
                content=(
                    f"(System note: your last answer had a problem: {violations}. "
                    "You claimed an action no tool actually performed, or stated "
                    "an exact number you don't have. Rewrite the answer without "
                    "doing that -- describe policy/options only, or escalate.)"
                )
            )
            return {"messages": [nudge], "corrective_rounds": corrective_rounds + 1, "answer": "", "declared_route": ""}

        # Corrective budget exhausted. This unconditional check is the fix for a
        # real gap found during iteration: a model can produce prose that *claims*
        # escalation ("I'm connecting you with a human agent...") without ever
        # calling the escalate tool -- that text doesn't match validate_output's
        # false-action-claim patterns, so without this check the loop would just
        # finalize on whatever call_trace exists, silently mis-routing a case that
        # should have escalated. Both fallback triggers are logged since their rate
        # is itself honest iteration evidence.
        if signal_missed or violations:
            answer = ESCALATION_FALLBACK_TEMPLATE.format(extra="")
            if "escalate" not in call_trace:
                call_trace = call_trace + ["escalate"]

        route = _derive_route(call_trace, question)
        return {"answer": answer, "route": route, "call_trace": call_trace}

    def route_after_guardrail(state: AgentState) -> Literal["agent", "__end__"]:
        return "agent" if not state.get("route") else END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_call_node)
    graph.add_node("finalize", finalize_node)
    graph.add_node("guardrail", guardrail_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent", route_after_agent, {"tools": "tools", "finalize": "finalize", "guardrail": "guardrail"}
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", "guardrail")
    graph.add_conditional_edges("guardrail", route_after_guardrail, {"agent": "agent", END: END})
    return graph.compile()


async def run(question: str, user_id: str) -> dict:
    """Requires the FastAPI service + stateless FastMCP server already running
    (see bootstrap.start_stack) and Ollama reachable."""
    token = await _get_token(user_id)

    mcp_client = MultiServerMCPClient(
        {
            "sezzle": StreamableHttpConnection(
                transport="streamable_http",
                url=settings.mcp_base_url,
                headers={"Authorization": f"Bearer {token}"},
            )
        }
    )
    tools = await mcp_client.get_tools()

    llm = ChatOllama(
        model=settings.ollama_chat_model,
        base_url=settings.ollama_base_url,
        temperature=settings.ollama_temperature,
        seed=settings.ollama_seed,
    )
    # finalize_answer is bound so the model CAN call it, but deliberately excluded
    # from tools_node (below) -- route_after_agent intercepts calls to it and sends
    # them to finalize_node instead of executing it as a real MCP tool call.
    llm_with_tools = llm.bind_tools([*tools, finalize_answer])
    tools_node = ToolNode(tools)

    graph = _build_graph(llm, llm_with_tools, tools_node)

    initial_messages: list[AnyMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
    for shot in FEW_SHOTS:
        cls = HumanMessage if shot["role"] == "user" else AIMessage
        initial_messages.append(cls(content=shot["content"]))
    initial_messages.append(HumanMessage(content=question))

    final_state = await graph.ainvoke(
        {
            "messages": initial_messages,
            "call_trace": [],
            "tool_calls_detail": [],
            "question": question,
            "rounds": 0,
            "corrective_rounds": 0,
            "route": "",
            "answer": "",
            "declared_route": "",
        },
        config={"recursion_limit": 50},
    )

    return {
        "route": final_state["route"],
        "answer": final_state["answer"],
        "call_trace": final_state["call_trace"],
        "tool_calls_detail": final_state["tool_calls_detail"],
        "declared_route": final_state["declared_route"] or None,
    }
