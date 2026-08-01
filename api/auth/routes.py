"""Mock login: no password because no credential store exists for these synthetic
shoppers. Simulates a shopper who already authenticated upstream (app/web session)
-- a real deployment receives a verified token from Sezzle's actual identity
provider here instead of minting one from a bare user_id."""
from __future__ import annotations

from fastapi import APIRouter

from api.auth.security import create_token
from api.models.auth import TokenRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
def issue_token(body: TokenRequest) -> TokenResponse:
    return TokenResponse(access_token=create_token(body.user_id))
