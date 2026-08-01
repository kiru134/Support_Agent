from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user_id, get_order_service
from api.models.orders import OrderDetailResponse, OrdersListResponse
from api.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=OrdersListResponse)
def list_orders(
    user_id: str = Depends(get_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> OrdersListResponse:
    return OrdersListResponse(orders=service.list_orders(user_id))


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_order(
    order_id: str,
    user_id: str = Depends(get_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> OrderDetailResponse:
    order, candidates = service.get_order_or_candidates(user_id, order_id)
    if order is not None:
        return OrderDetailResponse(order=order)
    if candidates:
        # Multiple of the CALLER'S OWN orders match -- safe to disclose (never
        # crosses accounts), and distinct from not_found so the agent can ask a
        # clarifying question instead of guessing or giving up.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "ambiguous",
                "candidates": [
                    {"order_id": c.order_id, "merchant": c.merchant, "status": c.status, "total": c.total}
                    for c in candidates
                ],
            },
        )
    # Identical response whether order_id doesn't exist or belongs to someone
    # else -- no oracle that would let account enumeration distinguish the two.
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
