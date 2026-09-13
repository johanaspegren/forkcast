import type { Recipe, RecipeCollectionFile, RecipeStatus } from "../recipes/recipeTypes";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${response.status}`);
  }
  return response.json();
}

export const recipeApi = {
  status: () => request<RecipeStatus>("/api/recipes/status"),
  list: () => request<Recipe[]>("/api/recipes"),
  get: (id: string) => request<Recipe>(`/api/recipes/${id}`),
  update: (recipe: Recipe) =>
    request<Recipe>(`/api/recipes/${recipe.id}`, { method: "PUT", body: JSON.stringify(recipe) }),
  remove: (id: string) => request<{ status: string }>(`/api/recipes/${id}`, { method: "DELETE" }),
  importUrl: (url: string, addedBy: string) =>
    request<Recipe>("/api/recipes/import-url", {
      method: "POST",
      body: JSON.stringify({ url, added_by: addedBy || null })
    }),
  exportCollection: () => request<RecipeCollectionFile>("/api/recipes/export"),
  importCollection: (collection: RecipeCollectionFile) =>
    request<Recipe[]>("/api/recipes/import-collection", {
      method: "POST",
      body: JSON.stringify(collection)
    }),
  // Multipart: the browser must set its own boundary, so no JSON headers here.
  importImage: async (file: File, addedBy: string) => {
    const form = new FormData();
    form.append("file", file);
    if (addedBy) form.append("added_by", addedBy);
    const response = await fetch("/api/recipes/import-image", { method: "POST", body: form });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail ?? `Upload failed: ${response.status}`);
    }
    return (await response.json()) as Recipe;
  },
  thumbUrl: (recipe: Recipe) =>
    recipe.photo.thumb_file ? `/api/recipes/${recipe.id}/thumb?v=${encodeURIComponent(recipe.updated_at ?? "")}` : null,
  imageUrl: (recipe: Recipe) => (recipe.photo.image_file ? `/api/recipes/${recipe.id}/image` : null)
};
