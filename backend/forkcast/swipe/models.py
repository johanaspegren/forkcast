from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Verdict(StrEnum):
    DISLIKE = "dislike"
    LIKE = "like"
    SUPERLIKE = "superlike"


class MemberVerdict(BaseModel):
    verdict: Verdict
    updated_at: str


class Member(BaseModel):
    """One family member's durable preferences.

    Verdicts persist across weeks, so a later round only needs to ask about
    meals this member has not seen yet.
    """

    member_id: str
    name: str
    avatar: str = "🍽️"
    verdicts: dict[str, MemberVerdict] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None

    def verdict_for(self, meal_id: str) -> Verdict | None:
        entry = self.verdicts.get(meal_id)
        return entry.verdict if entry else None


class DayPick(BaseModel):
    day: str
    meal_id: str
    meal_name: str
    meal_emoji: str
    chef: list[str] = Field(default_factory=list)
    cleanup: list[str] = Field(default_factory=list)
    reason: str | None = None


class WeekCandidate(BaseModel):
    """A complete, rule-checked week the family could be offered."""

    picks: list[DayPick]
    satisfaction: dict[str, float] = Field(default_factory=dict)
    members_without_a_win: list[str] = Field(default_factory=list)
    rule_exceptions: list[str] = Field(default_factory=list)
    mean_satisfaction: float = 0.0

    @property
    def meal_ids(self) -> list[str]:
        return [pick.meal_id for pick in self.picks]


class RoundStatus(StrEnum):
    COLLECTING = "collecting"
    PROPOSED = "proposed"
    LOCKED = "locked"


class SwipeRound(BaseModel):
    week_id: str
    year: int
    week: int
    status: RoundStatus = RoundStatus.COLLECTING
    participants: list[str] = Field(default_factory=list)
    # Bumped on every verdict write; a proposal built from an older revision is stale.
    verdicts_revision: int = 0
    proposal: WeekCandidate | None = None
    # Near-ties kept so the AI layer can re-rank without re-solving.
    candidates: list[WeekCandidate] = Field(default_factory=list)
    proposal_revision: int | None = None
    proposal_ai_used: bool = False
    rerolls: int = 0
    # Meal sets already shown this round, so "gör om" does not hand back a week
    # the family just rejected.
    shown_sets: list[list[str]] = Field(default_factory=list)
    updated_at: str | None = None
