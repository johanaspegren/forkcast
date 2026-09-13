from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from .classify import emoji_for, slugify
from .models import Recipe, RecipeCollection

DATA_DIR = Path(__file__).resolve().parents[3] / ".forkcast-data"
RECIPES_DIR = DATA_DIR / "recipes"
IMAGES_DIR = RECIPES_DIR / "images"
THUMBS_DIR = RECIPES_DIR / "thumbs"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    for directory in (RECIPES_DIR, IMAGES_DIR, THUMBS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def recipe_path(recipe_id: str) -> Path:
    return RECIPES_DIR / f"{recipe_id}.json"


def _write_atomic(path: Path, payload: dict) -> None:
    """Write through a temp file so a concurrent reader never sees a half file."""
    ensure_dirs()
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def allocate_id(title: str) -> str:
    """Slug from the title, suffixed only when it would collide."""
    base = slugify(title)
    if not recipe_path(base).exists():
        return base
    for suffix in range(2, 100):
        candidate = f"{base}-{suffix}"
        if not recipe_path(candidate).exists():
            return candidate
    return f"{base}-{int(datetime.now(timezone.utc).timestamp())}"


def save_recipe(recipe: Recipe) -> Recipe:
    recipe.updated_at = now_iso()
    if not recipe.added_at:
        recipe.added_at = recipe.updated_at
    if not recipe.card.emoji:
        # Keep the blob self-describing: imported collections often omit it.
        recipe.card.emoji = emoji_for(recipe.card.protein, recipe.card.is_vegetarian)
    _write_atomic(recipe_path(recipe.id), recipe.model_dump(mode="json"))
    return recipe


def get_recipe(recipe_id: str) -> Recipe:
    path = recipe_path(recipe_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Recipe not found")
    with path.open("r", encoding="utf-8") as handle:
        return Recipe.model_validate(json.load(handle))


def list_recipes() -> list[Recipe]:
    if not RECIPES_DIR.exists():
        return []
    recipes: list[Recipe] = []
    for path in sorted(RECIPES_DIR.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                recipes.append(Recipe.model_validate(json.load(handle)))
        except (json.JSONDecodeError, ValueError):
            # A malformed blob should not take the whole collection down.
            continue
    recipes.sort(key=lambda recipe: recipe.added_at or "", reverse=True)
    return recipes


def delete_recipe(recipe_id: str) -> None:
    recipe = get_recipe(recipe_id)
    for directory, name in ((IMAGES_DIR, recipe.photo.image_file), (THUMBS_DIR, recipe.photo.thumb_file)):
        if name:
            (directory / name).unlink(missing_ok=True)
    recipe_path(recipe_id).unlink(missing_ok=True)


def export_collection() -> RecipeCollection:
    return RecipeCollection(recipes=list_recipes())


def import_collection(collection: RecipeCollection) -> list[Recipe]:
    """Merge a forkcast_recipes.json style file. Existing ids are overwritten."""
    imported: list[Recipe] = []
    for recipe in collection.recipes:
        if not recipe.id:
            recipe.id = allocate_id(recipe.title)
        imported.append(save_recipe(recipe))
    return imported
