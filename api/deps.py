"""FastAPI dependency injection: verified identity + shared service singletons.

`get_current_user_id` is the only source of truth for "who is asking" anywhere in
this API -- no controller ever reads a user_id from a path/query/body param. That's
what makes cross-account access unrepresentable rather than merely rejected: the
capability to specify "whose data" doesn't exist outside the verified token.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from api.auth.security import verify_token
from api.services.escalation_service import EscalationService
from api.services.order_service import OrderService
from api.services.policy_service import PolicyService
from orders_store import OrdersStore


def get_current_user_id(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="expected 'Authorization: Bearer <token>'",
        )
    token = authorization.removeprefix("Bearer ").strip()
    return verify_token(token)


# Singletons created once at process start (app.state, wired in main.py) --
# re-loading DATA-orders.json or re-embedding the policy corpus per request would
# blow the p95 latency budget for no benefit, since neither changes per-request.
_order_service: OrderService | None = None
_policy_service: PolicyService | None = None
_escalation_service: EscalationService | None = None


def configure_services(
    order_service: OrderService, policy_service: PolicyService, escalation_service: EscalationService
) -> None:
    global _order_service, _policy_service, _escalation_service
    _order_service = order_service
    _policy_service = policy_service
    _escalation_service = escalation_service


def get_order_service() -> OrderService:
    assert _order_service is not None, "call configure_services() at app startup"
    return _order_service


def get_policy_service() -> PolicyService:
    assert _policy_service is not None, "call configure_services() at app startup"
    return _policy_service


def get_escalation_service() -> EscalationService:
    assert _escalation_service is not None, "call configure_services() at app startup"
    return _escalation_service
