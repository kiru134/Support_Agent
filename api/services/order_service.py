"""Business logic for order lookups. Thin wrapper over orders_store.py -- the
data-load and derived-field computation (unpaid balance, next upcoming installment,
refund shortfall, etc.) don't change just because there's now an HTTP layer above
them; this class only adds the shape conversion into API models.

`user_id` here always comes from a verified JWT claim (see api/deps.py), never from
a client-supplied field -- this service has no code path that accepts an
unauthenticated identity.
"""
from __future__ import annotations

from typing import Optional

from api.models.orders import OrderDetail
from orders_store import OrdersStore


class OrderService:
    def __init__(self, store: OrdersStore):
        self.store = store

    def list_orders(self, user_id: str) -> list[OrderDetail]:
        return self.store.orders_for_user(user_id)

    def get_order(self, user_id: str, order_id: str) -> Optional[OrderDetail]:
        """None for both "doesn't exist" and "belongs to someone else" -- same
        shape for both, so the API response gives no oracle distinguishing account
        enumeration from a typo'd order id. Also accepts a merchant name in place
        of a real order id (see orders_store.resolve_order) -- still scoped only
        to the caller's own orders."""
        return self.store.resolve_order(user_id, order_id)

    def get_order_or_candidates(
        self, user_id: str, order_id: str
    ) -> tuple[Optional[OrderDetail], list[OrderDetail]]:
        """Returns (order, []) on a clean single match, (None, []) on genuine
        not_found/cross-account, or (None, candidates) when the identifier matched
        more than one of the user's own orders -- ambiguous, not missing. All
        candidates are already scoped to this user, so surfacing them (instead of
        the generic not_found) leaks nothing across accounts; it's what lets the
        agent ask a clarifying question instead of guessing or giving up."""
        order = self.store.resolve_order(user_id, order_id)
        if order is not None:
            return order, []
        candidates = self.store.find_by_merchant(user_id, order_id)
        return None, (candidates if len(candidates) > 1 else [])
