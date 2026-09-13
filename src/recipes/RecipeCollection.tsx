import { ArrowLeft, Camera, Check, Clock, Download, Link2, Loader2, Search, Trash2, Upload, Users } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { recipeApi } from "../api/recipes";
import { REVIEWED_STATUS, needsReview, type Recipe, type RecipeStatus } from "./recipeTypes";

const PLAYER_PROFILE_KEY = "forkcast.playerProfile";

const PROTEIN_FILTERS = [
  { id: "all", label: "Alla" },
  { id: "kott", label: "Kött" },
  { id: "fagel", label: "Fågel" },
  { id: "fisk", label: "Fisk" },
  { id: "veg", label: "Vegetariskt" }
];

const STATUS_LABELS: Record<string, string> = {
  reviewed: "Granskad",
  draft_from_image: "Utkast från foto",
  draft_from_web_text: "Utkast från webbsida",
  imported_from_web: "Hämtad från webben",
  reviewed_from_image: "Granskad från foto"
};

function readName() {
  try {
    const profile = JSON.parse(localStorage.getItem(PLAYER_PROFILE_KEY) ?? "{}") as { name?: string };
    return profile.name ?? "";
  } catch {
    return "";
  }
}

function matchesProtein(recipe: Recipe, filter: string) {
  const protein = recipe.card.protein ?? "";
  if (filter === "all") return true;
  if (filter === "fisk") return recipe.card.is_fish;
  if (filter === "veg") return recipe.card.is_vegetarian;
  if (filter === "fagel") return protein === "kyckling" || protein === "kalkon";
  if (filter === "kott") return ["nöt", "fläsk", "lamm", "korv"].includes(protein);
  return true;
}

