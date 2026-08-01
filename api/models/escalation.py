from __future__ import annotations

from pydantic import BaseModel


class EscalationRequest(BaseModel):
    reason: str = ""


class EscalationResponse(BaseModel):
    status: str
    reason: str
    ticket_id: str
