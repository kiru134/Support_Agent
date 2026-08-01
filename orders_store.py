"""Loads DATA-orders.json once, validates it into Pydantic domain models (catching
schema drift at the boundary instead of a bare KeyError later), and computes
derived per-order fields.

Arithmetic and date logic live here, in plain Python, rather than being left to the
LLM -- this is deliberate: small local models are unreliable at multi-step arithmetic
and date math, and these numbers are exactly what the golden cases' `must_include`
regexes check byte-for-byte (amounts, dates, day counts).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

from api.models.orders import Installment, OrderDetail, OrderRaw, User

DATA_PATH = (
    Path(__file__).parent
    / "sezzleaiengineertakehomechallenge"
    / "DATA-orders.json"
)

RESCHEDULE_FEE = 5.0
MAX_RESCHEDULES = 3


class OrdersStore:
    def __init__(self, path: Path = DATA_PATH):
        raw = json.loads(path.read_text())
        self.today = date.fromisoformat(raw["today"])
        self.users: dict[str, User] = {
            u["user_id"]: User.model_validate(u) for u in raw["users"]
        }
        self._orders_by_id: dict[str, OrderDetail] = {}
        self._orders_by_user: dict[str, list[OrderDetail]] = {}
        self._order_owner: dict[str, str] = {}
        for raw_order in raw["orders"]:
            order = OrderRaw.model_validate(raw_order)
            enriched = self._enrich(order)
            self._orders_by_id[order.order_id] = enriched
            self._orders_by_user.setdefault(order.user_id, []).append(enriched)
            self._order_owner[order.order_id] = order.user_id

    def _enrich(self, order: OrderRaw) -> OrderDetail:
        unpaid = [i for i in order.installments if i.status != "paid"]
        unpaid_balance = round(sum(i.amount for i in unpaid), 2)

        next_upcoming: Optional[Installment] = next(
            (i for i in order.installments if i.status == "upcoming"), None
        )
        failed: Optional[Installment] = next(
            (i for i in order.installments if i.status == "failed"), None
        )

        reschedules_remaining = max(0, MAX_RESCHEDULES - order.reschedules_used)
        next_reschedule_fee = 0.0 if order.reschedules_used == 0 else RESCHEDULE_FEE

        refund_shortfall = None
        if order.refund is not None:
            refund_shortfall = round(max(0.0, order.refund.amount - unpaid_balance), 2)

        return OrderDetail(
            order_id=order.order_id,
            merchant=order.merchant,
            status=order.status,
            total=order.total,
            unpaid_balance=unpaid_balance,
            next_upcoming_installment=next_upcoming,
            has_failed_installment=failed is not None,
            failed_installment=failed,
            reschedules_used=order.reschedules_used,
            reschedules_remaining=reschedules_remaining,
            next_reschedule_fee=next_reschedule_fee,
            refund=order.refund,
            refund_shortfall_to_original_payment=refund_shortfall,
            installments=order.installments,
        )

    def orders_for_user(self, user_id: str) -> list[OrderDetail]:
        return list(self._orders_by_user.get(user_id, []))

    def owner_of(self, order_id: str) -> Optional[str]:
        """The real user_id that owns this order, or None if it doesn't exist.
        Ground truth for evaluation/categorize.py's Authorization Failure check --
        the running stack's own authorization boundary (see get_order) is what's
        actually enforced; this is a read-only lookup used only to score whether an
        answer mentioned an order id it had no business mentioning."""
        return self._order_owner.get(order_id)

    def get_order(self, user_id: str, order_id: str) -> Optional[OrderDetail]:
        """Returns None for both "doesn't exist" and "belongs to someone else" --
        same shape for both, so no response distinguishes account enumeration from
        a typo'd order id."""
        if self._order_owner.get(order_id) != user_id:
            return None
        return self._orders_by_id.get(order_id)

    def resolve_order(self, user_id: str, identifier: str) -> Optional[OrderDetail]:
        """Like get_order, but also accepts a merchant name in place of a real
        order id -- found during iteration (see ITERATION.md): the model would
        often pass a merchant name (or a merchant-name-shaped invented string) as
        order_id instead of first listing orders and matching itself, and
        sometimes wouldn't retry after the resulting not_found. Rather than
        depend on prompting/retry behavior alone, resolve that case here,
        server-side -- still scoped only to the caller's own orders, so this adds
        no authorization surface, it just makes the existing lookup robust to how
        the model actually calls it.

        Exact order_id match takes priority. If that fails, falls back to a
        case-insensitive substring match against merchant names among the user's
        own orders; ambiguous (multiple merchants match) or no match returns None,
        same as a genuine not_found.
        """
        exact = self.get_order(user_id, identifier)
        if exact is not None:
            return exact

        matches = self.find_by_merchant(user_id, identifier)
        return matches[0] if len(matches) == 1 else None

    def find_by_merchant(self, user_id: str, identifier: str) -> list[OrderDetail]:
        """All of the user's own orders whose merchant name contains `identifier`
        (case-insensitive). Used by resolve_order for the single-match case, and
        directly by the API layer to distinguish genuine not_found from ambiguous
        (multiple of the user's own orders match -- safe to disclose, since it
        never crosses into another account) so the agent can ask a clarifying
        question instead of silently guessing or giving up."""
        needle = identifier.strip().lower()
        if not needle:
            return []
        return [o for o in self.orders_for_user(user_id) if needle in o.merchant.lower()]

    def user_exists(self, user_id: str) -> bool:
        return user_id in self.users
