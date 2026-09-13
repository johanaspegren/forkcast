from __future__ import annotations

"""Choose the week. Deterministic, and never returns nothing.

The spec is explicit that Forkcast must work with the LLM switched off (§4.5),
so this module decides the menu on its own. The AI layer only ever re-ranks
weeks that came out of here, which is why it cannot break a house rule.
"""

import itertools
from datetime import datetime

from ..game import rules
from ..game.models import Meal
from .models import DayPick, Member, WeekCandidate
from .scoring import MemberProfile, Weights, build_profile, rank_key, satisfaction, wins_in

DEFAULT_MINUTES = 30
POOL_TARGET = 22


def prune_pool(
    meals: list[Meal],
    profiles: list[MemberProfile],
    day_count: int,
    target: int = POOL_TARGET,
) -> list[Meal]:
    """Shrink the deck before enumerating combinations.

    Enumerating 30 meals choose 5 is 142,506 candidates, which is seconds of
    CPU on a Raspberry Pi. Narrowing to ~22 first cuts that by an order of
    magnitude. This is the one place exactness is traded for speed, so it keeps
    every member's favourites and enough fish/non-minced meals for the house
    rules to remain satisfiable.
    """
    if len(meals) <= target:
        return list(meals)

    def aggregate(meal: Meal) -> float:
        return sum(p.wins.get(meal.id, 0.0) - p.pains.get(meal.id, 0.0) for p in profiles)

    by_aggregate = sorted(meals, key=lambda meal: (-aggregate(meal), meal.id))
    chosen: dict[str, Meal] = {meal.id: meal for meal in by_aggregate[: max(1, target // 2)]}

    # Everyone's own favourites, so no member is pruned out of the week.
    per_member = max(2, target // (2 * max(1, len(profiles))))
    for profile in profiles:
        liked = sorted(
            (meal for meal in meals if meal.id in profile.wins),
            key=lambda meal: (-profile.wins[meal.id], meal.id),
        )
        for meal in liked[:per_member]:
            chosen.setdefault(meal.id, meal)

    # Headroom for the house rules.
    for predicate in (lambda m: m.fish, lambda m: not m.minced_meat):
        for meal in [meal for meal in by_aggregate if predicate(meal)][:day_count]:
            chosen.setdefault(meal.id, meal)

    return list(chosen.values())


def assign_days(meal_ids: list[str], days: list[str], meal_minutes: dict[str, int]) -> dict[str, str]:
    """Put the slower cooking later in the week.

    Brute force over permutations (120 for five days) rather than a sort, so
    that per-day constraints can be added later without changing the shape.
    """
    if not meal_ids:
        return {}
    last = len(days) - 1
    best_order = min(
        itertools.permutations(meal_ids),
        key=lambda order: (
            sum(meal_minutes.get(meal_id, DEFAULT_MINUTES) * (last - i) for i, meal_id in enumerate(order)),
            order,
        ),
    )
    return dict(zip(days, best_order))


def solve(
    deck: list[Meal],
    members: list[Member],
    days: list[str],
    pinned: dict[str, str] | None = None,
    meal_minutes: dict[str, int] | None = None,
    weights: Weights = Weights(),
    now: datetime | None = None,
    limit: int = 8,
    epsilon: float | None = None,
) -> list[WeekCandidate]:
    """Best candidate weeks, best first. Never empty when the deck is not.

    With `epsilon`, the result is trimmed to weeks that are near-ties with the
    best one - equally good by the family's own criterion. That is the set the
    AI layer is allowed to choose from, so its judgement is confined to things
    the solver deliberately does not model (variety, day-feel, what the school
    is serving) and it can never trade away satisfaction.
    """
    meal_minutes = meal_minutes or {}
    meal_by_id = {meal.id: meal for meal in deck}
    # Tolerate ids from deleted recipes still sitting in stored verdicts.
    pinned = {
        day: meal_id
        for day, meal_id in (pinned or {}).items()
        if day in days and meal_id in meal_by_id
    }

    profiles = [build_profile(member, now, weights) for member in members]
    free_days = [day for day in days if day not in pinned]
    pinned_meals = [meal_by_id[meal_id] for meal_id in pinned.values()]
    available = [meal for meal in deck if meal.id not in set(pinned.values())]

    # Too few meals to fill the week: cover the days we can rather than fail.
    need = min(len(free_days), len(available))
    free_days = free_days[:need]
    if need == 0 and not pinned:
        return []

    pool = prune_pool(available, profiles, len(days), POOL_TARGET) if need else []

    scored = []
    for combo in itertools.combinations(pool, need):
        meals = list(combo) + pinned_meals
        meal_ids = [meal.id for meal in meals]
        violated = rules.violations(meals)
        scored.append((len(violated), rank_key(profiles, meal_ids, weights), combo, sorted(violated)))

    if not scored:
        return []

    scored.sort(key=lambda entry: (entry[0], entry[1]))
    # Tier: prefer weeks breaking no house rule; degrade only if none exists.
    fewest_violations = scored[0][0]
    winners = [entry for entry in scored if entry[0] == fewest_violations][:limit]

    candidates = []
    for _, _, combo, violated in winners:
        assignment = assign_days([meal.id for meal in combo], free_days, meal_minutes)
        assignment.update(pinned)
        ordered_days = [day for day in days if day in assignment]
        meal_ids = [assignment[day] for day in ordered_days]

        scores = {p.member_id: round(satisfaction(p, meal_ids, weights), 4) for p in profiles}
        candidates.append(
            WeekCandidate(
                picks=[
                    DayPick(
                        day=day,
                        meal_id=assignment[day],
                        meal_name=meal_by_id[assignment[day]].name,
                        meal_emoji=meal_by_id[assignment[day]].emoji,
                    )
                    for day in ordered_days
                ],
                satisfaction=scores,
                members_without_a_win=[
                    p.member_id for p in profiles if p.has_swiped and not wins_in(p, meal_ids)
                ],
                rule_exceptions=violated,
                mean_satisfaction=round(sum(scores.values()) / len(scores), 4) if scores else 0.0,
            )
        )

    if epsilon is not None and candidates:
        best = candidates[0]
        best_min = min(best.satisfaction.values()) if best.satisfaction else 0.0
        candidates = [
            candidate
            for candidate in candidates
            if candidate.mean_satisfaction >= best.mean_satisfaction - epsilon
            and (min(candidate.satisfaction.values()) if candidate.satisfaction else 0.0)
            >= best_min - epsilon
        ]
    return candidates


def assign_chefs(candidate: WeekCandidate, members: list[Member]) -> WeekCandidate:
    """Whoever super-liked a dish offers to cook it.

    A super-like is the one swipe that carries a commitment, so it doubles as
    the chore signal and no second voting mechanic is needed. When several
    people super-liked the same dish, the one cooking least that week takes it,
    which keeps the load even without anyone tracking it.
    """
    from .models import Verdict

    load: dict[str, int] = {member.member_id: 0 for member in members}
    by_id = {member.member_id: member for member in members}

    for pick in candidate.picks:
        volunteers = [
            member.member_id
            for member in members
            if member.verdict_for(pick.meal_id) is Verdict.SUPERLIKE
        ]
        if not volunteers:
            continue
        chosen = min(volunteers, key=lambda member_id: (load[member_id], by_id[member_id].name))
        load[chosen] += 1
        pick.chef = [chosen]
    return candidate
