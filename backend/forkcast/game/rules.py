from __future__ import annotations

"""House-rule evaluation, kept free of game state.

The spec (§28) asks for rules to live apart from the engine so that other
callers can reuse them; the swipe solver needs to score a candidate week that
has never been part of a `Session`. Everything here operates on a plain list of
`Meal` objects.
"""

from collections.abc import Iterable
from enum import StrEnum

from .models import Meal, RuleStatus


class RuleLevel(StrEnum):
    """§21's three levels. Only HOUSE rules can be overridden by the family."""

    HARD = "HARD"
    HOUSE = "HOUSE"
    PREFERENCE = "PREFERENCE"


ONE_FISH = "one_fish"
MAX_ONE_MINCED = "max_one_minced"

OVERRULED_SUFFIX = " — overruled by General Assembly"


def fish_count(meals: Iterable[Meal]) -> int:
    return sum(1 for meal in meals if meal.fish)


def minced_count(meals: Iterable[Meal]) -> int:
    return sum(1 for meal in meals if meal.minced_meat)


def evaluate(
    meals: list[Meal],
    overrides: Iterable[str] = (),
    week_complete: bool = True,
) -> list[RuleStatus]:
    """Evaluate the house rules over the meals chosen so far.

    `week_complete` softens `one_fish` while a draft is still in progress: a
    half-filled week has not broken the rule yet, it just has not met it. The
    caller decides, because a solver evaluating a full candidate week and a game
    showing rule chips mid-draft want opposite answers.
    """
    overrides = set(overrides)
    fish = fish_count(meals)
    minced = minced_count(meals)

    rules = [
        RuleStatus(
            id=ONE_FISH,
            label="At least 1 fish meal per week",
            level=RuleLevel.HOUSE,
            satisfied=fish >= 1 or not week_complete,
            detail=f"{fish} fish meals locked",
        ),
        RuleStatus(
            id=MAX_ONE_MINCED,
            label="Maximum 1 minced-meat meal per week",
            level=RuleLevel.HOUSE,
            satisfied=minced <= 1,
            detail=f"{minced} minced-meat meals locked",
        ),
    ]

    for rule in rules:
        if not rule.satisfied and rule.id in overrides:
            rule.satisfied = True
            rule.detail = f"{rule.detail}{OVERRULED_SUFFIX}"
    return rules


def violations(meals: list[Meal], overrides: Iterable[str] = ()) -> set[str]:
    """Rule ids a complete candidate week breaks. Used by the swipe solver."""
    return {
        rule.id
        for rule in evaluate(meals, overrides=overrides, week_complete=True)
        if not rule.satisfied
    }


def unsatisfiable(pool: list[Meal], day_count: int) -> set[str]:
    """Rules that no selection from this pool could ever satisfy.

    "This family owns no fish recipe" is a different problem from "this week has
    no fish", and the solver has to tell the family which one it is.
    """
    impossible: set[str] = set()
    if not any(meal.fish for meal in pool):
        impossible.add(ONE_FISH)
    # One minced meal is allowed, so the rest of the week must come from elsewhere.
    if sum(1 for meal in pool if not meal.minced_meat) < day_count - 1:
        impossible.add(MAX_ONE_MINCED)
    return impossible
