from __future__ import annotations

import re
import unicodedata

"""Deterministic Swedish/English ingredient classification.

URL imports carry no card metadata, so the protein and house-rule flags are
derived from the ingredient list. It also backstops the vision extractor when
it leaves a field empty.
"""

STOP_WORDS = {"med", "och", "i", "på", "till", "av", "en", "ett", "the", "with", "and"}

# Longest/most specific keywords first - the first match wins.
PROTEIN_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("skaldjur", ("räkor", "räka", "kräftor", "musslor", "scampi", "shrimp", "musse")),
    (
        "fisk",
        (
            "lax", "torsk", "sej", "kolja", "sill", "makrill", "tonfisk", "spätta",
            "abborre", "gös", "hoki", "rödspätta", "fiskfilé", "fisk", "salmon", "cod", "tuna",
        ),
    ),
    ("kalkon", ("kalkon", "turkey")),
    ("kyckling", ("kyckling", "chicken")),
    ("lamm", ("lamm", "lamb")),
    (
        "fläsk",
        ("fläsk", "bacon", "skinka", "kassler", "revben", "pork", "sidfläsk"),
    ),
    (
        "nöt",
        (
            "nötkött", "nötfärs", "köttfärs", "blandfärs", "oxfärs", "köttbullar", "högrev",
            "entrecote", "entrecôte", "oxfilé", "ryggbiff", "rostbiff", "biff", "oxkött",
            "beef", "flankstek", "kött",
        ),
    ),
    ("korv", ("korv", "chorizo", "sausage")),
    ("ägg", ("ägg", "egg")),
    ("halloumi", ("halloumi", "fetaost", "paneer")),
    ("tofu", ("tofu", "tempeh", "quorn", "sojafärs")),
]

EMOJI_BY_PROTEIN = {
    "fisk": "🐟",
    "skaldjur": "🦐",
    "kyckling": "🍗",
    "kalkon": "🦃",
    "nöt": "🥩",
    "fläsk": "🥓",
    "lamm": "🍖",
    "korv": "🌭",
    "ägg": "🍳",
    "halloumi": "🧀",
    "tofu": "🌱",
    "vegetarisk": "🥗",
}

# `färs` as a whole word or word suffix, but not inside `färsk` (fresh).
MINCED_PATTERN = re.compile(r"(?<![a-zåäö])[a-zåäö]*färs(?![a-zåäö])", re.IGNORECASE)
MINCED_EXTRA = ("köttfärs", "blandfärs", "minced", "ground beef")

VEGETARIAN_EXCLUDES = {"fisk", "skaldjur", "kyckling", "kalkon", "nöt", "fläsk", "lamm", "korv"}
FISH_PROTEINS = {"fisk", "skaldjur"}


def is_vegetarian_protein(protein: str | None) -> bool:
    return (protein or "vegetarisk") not in VEGETARIAN_EXCLUDES


def is_fish_protein(protein: str | None) -> bool:
    return (protein or "") in FISH_PROTEINS


def ascii_fold(value: str) -> str:
    """Fold Swedish characters the way the reference ids do (å/ä->a, ö->o, é->e)."""
    lowered = value.lower().replace("å", "a").replace("ä", "a").replace("ö", "o")
    decomposed = unicodedata.normalize("NFKD", lowered)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def slugify(value: str, max_words: int = 6) -> str:
    folded = ascii_fold(value)
    words = [word for word in re.split(r"[^a-z0-9]+", folded) if word]
    meaningful = [word for word in words if word not in STOP_WORDS] or words
    return "-".join(meaningful[:max_words]) or "recept"


def _haystack(ingredient_texts: list[str], title: str = "") -> str:
    return " ".join([title, *ingredient_texts]).lower()


def detect_protein(ingredient_texts: list[str], title: str = "") -> str:
    hay = _haystack(ingredient_texts, title)
    for protein, keywords in PROTEIN_KEYWORDS:
        if any(keyword in hay for keyword in keywords):
            return protein
    return "vegetarisk"


def detect_minced(ingredient_texts: list[str], title: str = "") -> bool:
    hay = _haystack(ingredient_texts, title)
    if MINCED_PATTERN.search(hay):
        return True
    return any(keyword in hay for keyword in MINCED_EXTRA)


def classify(ingredient_texts: list[str], title: str = "") -> dict:
    protein = detect_protein(ingredient_texts, title)
    return {
        "protein": protein,
        "uses_minced_meat": detect_minced(ingredient_texts, title),
        "is_fish": protein in {"fisk", "skaldjur"},
        "is_vegetarian": protein not in VEGETARIAN_EXCLUDES,
        "emoji": EMOJI_BY_PROTEIN.get(protein, "🍽️"),
    }


def emoji_for(protein: str | None, is_vegetarian: bool = False) -> str:
    if protein and protein in EMOJI_BY_PROTEIN:
        return EMOJI_BY_PROTEIN[protein]
    return "🥗" if is_vegetarian else "🍽️"
