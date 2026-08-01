from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_current_user_id, get_escalation_service
from api.models.escalation import EscalationRequest, EscalationResponse
from api.services.escalation_service import EscalationService

router = APIRouter(prefix="/escalate", tags=["escalation"])


@router.post("", response_model=EscalationResponse)
def escalate(
    body: EscalationRequest,
    user_id: str = Depends(get_current_user_id),
    service: EscalationService = Depends(get_escalation_service),
) -> EscalationResponse:
    return service.create(user_id, body.reason)
