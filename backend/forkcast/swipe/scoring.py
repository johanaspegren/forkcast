from __future__ import annotations

"""How happy each member would be with a candidate week.

The obvious objective — add up likes, subtract dislikes, then favour the
worst-off member — hands the week to whoever is hardest to please: someone who
dislikes most of the deck is the minimum in *every* candidate, so the whole
objective collapses onto them. That is the free veto the spec rejects (§19),
re-entering at week granularity, and it cannot tell "unhappy" from "barely
swiped".

Instead each member is measured against what a *random* week would give **them**.
A member who dislikes 90% of the deck expects a lot of pain from any week, so
avoiding their dislikes earns little; the only way to score for them is to
include one of their few likes. Blocking becomes expensive and helping cheap
(§4.2) as a property of the arithmetic rather than a rule bolted on top - which
is what lets left-swipes stay free and unlimited in the UI.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .models import Member, Verdict

EPSILON = 1e-6


@dataclass(frozen=True)
class Weights:
    """Every tunable in one place - expect to revisit these after a playtest."""

    like: float = 1.0
    superlike: float = 2.0
    dislike: float = 1.0
    # Keeps a bland week of five unknowns from beating a known-good one.
    unswiped_discount: float = 0.08
    # A seven-year-old's dislike from last autumn should not own this week.
    half_life_days: float = 182.0


@dataclass
class MemberProfile:
    """Per-meal weights for one member, precomputed once per solve."""

    member_id: str
    wins: dict[str, float] = field(default_factory=dict)
    pains: dict[str, float] = field(default_factory=dict)
    swiped: float = 0.0
    total_win: float = 0.0
    total_pain: float = 0.0

    @property
    def has_swiped(self) -> bool:
        return self.swiped > 0


def _age_weight(updated_at: str | None, now: datetime, half_life_days: float) -> float:
    if not updated_at or half_life_days <= 0:
        return 1.0
    try:
        stamp = datetime.fromisoformat(updated_at)
    except ValueError:
        return 1.0
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - stamp).total_seconds() / 86400.0)
    return 0.5 ** (age_days / half_life_days)


def build_profile(member: Member, now: datetime | None = None, weights: Weights = Weights()) -> MemberProfile:
    now = now or datetime.now(timezone.utc)
    profile = MemberProfile(member_id=member.member_id)

    for meal_id, entry in member.verdicts.items():
        decay = _age_weight(entry.updated_at, now, weights.half_life_days)
        if decay <= 0:
            continue
        profile.swiped += decay
        if entry.verdict is Verdict.LIKE:
            profile.wins[meal_id] = weights.like * decay
            profile.total_win += weights.like * decay
        elif entry.verdict is Verdict.SUPERLIKE:
            profile.wins[meal_id] = weights.superlike * decay
            profile.total_win += weights.superlike * decay
        elif entry.verdict is Verdict.DISLIKE:
            profile.pains[meal_id] = weights.dislike * decay
            profile.total_pain += weights.dislike * decay
    return profile


def satisfaction(profile: MemberProfile, meal_ids: list[str], weights: Weights = Weights()) -> float:
    """How much better than a random week this week is, for this member.

    Roughly: 0 means "about what chance would have given me", positive means
    better. A member who has not swiped scores 0 for every week and so does not
    steer the result.
    """
    if not meal_ids or not profile.has_swiped:
        return 0.0

    size = len(meal_ids)
    expected_win = size * profile.total_win / profile.swiped
    expected_pain = size * profile.total_pain / profile.swiped

    wins = sum(profile.wins.get(meal_id, 0.0) for meal_id in meal_ids)
    pains = sum(profile.pains.get(meal_id, 0.0) for meal_id in meal_ids)
    unswiped = sum(
        1 for meal_id in meal_ids if meal_id not in profile.wins and meal_id not in profile.pains
    )

    score = wins / max(EPSILON, expected_win) - pains / max(EPSILON, expected_pain)
    return score - weights.unswiped_discount * unswiped


def wins_in(profile: MemberProfile, meal_ids: list[str]) -> int:
    """Meals this member actually liked. Drives "alla får minst en favorit"."""
    return sum(1 for meal_id in meal_ids if meal_id in profile.wins)


def rank_key(profiles: list[MemberProfile], meal_ids: list[str], weights: Weights = Weights()):
    """Sort key for candidate weeks, best first under an ascending sort.

    Leximin first: compare the worst-off member, then the second-worst, and so
    on, rather than collapsing to a sum that lets one delighted member pay for
    another's miserable week.

    "Everyone gets at least one favourite" is only a tie-break. Making it the
    primary key sounds fairer but is not: it will drag a meal that three people
    dislike into the week purely so a fourth gets a win, which lowers the floor
    it was meant to raise. Leximin already reaches for the inclusive week
    whenever that genuinely helps the worst-off member.

    Mean breaks remaining ties, and the meal ids keep the order stable so the
    confirm screen does not reshuffle under the family's fingers.
    """
    scores = [satisfaction(profile, meal_ids, weights) for profile in profiles]
    without_a_win = sum(1 for profile in profiles if profile.has_swiped and not wins_in(profile, meal_ids))
    mean = sum(scores) / len(scores) if scores else 0.0
    # Negated so that ascending sort puts the best candidate first.
    return (tuple(-score for score in sorted(scores)), without_a_win, -mean, tuple(sorted(meal_ids)))
