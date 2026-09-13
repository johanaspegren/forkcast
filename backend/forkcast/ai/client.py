from __future__ import annotations

"""Thin wrapper over the Anthropic SDK.

Kept separate from the game and swipe packages so that nothing in the rules or
the solver imports an AI dependency (§28).
"""

import os

DEFAULT_MODEL = "claude-opus-5"


def resolve_model() -> str:
    return os.environ.get("FORKCAST_AI_MODEL", DEFAULT_MODEL)


def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def make_client():
    """The configured client, or None when the family has not set a key.

    Unlike photo import, every AI call in the swipe flow has a deterministic
    fallback, so a missing key is never an error.
    """
    if not available():
        return None
    try:
        import anthropic
    except ImportError:
        return None
    return anthropic.Anthropic()
