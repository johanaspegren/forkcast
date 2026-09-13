export type DishBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type RecipeSource = {
  publisher: string | null;
  source_url: string | null;
  source_image: string | null;
  source_tag: string | null;
  retrieved_at: string | null;
};

export type RecipeCard = {
  protein: string | null;
  protein_form: string | null;
  meal_type: string;
  uses_minced_meat: boolean;
  is_fish: boolean;
  is_vegetarian: boolean;
  emoji: string | null;
  tags: string[];
};

export type Ingredient = {
  section: string | null;
  name: string;
  quantity: number | null;
  unit: string | null;
  source_text: string | null;
  use: string | null;
};

export type RecipeStep = {
  step: number;
  section: string | null;
  text: string;
};

export type RecipePhoto = {
  image_file: string | null;
  thumb_file: string | null;
  dish_box: DishBox | null;
  crop_source: string | null;
};

export type Recipe = {
  id: string;
  title: string;
  language: string;
  source: RecipeSource;
  servings: number | null;
  time_minutes: { total: number | null; printed_range: string | null };
  card: RecipeCard;
  ingredients: Ingredient[];
  steps: RecipeStep[];
  photo: RecipePhoto;
  data_quality: { transcription_status: string; notes: string[] };
  added_by: string | null;
  added_at: string | null;
  updated_at: string | null;
};

export type RecipeCollectionFile = {
  schema_version: string;
  project: string;
  language: string;
  recipes: Recipe[];
};

export type RecipeStatus = {
  photo_import: boolean;
  model: string | null;
  count: number;
};

export const REVIEWED_STATUS = "reviewed";

// Imported collections use variants such as "reviewed_from_image"; anything a
// human has already signed off on counts as reviewed.
export function needsReview(recipe: Recipe) {
  return !recipe.data_quality.transcription_status.startsWith("reviewed");
}

export function ingredientLabel(ingredient: Ingredient) {
  const amount = [ingredient.quantity ?? "", ingredient.unit ?? ""].join(" ").trim();
  return amount ? `${ingredient.name} ${amount}` : ingredient.name;
}
