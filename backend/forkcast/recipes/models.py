from __future__ import annotations

from pydantic import BaseModel, Field

SCHEMA_VERSION = "0.1"
DEFAULT_LANGUAGE = "sv-SE"


class RecipeSource(BaseModel):
    """Where the recipe came from. At least one of the reference fields is set."""

    publisher: str | None = None
    source_url: str | None = None
    source_image: str | None = None
    source_tag: str | None = None
    retrieved_at: str | None = None


class TimeMinutes(BaseModel):
    total: int | None = None
    printed_range: str | None = None


class RecipeCard(BaseModel):
    """The game-facing summary of a recipe. Mirrors the Forkcast Meal model."""

    protein: str | None = None
    protein_form: str | None = None
    meal_type: str = "middag"
    uses_minced_meat: bool = False
    is_fish: bool = False
    is_vegetarian: bool = False
    emoji: str | None = None
    tags: list[str] = Field(default_factory=list)


class Ingredient(BaseModel):
    section: str | None = None
    name: str
    quantity: float | None = None
    unit: str | None = None
    source_text: str | None = None
    use: str | None = None


class Step(BaseModel):
    step: int
    section: str | None = None
    text: str


class DataQuality(BaseModel):
    transcription_status: str = "draft"
    notes: list[str] = Field(default_factory=list)


class DishBox(BaseModel):
    """Normalised 0-1 crop of the served dish inside the source image."""

    x: float
    y: float
    width: float
    height: float


class RecipePhoto(BaseModel):
    image_file: str | None = None
    thumb_file: str | None = None
    dish_box: DishBox | None = None
    crop_source: str | None = None


class Recipe(BaseModel):
    id: str
    title: str
    language: str = DEFAULT_LANGUAGE
    source: RecipeSource = Field(default_factory=RecipeSource)
    servings: int | None = None
    time_minutes: TimeMinutes = Field(default_factory=TimeMinutes)
    card: RecipeCard = Field(default_factory=RecipeCard)
    ingredients: list[Ingredient] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    photo: RecipePhoto = Field(default_factory=RecipePhoto)
    data_quality: DataQuality = Field(default_factory=DataQuality)
    added_by: str | None = None
    added_at: str | None = None
    updated_at: str | None = None


class RecipeCollection(BaseModel):
    """The portable export/import format, matching forkcast_recipes.json."""

    schema_version: str = SCHEMA_VERSION
    project: str = "Forkcast"
    language: str = DEFAULT_LANGUAGE
    recipes: list[Recipe] = Field(default_factory=list)


class ExtractedRecipe(BaseModel):
    """What the vision/text model is asked to return. Kept flat and free of
    server-owned fields (id, stored filenames, timestamps)."""

    title: str
    servings: int | None = None
    total_minutes: int | None = None
    printed_time_range: str | None = None
    publisher: str | None = None
    source_tag: str | None = None
    protein: str | None = None
    protein_form: str | None = None
    uses_minced_meat: bool = False
    is_fish: bool = False
    is_vegetarian: bool = False
    tags: list[str] = Field(default_factory=list)
    ingredients: list[Ingredient] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    dish_box: DishBox | None = None


class ImportUrlRequest(BaseModel):
    url: str
    added_by: str | None = None


class UpdateRecipeRequest(BaseModel):
    recipe: Recipe
