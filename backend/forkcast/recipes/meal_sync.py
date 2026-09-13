from __future__ import annotations

"""Bridge between the recipe collection and the game's meal pool.

`MEALS` in the engine is a module-level dict that the whole engine subscripts
directly, so recipe-backed meals are merged into that same dict object rather
than threaded through every call site. Nothing in `game/` imports this module,
which keeps the game engine independent of the recipe layer.
"""

from ..game.engine import MEALS, engine
from ..game.models import Meal
from .classify import emoji_for
from .models import Recipe

MEAL_ID_PREFIX = "recipe-"


def meal_id_for(recipe_id: str) -> str:
    return f"{MEAL_ID_PREFIX}{recipe_id}"


def recipe_to_meal(recipe: Recipe) -> Meal:
    card = recipe.card
    return Meal(
        id=meal_id_for(recipe.id),
        name=recipe.title,
        emoji=card.emoji or emoji_for(card.protein, card.is_vegetarian),
        tags=card.tags,
        protein_type=card.protein,
        minced_meat=card.uses_minced_meat,
        fish=card.is_fish,
    )


def register_recipe(recipe: Recipe) -> Meal:
    meal = recipe_to_meal(recipe)
    MEALS[meal.id] = meal
    return meal


def unregister_recipe(recipe_id: str) -> bool:
    """Drop a deleted recipe from the pool unless a live session still names it.

    Sessions hold meal ids in proposals and locked days; removing an id they
    reference would make the engine raise on the next lookup.
    """
    meal_id = meal_id_for(recipe_id)
    if meal_id not in MEALS:
        return False
    if _in_use(meal_id):
        return False
    del MEALS[meal_id]
    return True


def _in_use(meal_id: str) -> bool:
    for session in engine.sessions.values():
        if any(proposal.meal_id == meal_id for proposal in session.proposals.values()):
            return True
        if any(entry and entry.meal_id == meal_id for entry in session.week.values()):
            return True
        if any(meal_id in state.selected_meals or meal_id in state.meal_cards for state in session.player_state.values()):
            return True
    return False


def sync_recipe_meals() -> int:
    """Load every stored recipe into the meal pool. Called once at startup."""
    from .store import list_recipes

    recipes = list_recipes()
    for recipe in recipes:
        register_recipe(recipe)
    return len(recipes)
