from __future__ import annotations

from fastapi import HTTPException

from . import extract_url, thumbnail
from .classify import classify, emoji_for, is_fish_protein, is_vegetarian_protein
from .extract_image import extract_from_image, extract_from_text, extraction_available
from .meal_sync import register_recipe
from .models import (
    DataQuality,
    ExtractedRecipe,
    Recipe,
    RecipeCard,
    RecipePhoto,
    RecipeSource,
    TimeMinutes,
)
from .store import allocate_id, now_iso, save_recipe


def _build_card(extracted: ExtractedRecipe) -> RecipeCard:
    """Trust what the extractor read; fall back to keyword classification.

    The house rules key off these flags, so they are derived from the settled
    protein rather than taken from two sources that can disagree - a recipe was
    otherwise able to come out as both `nöt` and vegetarian.
    """
    ingredient_texts = [
        text for item in extracted.ingredients for text in (item.source_text, item.name) if text
    ]
    guess = classify(ingredient_texts, extracted.title)
    protein = extracted.protein or guess["protein"]

    # Err towards flagging: a missed fish or färs day breaks a house rule.
    is_fish = extracted.is_fish or guess["is_fish"] or is_fish_protein(protein)
    return RecipeCard(
        protein=protein,
        protein_form=extracted.protein_form,
        uses_minced_meat=extracted.uses_minced_meat or guess["uses_minced_meat"],
        is_fish=is_fish,
        is_vegetarian=is_vegetarian_protein(protein) and not is_fish,
        emoji=emoji_for(protein, is_vegetarian_protein(protein)),
        tags=extracted.tags,
    )


def build_recipe(
    extracted: ExtractedRecipe,
    source: RecipeSource,
    added_by: str | None,
    transcription_status: str,
) -> Recipe:
    return Recipe(
        id=allocate_id(extracted.title),
        title=extracted.title.strip(),
        source=source,
        servings=extracted.servings,
        time_minutes=TimeMinutes(total=extracted.total_minutes, printed_range=extracted.printed_time_range),
        card=_build_card(extracted),
        ingredients=extracted.ingredients,
        steps=extracted.steps,
        data_quality=DataQuality(transcription_status=transcription_status, notes=extracted.notes),
        added_by=added_by,
        added_at=now_iso(),
    )


def ingest_image(image_bytes: bytes, added_by: str | None, original_filename: str | None) -> Recipe:
    try:
        image = thumbnail.load_normalised(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    extracted = extract_from_image(thumbnail.to_vision_jpeg(image))
    recipe = build_recipe(
        extracted,
        RecipeSource(
            publisher=extracted.publisher,
            source_image=original_filename,
            source_tag=extracted.source_tag,
            retrieved_at=now_iso(),
        ),
        added_by,
        "draft_from_image",
    )
    recipe.photo = RecipePhoto(
        image_file=thumbnail.store_source_image(image, recipe.id),
        thumb_file=thumbnail.make_thumbnail(image, recipe.id, extracted.dish_box),
        dish_box=extracted.dish_box,
        crop_source="model" if extracted.dish_box else "heuristic",
    )
    return _persist(recipe)


def ingest_url(url: str, added_by: str | None) -> Recipe:
    page = extract_url.fetch_page(url)
    node = extract_url.find_recipe_node(page, url)

    if node:
        url = extract_url.canonical_url(node, page, url)
        extracted = extract_url.from_json_ld(node, url)
        status = "imported_from_web"
        image_url = extract_url.first_image_url(node, url)
    elif extraction_available():
        extracted = extract_from_text(extract_url.page_to_text(page), url)
        status = "draft_from_web_text"
        image_url = None
    else:
        raise HTTPException(
            status_code=422,
            detail="That page has no machine-readable recipe, and no Anthropic API key is configured to read it. Add the recipe by hand instead.",
        )

    if not extracted.ingredients and not extracted.steps:
        raise HTTPException(status_code=422, detail="No recipe could be read from that page")

    recipe = build_recipe(
        extracted,
        RecipeSource(
            publisher=extracted.publisher,
            source_url=url,
            source_tag=extracted.source_tag,
            retrieved_at=now_iso(),
        ),
        added_by,
        status,
    )

    if image_url:
        image_bytes = extract_url.fetch_image(image_url)
        if image_bytes:
            try:
                # A site's own recipe photo is already framed on the dish.
                recipe.photo = RecipePhoto(
                    thumb_file=thumbnail.thumbnail_from_bytes(image_bytes, recipe.id),
                    crop_source="source_photo",
                )
            except ValueError:
                pass

    return _persist(recipe)


def _persist(recipe: Recipe) -> Recipe:
    saved = save_recipe(recipe)
    register_recipe(saved)
    return saved
