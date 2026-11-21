"""Chat orchestrator. LLM path (llm.py) when a key is present, deterministic fallback otherwise.

agent_review() lives in modules/proposals.py and is re-exported here.
"""
from __future__ import annotations

import logging
import os
import re

import fallback
from modules import proposals
from modules.proposals import agent_review  # noqa: F401  (re-export)
from state import State
from texts import tr

log = logging.getLogger("agent")

CONFIRM_RE = re.compile(r"^\s*(да|подтверждаю|ок|окей|давай|создай|yes|ha|xa|tasdiqlayman|mayli)\s*[.!]?\s*$",
                        re.IGNORECASE)


def _pending_chat(s: State):
    return [p for p in s.proposals.values() if p.origin == "chat" and p.status == "pending"]


def chat(s: State, message: str, history: list[dict], lang: str = "ru") -> dict:
    # 1. typed confirmation is handled by CODE, never by the LLM
    if CONFIRM_RE.match(message):
        pend = _pending_chat(s)
        if len(pend) == 1:
            res = proposals.apply(s, pend[0].id)
            return {"reply": res["message"], "proposals": [], "source": "code"}
        if not pend:
            return {"reply": tr("a_nothing"), "proposals": [], "source": "code"}
        return {"reply": tr("a_several"),
                "proposals": [proposals.view(p) for p in pend], "source": "code"}

    # 2. LLM, if configured
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        before = set(s.proposals)
        try:
            import llm
            out = llm.chat(s, message, history, lang)
            if out is not None:
                return {**out, "source": "llm"}
        except Exception as e:  # never break the demo; never leak details
            log.warning("LLM failed, using fallback: %s", type(e).__name__)
        # LLM gave up midway: withdraw any proposal it created so the fallback doesn't duplicate it
        for pid in set(s.proposals) - before:
            if s.proposals[pid].status == "pending":
                s.proposals[pid].status = "resolved"

    # 3. deterministic fallback
    out = fallback.reply(s, message)
    return {**out, "source": "fallback"}
