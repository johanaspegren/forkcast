"""Characterisation tests for house-rule evaluation.

These lock in the behaviour `GameEngine._refresh_rules` had before the rule
logic was extracted into `game/rules.py`, so that Classic Draft and Realtime
Rush cannot drift when the swipe solver starts sharing the same code.

The subtle one is `one_fish`: it reports satisfied while the week is still
incomplete, because a half-drafted week has not broken the rule yet.
"""

import pytest

from backend.forkcast.game import rules
from backend.forkcast.game.engine import DAYS, MEALS, engine
from backend.forkcast.game.models import WeekEntry

# id -> (locked meal ids, overrides, {rule_id: (satisfied, detail)})
GOLDEN = {
    "empty": ([], [], {
        "one_fish": (True, "0 fish meals locked"),
        "max_one_minced": (True, "0 minced-meat meals locked"),
    }),
    "partial_one_fish": (["salmon"], [], {
        "one_fish": (True, "1 fish meals locked"),
        "max_one_minced": (True, "0 minced-meat meals locked"),
    }),
    "partial_two_minced": (["tacos", "burgers"], [], {
        "one_fish": (True, "0 fish meals locked"),
        "max_one_minced": (False, "2 minced-meat meals locked"),
    }),
    "full_no_fish": (["pasta", "pizza", "yakiniku", "chicken_curry", "tomato_soup"], [], {
        "one_fish": (False, "0 fish meals locked"),
        "max_one_minced": (True, "0 minced-meat meals locked"),
    }),
    "full_fish_and_minced": (["salmon", "tacos", "pasta", "pizza", "yakiniku"], [], {
        "one_fish": (True, "1 fish meals locked"),
        "max_one_minced": (True, "1 minced-meat meals locked"),
    }),
    "full_two_minced": (["tacos", "burgers", "pasta", "pizza", "salmon"], [], {
        "one_fish": (True, "1 fish meals locked"),
        "max_one_minced": (False, "2 minced-meat meals locked"),
    }),
    "full_no_fish_override": (
        ["pasta", "pizza", "yakiniku", "chicken_curry", "tomato_soup"], ["one_fish"], {
            "one_fish": (True, "0 fish meals locked — overruled by General Assembly"),
            "max_one_minced": (True, "0 minced-meat meals locked"),
        }),
    "full_two_minced_override": (
        ["tacos", "burgers", "pasta", "pizza", "salmon"], ["max_one_minced"], {
            "one_fish": (True, "1 fish meals locked"),
            "max_one_minced": (True, "2 minced-meat meals locked — overruled by General Assembly"),
        }),
}


def _session_with(meal_ids, overrides):
    session = engine.create_session()
    session.rule_overrides = list(overrides)
    for day, meal_id in zip(DAYS, meal_ids):
        session.week[day] = WeekEntry(meal_id=meal_id)
    return session


@pytest.mark.parametrize("case", list(GOLDEN))
def test_engine_rules_match_golden(case):
    """The engine's rule output is unchanged by the extraction."""
    meal_ids, overrides, expected = GOLDEN[case]
    session = _session_with(meal_ids, overrides)
    engine._refresh_rules(session)

    assert [rule.id for rule in session.rules] == list(expected)
    for rule in session.rules:
        satisfied, detail = expected[rule.id]
        assert rule.satisfied is satisfied, f"{case}/{rule.id} satisfied"
        assert rule.detail == detail, f"{case}/{rule.id} detail"
        assert rule.level == "HOUSE"


@pytest.mark.parametrize("case", list(GOLDEN))
def test_pure_evaluate_matches_engine(case):
    """`rules.evaluate` reproduces the engine result from meals alone."""
    meal_ids, overrides, _ = GOLDEN[case]
    session = _session_with(meal_ids, overrides)
    engine._refresh_rules(session)

    evaluated = rules.evaluate(
        [MEALS[meal_id] for meal_id in meal_ids],
        overrides=overrides,
        week_complete=len(meal_ids) == len(DAYS),
    )
    assert [r.model_dump() for r in evaluated] == [r.model_dump() for r in session.rules]


def test_one_fish_is_pending_not_broken_while_week_incomplete():
    """The softening is a draft-in-progress nuance, not a property of the rule."""
    no_fish = [MEALS["pasta"]]
    assert rules.evaluate(no_fish, week_complete=False)[0].satisfied is True
    assert rules.evaluate(no_fish, week_complete=True)[0].satisfied is False


def test_violations_reports_broken_rule_ids():
    week = [MEALS[m] for m in ("tacos", "burgers", "pasta", "pizza", "yakiniku")]
    assert rules.violations(week) == {"one_fish", "max_one_minced"}
    assert rules.violations(week, overrides=["one_fish"]) == {"max_one_minced"}
    ok = [MEALS[m] for m in ("salmon", "tacos", "pasta", "pizza", "yakiniku")]
    assert rules.violations(ok) == set()


def test_unsatisfiable_distinguishes_pool_from_week():
    """A family owning no fish recipe is a different problem from a fishless week."""
    fishless = [MEALS[m] for m in ("pasta", "pizza", "tacos", "burgers", "yakiniku")]
    assert "one_fish" in rules.unsatisfiable(fishless, day_count=5)

    with_fish = fishless + [MEALS["salmon"]]
    assert "one_fish" not in rules.unsatisfiable(with_fish, day_count=5)

    # Only one minced meal is allowed, so a mostly-minced pool cannot fill a week:
    # two of these three meals are minced, so any 3-day pick already breaks the rule.
    mostly_minced = [MEALS[m] for m in ("tacos", "burgers", "salmon")]
    assert "max_one_minced" in rules.unsatisfiable(mostly_minced, day_count=5)
    assert "max_one_minced" in rules.unsatisfiable(mostly_minced, day_count=3)
    # Two days is fine: salmon plus a single minced meal.
    assert "max_one_minced" not in rules.unsatisfiable(mostly_minced, day_count=2)
