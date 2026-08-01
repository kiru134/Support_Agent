"""Deterministic checks that sit *around* the model, never *instead of* it.

Two jobs, both post-hoc (they observe what the model did/said, they never decide
the answer themselves):

1. Escalation safety net -- if the user's question strongly matches one of the four
   policy-defined forced-escalation categories but the model didn't call `escalate`,
   flag it so the agent loop can force one corrective regeneration. This is a net
   under the model's own judgment (driven by the system prompt + the `escalate`
   tool), not a pre-classifier that answers instead of it.
2. Output validation -- block two structurally-should-never-happen patterns:
   first-person claims of a completed action with no corresponding mutating tool
   ("I've paused/waived/rescheduled ..."), and a fabricated exact spending limit.
"""
from __future__ import annotations

import re

# Category name -> regex matched against the raw user question. Deliberately narrow
# and literal (mirrors the four categories the policy docs themselves call out as
# human-only) rather than a broad sentiment classifier -- a broad net would start
# doing the model's judgment work for it.
ESCALATION_SIGNALS: dict[str, re.Pattern] = {
    "hardship": re.compile(
        r"\b(lost my job|laid off|can'?t afford|can'?t pay|financial hardship|"
        r"medical emergency|natural disaster)\b",
        re.I,
    ),
    "fraud": re.compile(
        r"\b(never placed|didn'?t place|don'?t recognize|stolen (card|account)|"
        r"hacked|unauthorized|account takeover|someone (used|accessed) my)\b",
        re.I,
    ),
    "exact_decline_or_limit": re.compile(
        r"\b(why was .*(declined|denied)|exact (spending )?limit|"
        r"what('?s| is) my (exact )?limit)\b",
        re.I,
    ),
    "dispute_filing": re.compile(
        r"\b(never shipped|item not received|not as described|wrong item|"
        r"file a dispute|open a dispute)\b",
        re.I,
    ),
}


def detect_escalation_signal(question: str) -> str | None:
    for category, pattern in ESCALATION_SIGNALS.items():
        if pattern.search(question):
            return category
    return None


# Verbs with no corresponding mutating tool -- if the model claims to have *done*
# one of these, that claim is false by construction (no tool exists that could have
# made it true), regardless of how confident the phrasing sounds.
_ACTION_CLAIM_PATTERN = re.compile(
    r"\bI(?:'ve|'ll| will| am going to| have)\s+((?:go(?:ne)? ahead and)\s+)?"
    r"(paused|waived|reschedul\w*|refunded|filed|cancel(l)?ed|reversed|credited)\b",
    re.I,
)

_FABRICATED_LIMIT_PATTERN = re.compile(
    r"(\$\s?\d[\d,]*(\.\d+)?\s*(is|as)?\s*your\s*(exact\s*)?limit|"
    r"your\s*(exact\s*)?limit\s*(is|of)\s*\$?\s?\d)",
    re.I,
)


def validate_output(answer: str) -> list[str]:
    """Returns a list of violation codes (empty if the answer is clean)."""
    violations = []
    if _ACTION_CLAIM_PATTERN.search(answer):
        violations.append("claimed_unsupported_action")
    if _FABRICATED_LIMIT_PATTERN.search(answer):
        violations.append("fabricated_exact_limit")
    return violations


ESCALATION_FALLBACK_TEMPLATE = (
    "I want to make sure this is handled correctly, so I'm connecting you with a "
    "human agent on our support team who can help directly. {extra}"
    "In the meantime, please don't share sensitive account details here beyond "
    "what you already have."
)
