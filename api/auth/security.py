"""JWT issuance/verification. Mock login: no password, since no credential store
exists for synthetic shoppers -- see auth/routes.py. Production would receive an
already-verified identity token from Sezzle's real identity provider rather than
minting one here."""
from __future__ import annotations

import time

import jwt
from fastapi import HTTPException, status

from config.settings import settings


def create_token(user_id: str) -> str:
    now = int(time.time())
    payload = {"sub": user_id, "iat": now, "exp": now + settings.jwt_expiry_seconds}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> str:
    """Returns the verified user_id (the token's `sub` claim), or raises 401."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
        )
    return payload["sub"]
