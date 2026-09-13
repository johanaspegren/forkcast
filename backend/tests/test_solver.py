"""The solver must always produce a week, and it must not be captured by one member."""

import random
from datetime import datetime, timedelta, timezone

from backend.forkcast.game.engine import DAYS, MEALS
from backend.forkcast.swipe.models import Member
from backend.forkcast.swipe.solver import assign_days, prune_pool, solve
from backend.forkcast.swipe.scoring import build_profile, satisfaction

NOW = datetime(2026, 9, 13, tzinfo=timezone.utc)
RECENT = (NOW - timedelta(days=2)).isoformat()
DECK = list(MEALS.values())


def member(name: str, **verdicts) -> Member:
    return Member(
        member_id=name,
        name=name,
        verdicts={meal: {"verdict": v, "updated_at": RECENT} for meal, v in verdicts.items()},
    )


HOUSEHOLD = [
    member("johan", salmon="superlike", tacos="like", pizza="dislike"),
    member("elsa", tacos="superlike", pizza="like", salmon="dislike"),
    member("oscar", pasta="like", chicken_curry="superlike", burgers="dislike"),
]


def test_fills_every_day_and_keeps_the_house_rules():
    week = solve(DECK, HOUSEHOLD, DAYS, now=NOW)[0]
    assert [pick.day for pick in week.picks] == DAYS
    assert len(set(week.meal_ids)) == len(DAYS), "no repeated meals"
    assert week.rule_exceptions == []
    assert sum(1 for mid in week.meal_ids if MEALS[mid].fish) >= 1
    assert sum(1 for mid in week.meal_ids if MEALS[mid].minced_meat) <= 1


def test_everyone_gets_something_they_like_when_possible():
    week = solve(DECK, HOUSEHOLD, DAYS, now=NOW)[0]
    assert week.members_without_a_win == []


def test_a_grumpy_member_does_not_dictate_the_week():
    """The property the whole objective exists for.

    Three members who agree, plus one who dislikes everything they like and
    likes only one thing. A naive "maximise the worst-off member" objective
    would build the week around the grumpy one, because they are the minimum in
    every candidate. Here they should get their one meal - representation - and
    no more.
    """
    agreed = ["yakiniku", "teriyaki_bowl", "pasta", "pizza"]
    household = [
        member("a", yakiniku="superlike", teriyaki_bowl="like", pasta="like", pizza="like", veggie_chili="dislike"),
        member("b", yakiniku="like", teriyaki_bowl="superlike", pasta="like", pizza="like", veggie_chili="dislike"),
        member("c", yakiniku="like", teriyaki_bowl="like", pasta="superlike", pizza="like", veggie_chili="dislike"),
        member(
            "grumpy",
            yakiniku="dislike", teriyaki_bowl="dislike", pasta="dislike",
            pizza="dislike", veggie_chili="like",
        ),
    ]
    week = solve(DECK, household, DAYS, now=NOW)[0]

    liked_by_majority = [mid for mid in week.meal_ids if mid in agreed]
    assert len(liked_by_majority) >= 3, f"majority was crowded out: {week.meal_ids}"
    assert week.meal_ids.count("veggie_chili") <= 1, "the week was built around one member"

    # Leximin should still lift the worst-off member well above the week the
    # majority would have picked on their own.
    majority_only = ["yakiniku", "teriyaki_bowl", "pasta", "pizza", "salmon"]
    profiles = [build_profile(m, NOW) for m in household]
    worst_if_ignored = min(satisfaction(p, majority_only) for p in profiles)
    assert min(week.satisfaction.values()) > worst_if_ignored


def test_never_returns_an_empty_week_for_a_tiny_pool():
    """A family with three meals gets a three-day week, not an error."""
    tiny = [MEALS[m] for m in ("salmon", "pasta", "pizza")]
    weeks = solve(tiny, HOUSEHOLD, DAYS, now=NOW)
    assert weeks, "solver returned nothing"
    assert len(weeks[0].picks) == 3
    assert len(set(weeks[0].meal_ids)) == 3


def test_degrades_and_records_the_exception_when_a_rule_cannot_be_met():
    """No fish in the whole pool is a different problem from a fishless week."""
    fishless = [meal for meal in DECK if not meal.fish]
    week = solve(fishless, HOUSEHOLD, DAYS, now=NOW)[0]
    assert len(week.picks) == len(DAYS)
    assert "one_fish" in week.rule_exceptions


def test_is_deterministic_regardless_of_deck_order():
    """A refresh must not reshuffle the week under the family's fingers."""
    baseline = solve(DECK, HOUSEHOLD, DAYS, now=NOW)[0].meal_ids
    for seed in range(5):
        shuffled = DECK[:]
        random.Random(seed).shuffle(shuffled)
        assert solve(shuffled, HOUSEHOLD, DAYS, now=NOW)[0].meal_ids == baseline


def test_pinned_days_are_kept_and_not_reused():
    week = solve(DECK, HOUSEHOLD, DAYS, pinned={"friday": "pizza"}, now=NOW)[0]
    assert dict((p.day, p.meal_id) for p in week.picks)["friday"] == "pizza"
    assert week.meal_ids.count("pizza") == 1


def test_tolerates_a_pinned_meal_that_no_longer_exists():
    """Verdicts outlive recipes; a deleted meal id must not crash the solve."""
    week = solve(DECK, HOUSEHOLD, DAYS, pinned={"friday": "recipe-deleted-last-year"}, now=NOW)[0]
    assert len(week.picks) == len(DAYS)


def test_assign_days_puts_slower_cooking_later_in_the_week():
    minutes = {"a": 60, "b": 20, "c": 45}
    assignment = assign_days(["a", "b", "c"], ["monday", "tuesday", "wednesday"], minutes)
    ordered = [minutes[assignment[d]] for d in ("monday", "tuesday", "wednesday")]
    assert ordered == sorted(ordered)


def test_prune_pool_keeps_every_members_favourite_and_rule_headroom():
    profiles = [build_profile(m, NOW) for m in HOUSEHOLD]
    big_deck = DECK * 4  # force pruning
    pool = prune_pool(big_deck, profiles, day_count=len(DAYS), target=8)
    pool_ids = {meal.id for meal in pool}
    for profile in profiles:
        assert pool_ids & set(profile.wins), f"{profile.member_id} lost every favourite"
    assert any(MEALS[mid].fish for mid in pool_ids), "no fish left to satisfy one_fish"
