"""The AI layer must never be able to damage a week.

Every test here uses a fake client: no network, no key, no cost.
"""

import pytest

from backend.forkcast.ai.forkcast_ai import DayReason, ForkcastAI, WeekRanking, apply_ranking
from backend.forkcast.swipe.models import DayPick, Member, WeekCandidate


def candidate(*meals: str) -> WeekCandidate:
    return WeekCandidate(
        picks=[
            DayPick(day=day, meal_id=meal, meal_name=meal.title(), meal_emoji="🍽️")
            for day, meal in zip(["monday", "tuesday", "wednesday", "thursday", "friday"], meals)
        ]
    )


CANDIDATES = [candidate("a", "b", "c", "d", "e"), candidate("a", "b", "c", "d", "f")]
MEMBERS = [Member(member_id="m1", name="Elsa")]


class FakeResponse:
    def __init__(self, parsed, stop_reason="end_turn"):
        self.parsed_output = parsed
        self.stop_reason = stop_reason


class FakeClient:
    def __init__(self, result):
        self._result = result
        self.messages = self

    def parse(self, **_kwargs):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def ai_with(result) -> ForkcastAI:
    return ForkcastAI(client=FakeClient(result))


def test_without_a_key_there_is_no_ai_and_no_error():
    forkcast_ai = ForkcastAI(client=None)
    assert forkcast_ai.available is False
    assert forkcast_ai.rank_week_candidates(CANDIDATES, MEMBERS) is None


def test_a_valid_choice_is_returned():
    ranking = WeekRanking(choice_index=1, reasons=[DayReason(day="monday", reason="Elsa ville ha den.")])
    assert ai_with(FakeResponse(ranking)).rank_week_candidates(CANDIDATES, MEMBERS).choice_index == 1


@pytest.mark.parametrize("bad_index", [-1, 2, 99])
def test_an_out_of_range_index_falls_back_to_the_best_week(bad_index):
    """The model returns an index, never meal ids, so this is the worst it can do."""
    ranking = WeekRanking(choice_index=bad_index)
    result = ai_with(FakeResponse(ranking)).rank_week_candidates(CANDIDATES, MEMBERS)
    assert result.choice_index == 0


def test_a_refusal_is_treated_as_no_suggestion():
    ranking = WeekRanking(choice_index=1)
    assert ai_with(FakeResponse(ranking, stop_reason="refusal")).rank_week_candidates(CANDIDATES, MEMBERS) is None


def test_an_unparseable_response_is_treated_as_no_suggestion():
    assert ai_with(FakeResponse(None)).rank_week_candidates(CANDIDATES, MEMBERS) is None


@pytest.mark.parametrize(
    "error",
    [
        ConnectionError("the Pi is offline"),
        TimeoutError("the model took too long"),
        RuntimeError("rate limited"),
        ValueError("schema mismatch"),
    ],
)
def test_every_failure_mode_keeps_the_deterministic_week(error):
    """Deliberately not importing the Anthropic SDK: the suite must run without
    it, and the adapter catches broadly precisely so a new SDK exception class
    cannot take the week down."""
    assert ai_with(error).rank_week_candidates(CANDIDATES, MEMBERS) is None


def test_reasons_are_attached_only_to_days_the_model_named():
    week = candidate("a", "b", "c", "d", "e")
    week.picks[0].reason = "original"
    applied = apply_ranking(
        week,
        WeekRanking(
            choice_index=0,
            reasons=[DayReason(day="tuesday", reason="Passar mitt i veckan."), DayReason(day="friday", reason="   ")],
        ),
    )
    by_day = {pick.day: pick.reason for pick in applied.picks}
    assert by_day["tuesday"] == "Passar mitt i veckan."
    assert by_day["monday"] == "original", "days the model ignored keep what they had"
    assert by_day["friday"] is None, "a blank reason is not applied"
