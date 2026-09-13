"""The objective: does a week work for everyone, not just on average."""

import pytest

from datetime import datetime, timedelta, timezone

from backend.forkcast.swipe.models import Member
from backend.forkcast.swipe.scoring import Weights, build_profile, satisfaction

NOW = datetime(2026, 9, 13, tzinfo=timezone.utc)
RECENT = (NOW - timedelta(days=3)).isoformat()


def member(name: str, **verdicts) -> Member:
    return Member(
        member_id=name,
        name=name,
        verdicts={meal: {"verdict": v, "updated_at": RECENT} for meal, v in verdicts.items()},
    )


def sat(m: Member, meal_ids, weights: Weights = Weights()) -> float:
    return satisfaction(build_profile(m, NOW, weights), meal_ids, weights)


def test_a_week_of_your_likes_beats_a_week_of_your_dislikes():
    elsa = member("elsa", tacos="superlike", pizza="like", salmon="dislike", pasta="dislike")
    assert sat(elsa, ["tacos", "pizza"]) > 0 > sat(elsa, ["salmon", "pasta"])


def test_a_member_who_never_swiped_does_not_steer():
    ghost = member("ghost")
    assert sat(ghost, ["tacos", "pizza"]) == 0.0
    assert sat(ghost, ["salmon", "pasta"]) == 0.0


def test_someone_who_dislikes_almost_everything_cannot_exceed_neutral():
    """The key anti-dictator property.

    A member with no likes has nothing to win, so no week can score above ~0 for
    them. They can still be hurt, so avoiding their dislikes matters - but they
    cannot outbid a member who actually likes things.
    """
    grumpy = member(
        "grumpy",
        tacos="dislike", pizza="dislike", pasta="dislike",
        salmon="dislike", burgers="dislike", yakiniku="dislike",
    )
    best_possible = sat(grumpy, ["chicken_curry", "tomato_soup"])  # none of their dislikes
    assert best_possible <= 0.0

    happy = member("happy", tacos="superlike", pizza="like")
    assert sat(happy, ["tacos", "pizza"]) > best_possible


def test_influence_does_not_depend_on_how_much_you_swiped():
    """Participation invariance.

    Satisfaction is driven by a member's like *rate*, not how many cards they
    got through, so someone who swiped four meals is not drowned out by someone
    who swiped eight. Both below like half of what they swiped, and both are
    handed a week made entirely of their own likes.
    """
    light = member("light", tacos="like", pizza="like", pasta="dislike", salmon="dislike")
    heavy = member(
        "heavy",
        tacos="like", pizza="like", burgers="like", yakiniku="like",
        pasta="dislike", salmon="dislike", chicken_curry="dislike", tomato_soup="dislike",
    )
    assert sat(light, ["tacos", "pizza"]) == pytest.approx(sat(heavy, ["tacos", "pizza"]))


def test_hitting_more_of_your_likes_scores_higher():
    """Sanity check on the above: volume of hits still matters within a member."""
    m = member("m", tacos="like", pizza="like", pasta="dislike", salmon="dislike")
    assert sat(m, ["tacos", "pizza"]) > sat(m, ["tacos", "chicken_curry"])


def test_old_verdicts_count_for_less_than_recent_ones():
    stale = Member(
        member_id="stale", name="stale",
        verdicts={
            "tacos": {"verdict": "like", "updated_at": (NOW - timedelta(days=730)).isoformat()},
            "pizza": {"verdict": "like", "updated_at": RECENT},
        },
    )
    profile = build_profile(stale, NOW)
    assert profile.wins["pizza"] > profile.wins["tacos"]


def test_an_unknown_week_loses_to_a_known_good_one():
    elsa = member("elsa", tacos="superlike", pizza="like")
    assert sat(elsa, ["tacos", "pizza"]) > sat(elsa, ["pasta", "yakiniku"])
