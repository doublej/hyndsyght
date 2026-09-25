"""Derives a short, bounded `intent` field from a closed turn/subagent's stashed message.

Formalizes Phase 5's captured `last_assistant_message` into a dedicated
field on that one event's payload. Zero propagation to any other event,
ever — the "semantic bleed" idea (labeling nearby events by proximity)
stays rejected; see the plan's Phase 8 note.
"""

import re
from typing import Any

INTENT_MAX_CHARS = 200

_SENTENCE_END = re.compile(r"[.!?](?:\s|$)")


def extract_intent(payload: dict[str, Any]) -> str | None:
    message = (payload.get("last_assistant_message") or "").strip()
    if not message:
        return None
    match = _SENTENCE_END.search(message)
    sentence = message[: match.end()] if match else message
    return sentence.strip()[:INTENT_MAX_CHARS]
