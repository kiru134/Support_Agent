from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_current_user_id, get_policy_service
from api.models.policy import PolicySearchResponse
from api.services.policy_service import PolicyService

router = APIRouter(prefix="/policy", tags=["policy"])


@router.get("/search", response_model=PolicySearchResponse)
def search_policy(
    q: str,
    k: int = 4,
    # Authenticated but not used for scoping -- policy docs aren't per-account data.
    # Still requires a valid token: no anonymous access to any endpoint.
    _user_id: str = Depends(get_current_user_id),
    service: PolicyService = Depends(get_policy_service),
) -> PolicySearchResponse:
    return PolicySearchResponse(results=service.search(q, k))