export default function RecipeCollection() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [status, setStatus] = useState<RecipeStatus | null>(null);
  const [selected, setSelected] = useState<Recipe | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [addedBy, setAddedBy] = useState(readName);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const cameraInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    recipeApi.list().then(setRecipes).catch((err) => setError(err.message));
    recipeApi.status().then(setStatus).catch(() => setStatus(null));
  }, []);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return recipes.filter((recipe) => {
      if (!matchesProtein(recipe, filter)) return false;
      if (!needle) return true;
      const haystack = [
        recipe.title,
        recipe.card.protein ?? "",
        recipe.source.publisher ?? "",
        ...recipe.card.tags,
        ...recipe.ingredients.map((item) => item.name)
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [recipes, query, filter]);

  function upsert(recipe: Recipe) {
    setRecipes((current) => [recipe, ...current.filter((item) => item.id !== recipe.id)]);
  }

  async function addImages(files: File[]) {
    const images = files.filter((file) => file.type.startsWith("image/"));
    if (!images.length) {
      setError("Släpp en bild på ett recept");
      return;
    }
    setError("");
    for (const [index, file] of images.entries()) {
      setBusy(`Läser ${file.name} (${index + 1}/${images.length})…`);
      try {
        upsert(await recipeApi.importImage(file, addedBy));
        setNotice(`${file.name} tillagd`);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Kunde inte läsa bilden");
        break;
      }
    }
    setBusy("");
  }

  async function addUrl() {
    if (!url.trim()) return;
    setBusy("Hämtar receptet…");
    setError("");
    try {
      upsert(await recipeApi.importUrl(url.trim(), addedBy));
      setUrl("");
      setNotice("Receptet tillagt");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte hämta receptet");
    }
    setBusy("");
  }

  async function exportCollection() {
    try {
      const collection = await recipeApi.exportCollection();
      const blob = new Blob([JSON.stringify(collection, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "forkcast_recipes.json";
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte exportera");
    }
  }

  async function importCollectionFile(file: File) {
    setBusy("Importerar samling…");
    try {
      const parsed = JSON.parse(await file.text());
      const imported = await recipeApi.importCollection(parsed);
      imported.forEach(upsert);
      setNotice(`${imported.length} recept importerade`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte importera filen");
    }
    setBusy("");
  }

  function handleDrop(event: React.DragEvent) {
    event.preventDefault();
    setDragging(false);
    const files = Array.from(event.dataTransfer.files);
    const collection = files.find((file) => file.name.endsWith(".json"));
    if (collection) {
      void importCollectionFile(collection);
      return;
    }
    void addImages(files);
  }

  if (selected) {
    return (
      <RecipeDetail
        recipe={selected}
        onBack={() => setSelected(null)}
        onChanged={(recipe) => {
          upsert(recipe);
          setSelected(recipe);
        }}
        onDeleted={(id) => {
          setRecipes((current) => current.filter((item) => item.id !== id));
          setSelected(null);
        }}
      />
    );
  }

  return (
    <main className="shell recipe-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Familjens recept</p>
          <h1>Receptsamling</h1>
        </div>
        <a className="recipe-back-link" href="/">
          <ArrowLeft size={18} /> Spelet
        </a>
      </header>

      <section
        className={dragging ? "panel recipe-dropzone dragging" : "panel recipe-dropzone"}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <label>
          Ditt namn
          <input value={addedBy} onChange={(event) => setAddedBy(event.target.value)} placeholder="Johan" />
        </label>

        <div className="recipe-drop-target">
          <Upload size={26} />
          <strong>Släpp ett foto på ett recept här</strong>
          <span>eller en forkcast_recipes.json för att importera en hel samling</span>
          <div className="recipe-drop-buttons">
            <button className="primary" onClick={() => fileInput.current?.click()} type="button">
              Välj bild
            </button>
            <button onClick={() => cameraInput.current?.click()} type="button">
              <Camera size={16} /> Fotografera
            </button>
          </div>
          <input
            accept="image/*,application/json"
            hidden
            multiple
            onChange={(event) => {
              const files = Array.from(event.target.files ?? []);
              const collection = files.find((file) => file.name.endsWith(".json"));
              if (collection) void importCollectionFile(collection);
              else void addImages(files);
              event.target.value = "";
            }}
            ref={fileInput}
            type="file"
          />
          <input
            accept="image/*"
            capture="environment"
            hidden
            onChange={(event) => {
              void addImages(Array.from(event.target.files ?? []));
              event.target.value = "";
            }}
            ref={cameraInput}
            type="file"
          />
        </div>

        <div className="recipe-url-row">
          <Link2 size={18} />
          <input
            onChange={(event) => setUrl(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && addUrl()}
            placeholder="Klistra in en länk till ett recept"
            value={url}
          />
          <button className="primary" disabled={!url.trim() || Boolean(busy)} onClick={addUrl} type="button">
            Lägg till
          </button>
        </div>

        {status && !status.photo_import && (
          <p className="recipe-hint">
            Foton kan inte läsas av automatiskt — servern saknar ANTHROPIC_API_KEY. Länkar fungerar ändå.
          </p>
        )}
        {busy && (
          <p className="recipe-busy">
            <Loader2 className="spin" size={16} /> {busy}
          </p>
        )}
        {error && <p className="error">{error}</p>}
        {notice && !error && <p className="recipe-notice">{notice}</p>}
      </section>

      <section className="panel recipe-browse">
        <div className="recipe-search">
          <Search size={18} />
          <input
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Sök på rätt, råvara eller märke"
            value={query}
          />
        </div>
        <div className="recipe-filters">
          {PROTEIN_FILTERS.map((option) => (
            <button
              className={filter === option.id ? "recipe-filter selected" : "recipe-filter"}
              key={option.id}
              onClick={() => setFilter(option.id)}
              type="button"
            >
              {option.label}
            </button>
          ))}
          <button className="recipe-filter ghost" onClick={exportCollection} type="button">
            <Download size={14} /> Exportera
          </button>
        </div>

        <p className="recipe-count">
          {visible.length} av {recipes.length} recept
        </p>

        {visible.length === 0 ? (
          <p className="recipe-empty">
            {recipes.length === 0 ? "Inga recept än — släpp ett foto eller klistra in en länk." : "Inga träffar."}
          </p>
        ) : (
          <div className="recipe-grid">
            {visible.map((recipe) => (
              <button className="recipe-tile" key={recipe.id} onClick={() => setSelected(recipe)} type="button">
                <div className="recipe-thumb">
                  {recipeApi.thumbUrl(recipe) ? (
                    <img alt="" loading="lazy" src={recipeApi.thumbUrl(recipe)!} />
                  ) : (
                    <span className="recipe-thumb-fallback">{recipe.card.emoji ?? "🍽️"}</span>
                  )}
                  {needsReview(recipe) && <span className="recipe-badge">Granska</span>}
                </div>
                <strong>{recipe.title}</strong>
                <small>
                  {recipe.time_minutes.total ? `${recipe.time_minutes.total} min` : recipe.card.protein ?? ""}
                  {recipe.servings ? ` · ${recipe.servings} port` : ""}
                </small>
              </button>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function RecipeDetail({
  recipe,
  onBack,
  onChanged,
  onDeleted
}: {
  recipe: Recipe;
  onBack: () => void;
  onChanged: (recipe: Recipe) => void;
  onDeleted: (id: string) => void;
}) {
  const [draft, setDraft] = useState(recipe);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDraft(recipe);
    setEditing(false);
  }, [recipe.id]);

  const sections = useMemo(() => {
    const grouped = new Map<string, typeof draft.ingredients>();
    for (const ingredient of draft.ingredients) {
      const key = ingredient.section ?? "";
      grouped.set(key, [...(grouped.get(key) ?? []), ingredient]);
    }
    return Array.from(grouped.entries());
  }, [draft.ingredients]);

  async function save(next: Recipe) {
    setSaving(true);
    setError("");
    try {
      onChanged(await recipeApi.update(next));
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte spara");
    }
    setSaving(false);
  }

  async function remove() {
    if (!window.confirm(`Ta bort ${recipe.title}?`)) return;
    try {
      await recipeApi.remove(recipe.id);
      onDeleted(recipe.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ta bort");
    }
  }

  const thumb = recipeApi.thumbUrl(draft);
  const image = recipeApi.imageUrl(draft);

  return (
    <main className="shell recipe-shell">
      <header className="topbar">
        <button className="recipe-back-link" onClick={onBack} type="button">
          <ArrowLeft size={18} /> Tillbaka
        </button>
      </header>

      <section className="panel recipe-detail">
        {thumb && <img alt="" className="recipe-hero" src={thumb} />}

        {editing ? (
          <label>
            Titel
            <input onChange={(event) => setDraft({ ...draft, title: event.target.value })} value={draft.title} />
          </label>
        ) : (
          <h2>{draft.title}</h2>
        )}

        <div className="recipe-meta">
          {draft.time_minutes.total && (
            <span>
              <Clock size={14} /> {draft.time_minutes.printed_range ?? `${draft.time_minutes.total} min`}
            </span>
          )}
          {draft.servings && (
            <span>
              <Users size={14} /> {draft.servings} portioner
            </span>
          )}
          {draft.card.emoji && <span>{draft.card.emoji} {draft.card.protein}</span>}
        </div>

        <p className="recipe-source">
          {draft.source.publisher && <strong>{draft.source.publisher}</strong>}
          {draft.source.source_url && (
            <>
              {" · "}
              <a href={draft.source.source_url} rel="noreferrer noopener" target="_blank">
                Källa
              </a>
            </>
          )}
          {draft.source.source_image && <> · Foto: {draft.source.source_image}</>}
          {draft.added_by && <> · Tillagd av {draft.added_by}</>}
        </p>

        <p className="recipe-status-line">
          {STATUS_LABELS[draft.data_quality.transcription_status] ?? draft.data_quality.transcription_status}
        </p>

        {draft.data_quality.notes.length > 0 && (
          <ul className="recipe-notes">
            {draft.data_quality.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        )}

        <div className="recipe-actions">
          {needsReview(draft) && (
            <button
              className="primary"
              disabled={saving}
              onClick={() =>
                save({
                  ...draft,
                  data_quality: { ...draft.data_quality, transcription_status: REVIEWED_STATUS }
                })
              }
              type="button"
            >
              <Check size={16} /> Markera som granskad
            </button>
          )}
          <button onClick={() => (editing ? save(draft) : setEditing(true))} type="button" disabled={saving}>
            {editing ? "Spara ändringar" : "Redigera"}
          </button>
          <button className="recipe-danger" onClick={remove} type="button">
            <Trash2 size={16} /> Ta bort
          </button>
        </div>

        {error && <p className="error">{error}</p>}
      </section>

      <section className="panel">
        <h3>Ingredienser</h3>
        {sections.map(([section, items]) => (
          <div className="recipe-section" key={section || "default"}>
            {section && <h4>{section}</h4>}
            <ul className="recipe-ingredients">
              {items.map((ingredient, index) => {
                const position = draft.ingredients.indexOf(ingredient);
                return editing ? (
                  <li className="recipe-ingredient-edit" key={`${ingredient.name}-${index}`}>
                    <input
                      onChange={(event) => {
                        const next = [...draft.ingredients];
                        next[position] = { ...ingredient, name: event.target.value };
                        setDraft({ ...draft, ingredients: next });
                      }}
                      value={ingredient.name}
                    />
                    <input
                      className="recipe-qty"
                      onChange={(event) => {
                        const next = [...draft.ingredients];
                        const parsed = Number(event.target.value.replace(",", "."));
                        next[position] = {
                          ...ingredient,
                          quantity: event.target.value === "" || Number.isNaN(parsed) ? null : parsed
                        };
                        setDraft({ ...draft, ingredients: next });
                      }}
                      value={ingredient.quantity ?? ""}
                    />
                    <input
                      className="recipe-unit"
                      onChange={(event) => {
                        const next = [...draft.ingredients];
                        next[position] = { ...ingredient, unit: event.target.value || null };
                        setDraft({ ...draft, ingredients: next });
                      }}
                      value={ingredient.unit ?? ""}
                    />
                  </li>
                ) : (
                  <li key={`${ingredient.name}-${index}`}>
                    <span>{ingredient.name}</span>
                    <em>
                      {ingredient.quantity ?? ""} {ingredient.unit ?? ""}
                    </em>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </section>

      <section className="panel">
        <h3>Gör så här</h3>
        <ol className="recipe-steps">
          {draft.steps.map((step) => (
            <li key={step.step}>
              {step.section && <strong>{step.section}: </strong>}
              {step.text}
            </li>
          ))}
        </ol>
      </section>

      {image && (
        <section className="panel">
          <h3>Originalbild</h3>
          <img alt={`Receptkort för ${draft.title}`} className="recipe-original" src={image} />
        </section>
      )}
    </main>
  );
}
