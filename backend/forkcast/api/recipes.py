from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.forkcast.recipes import store, thumbnail
from backend.forkcast.recipes.extract_image import extraction_available, resolve_model
from backend.forkcast.recipes.ingest import ingest_image, ingest_url
from backend.forkcast.recipes.meal_sync import meal_id_for, register_recipe, unregister_recipe
from backend.forkcast.recipes.models import ImportUrlRequest, Recipe, RecipeCollection

router = APIRouter(prefix="/api/recipes")

MAX_UPLOAD_BYTES = 25_000_000
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


@router.get("/status")
def status() -> dict:
    return {
        "photo_import": extraction_available(),
        "model": resolve_model() if extraction_available() else None,
        "count": len(store.list_recipes()),
    }


@router.get("")
def list_recipes() -> list[Recipe]:
    return store.list_recipes()


@router.get("/export")
def export_collection() -> RecipeCollection:
    return store.export_collection()


@router.post("/import-collection")
def import_collection(collection: RecipeCollection) -> list[Recipe]:
    imported = store.import_collection(collection)
    for recipe in imported:
        register_recipe(recipe)
    return imported


@router.post("/import-url")
def import_url(request: ImportUrlRequest) -> Recipe:
    return ingest_url(request.url, request.added_by)


@router.post("/import-image")
async def import_image(file: UploadFile = File(...), added_by: str | None = Form(None)) -> Recipe:
    if file.content_type and file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=422, detail=f"Unsupported image type: {file.content_type}")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="That photo is larger than 25 MB")
    if not data:
        raise HTTPException(status_code=422, detail="The uploaded file was empty")
    return ingest_image(data, added_by, file.filename)


@router.get("/{recipe_id}")
def get_recipe(recipe_id: str) -> Recipe:
    return store.get_recipe(recipe_id)


@router.put("/{recipe_id}")
def update_recipe(recipe_id: str, recipe: Recipe) -> Recipe:
    store.get_recipe(recipe_id)  # 404 if it is not there
    if recipe.id != recipe_id:
        raise HTTPException(status_code=422, detail="Recipe id in the body does not match the URL")
    saved = store.save_recipe(recipe)
    register_recipe(saved)
    return saved


@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: str) -> dict:
    store.delete_recipe(recipe_id)
    removed = unregister_recipe(recipe_id)
    return {
        "status": "deleted",
        "meal_id": meal_id_for(recipe_id),
        "meal_removed": removed,
        "detail": None if removed else "Kept in the meal pool until the sessions using it end",
    }


@router.get("/{recipe_id}/thumb")
def recipe_thumb(recipe_id: str) -> FileResponse:
    recipe = store.get_recipe(recipe_id)
    path = thumbnail.existing_file(store.THUMBS_DIR, recipe.photo.thumb_file)
    if not path:
        raise HTTPException(status_code=404, detail="No thumbnail for this recipe")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/{recipe_id}/image")
def recipe_image(recipe_id: str) -> FileResponse:
    recipe = store.get_recipe(recipe_id)
    path = thumbnail.existing_file(store.IMAGES_DIR, recipe.photo.image_file)
    if not path:
        raise HTTPException(status_code=404, detail="No source image for this recipe")
    return FileResponse(path, media_type="image/jpeg")


@router.post("/{recipe_id}/recrop")
def recrop(recipe_id: str, box: dict) -> Recipe:
    """Re-cut the thumbnail when the automatic crop missed the dish."""
    recipe = store.get_recipe(recipe_id)
    path = thumbnail.existing_file(store.IMAGES_DIR, recipe.photo.image_file)
    if not path:
        raise HTTPException(status_code=404, detail="No source image to crop")

    from backend.forkcast.recipes.models import DishBox

    dish_box = DishBox.model_validate(box)
    image = thumbnail.load_normalised(path.read_bytes())
    recipe.photo.thumb_file = thumbnail.make_thumbnail(image, recipe.id, dish_box)
    recipe.photo.dish_box = dish_box
    recipe.photo.crop_source = "manual"
    return store.save_recipe(recipe)
