from __future__ import annotations

"""What each member is asked to swipe, and in what order.

Weekly fatigue is what kills this feature, so a round is short and asks first
about the meals the solver knows nothing about.
"""

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from ..game.engine import MEALS
from ..game.models import Meal
from ..recipes import store as recipe_store
from ..recipes.models import Recipe
from ..recipes.meal_sync import MEAL_ID_PREFIX
from .models import Member, Verdict

DEFAULT_LIMIT = 14
STALE_AFTER_DAYS = 90


class DeckCard(BaseModel):
    meal_id: str
    name: str
    emoji: str
    thumb_url: str | None = None
    minutes: int | None = None
    servings: int | None = None
    protein: str | None = None
    is_fish: bool = False
    is_minced: bool = False
    previous_verdict: Verdict | None = None


def recipe_id_for(meal_id: str) -> str | None:
    return meal_id[len(MEAL_ID_PREFIX):] if meal_id.startswith(MEAL_ID_PREFIX) else None


def recipe_index() -> dict[str, Recipe]:
    """meal_id -> Recipe, for the meals that came from the recipe collection."""
    return {f"{MEAL_ID_PREFIX}{recipe.id}": recipe for recipe in recipe_store.list_recipes()}


def resolve_meals(meal_ids: list[str]) -> list[Meal]:
    """Look meals up tolerantly.

    Stored verdicts outlive recipes, so an id whose recipe was deleted months
    ago is dropped rather than raising.
    """
    return [MEALS[meal_id] for meal_id in meal_ids if meal_id in MEALS]


def meal_minutes(recipes: dict[str, Recipe] | None = None) -> dict[str, int]:
    recipes = recipe_index() if recipes is None else recipes
    return {
        meal_id: recipe.time_minutes.total
        for meal_id, recipe in recipes.items()
        if recipe.time_minutes.total
    }


def to_card(meal: Meal, recipes: dict[str, Recipe], member: Member | None = None) -> DeckCard:
    recipe = recipes.get(meal.id)
    return DeckCard(
        meal_id=meal.id,
        name=meal.name,
        emoji=meal.emoji,
        thumb_url=f"/api/recipes/{recipe.id}/thumb" if recipe and recipe.photo.thumb_file else None,
        minutes=recipe.time_minutes.total if recipe else None,
        servings=recipe.servings if recipe else None,
        protein=meal.protein_type,
        is_fish=meal.fish,
        is_minced=meal.minced_meat,
        previous_verdict=member.verdict_for(meal.id) if member else None,
    )


def build_deck(
    member: Member,
    meals: list[Meal] | None = None,
    limit: int = DEFAULT_LIMIT,
    now: datetime | None = None,
) -> list[DeckCard]:
    """Unswiped meals first, then verdicts old enough to be worth re-checking.

    Photo-backed cards are floated to the front of each group: the first few
    cards decide whether anyone finishes the deck.
    """
    now = now or datetime.now(timezone.utc)
    meals = list(MEALS.values()) if meals is None else meals
    recipes = recipe_index()
    stale_before = now - timedelta(days=STALE_AFTER_DAYS)

    unswiped: list[Meal] = []
    stale: list[Meal] = []
    for meal in meals:
        entry = member.verdicts.get(meal.id)
        if entry is None:
            unswiped.append(meal)
            continue
        try:
            updated = datetime.fromisoformat(entry.updated_at)
        except ValueError:
            continue
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        if updated < stale_before:
            stale.append(meal)

    def presentation_order(meal: Meal) -> tuple:
        # Cards with a real dish photo lead; the rest fall back to a designed
        # emoji card. Then a stable alphabetical order.
        recipe = recipes.get(meal.id)
        has_photo = bool(recipe and recipe.photo.thumb_file)
        return (0 if has_photo else 1, meal.name.lower(), meal.id)

    ordered = sorted(unswiped, key=presentation_order) + sorted(stale, key=presentation_order)
    return [to_card(meal, recipes, member) for meal in ordered[:limit]]


VERDICT_ORDER = {Verdict.SUPERLIKE: 0, Verdict.LIKE: 1, Verdict.DISLIKE: 2}


def build_summary(member: Member, meals: list[Meal] | None = None) -> list[DeckCard]:
    """Everything this member has voted on, best-loved first.

    Unlike the deck this includes meals already swiped - it is the recap, not
    the round. Ids whose recipe has since been deleted are skipped rather than
    raising, the same way `resolve_meals` does.
    """
    meals = list(MEALS.values()) if meals is None else meals
    recipes = recipe_index()
    voted = [meal for meal in meals if meal.id in member.verdicts]
    voted.sort(
        key=lambda meal: (
            VERDICT_ORDER.get(member.verdicts[meal.id].verdict, 9),
            meal.name.lower(),
        )
    )
    return [to_card(meal, recipes, member) for meal in voted]
