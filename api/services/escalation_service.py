"""Escalation is a logging/no-op action -- there is no real ticketing system behind
it (flagged explicitly as unfinished in README). This is deliberate: it's what
keeps "I've escalated this" honest, since the only thing that actually happens is a
log entry, never a promise of a specific outcome or timeline."""
from __future__ import annotations

import itertools
import logging
import time

logger = logging.getLogger("escalations")
_counter = itertools.count(1)


class EscalationService:
    def create(self, user_id: str, reason: str) -> dict:
        ticket_id = f"esc_{int(time.time())}_{next(_counter)}"
        logger.info("escalation ticket=%s user=%s reason=%r", ticket_id, user_id, reason)
        return {"status": "escalated", "reason": reason, "ticket_id": ticket_id}
