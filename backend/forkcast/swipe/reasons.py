from __future__ import annotations

"""Why each dish is on the menu, written without an LLM.

The AI layer replaces these with better sentences when it is configured, but
the feature has to read well with the key unset (§4.5), so this is the baseline
rather than a placeholder.
"""

from .models import Member, Verdict, WeekCandidate


def _names(members: list[Member], meal_id: str, verdict: Verdict) -> list[str]:
    return [member.name for member in members if member.verdict_for(meal_id) is verdict]


def _join(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} och {names[-1]}"


def describe(meal_id: str, members: list[Member]) -> str:
    fans = _names(members, meal_id, Verdict.SUPERLIKE)
    likers = _names(members, meal_id, Verdict.LIKE)

    if fans:
        return f"{_join(fans)} önskade den här."
    if len(likers) == 2:
        return f"{_join(likers)} gillade båda den här."
    if len(likers) > 2:
        return f"{_join(likers)} gillade den här."
    if likers:
        return f"{likers[0]} gillade den här."
    return "Ingen hade något emot den här."


def fill(candidate: WeekCandidate, members: list[Member]) -> WeekCandidate:
    for pick in candidate.picks:
        pick.reason = describe(pick.meal_id, members)
    return candidate
