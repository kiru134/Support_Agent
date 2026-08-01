from __future__ import annotations

from pydantic import BaseModel


class PolicyChunk(BaseModel):
    doc: str
    heading: str
    text: str
    score: float


class PolicySearchResponse(BaseModel):
    results: list[PolicyChunk]
