"""Pydantic models for the order domain, in two layers:

- Raw models (`User`, `OrderRaw`) mirror DATA-orders.json's on-disk shape exactly --
  parsing into these at load time in orders_store.py catches schema drift at the
  data boundary instead of failing later with a bare KeyError.
- Enriched/DTO models (`OrderSummary`, `OrderDetail`) add the derived fields
  (unpaid balance, next upcoming installment, refund shortfall, etc.) computed in
  orders_store.py. OrderService returns these directly; FastAPI's `response_model`
  serializes them at the API boundary with no separate dict-based DTO step.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Installment(BaseModel):
    installment: int
    amount: float
    due_date: str
    status: str
    paid_date: Optional[str] = None


class Refund(BaseModel):
    amount: float
    issued_date: str
    status: str


class User(BaseModel):
    user_id: str
    name: str
    account_status: str
    # Present in the source data but unused: the real per-order reschedule counter
    # is OrderRaw.reschedules_used, not this. Kept (typed loosely) so parsing
    # doesn't silently drop a field we haven't verified is truly always empty.
    reschedules_used: dict = {}


class OrderRaw(BaseModel):
    order_id: str
    user_id: str
    merchant: str
    order_date: str
    total: float
    plan: str
    status: str
    reschedules_used: int
    refund: Optional[Refund] = None
    installments: list[Installment]


class OrderSummary(BaseModel):
    order_id: str
    merchant: str
    status: str
    total: float
    unpaid_balance: float
    next_upcoming_installment: Optional[Installment] = None
    has_failed_installment: bool
    failed_installment: Optional[Installment] = None
    reschedules_used: int
    reschedules_remaining: int
    next_reschedule_fee: float
    refund: Optional[Refund] = None
    refund_shortfall_to_original_payment: Optional[float] = None


class OrderDetail(OrderSummary):
    installments: list[Installment]


class OrdersListResponse(BaseModel):
    orders: list[OrderSummary]


class OrderDetailResponse(BaseModel):
    order: OrderDetail
