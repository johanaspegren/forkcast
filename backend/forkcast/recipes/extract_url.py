from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from fastapi import HTTPException

from .models import ExtractedRecipe, Ingredient, Step

USER_AGENT = "Forkcast/0.1 (family recipe collection)"
FETCH_TIMEOUT = 12
MAX_PAGE_BYTES = 4_000_000
MAX_IMAGE_BYTES = 12_000_000

LD_JSON_PATTERN = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE
)
TAG_PATTERN = re.compile(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", re.DOTALL | re.IGNORECASE)
DURATION_PATTERN = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?", re.IGNORECASE)

FRACTIONS = {"½": "0.5", "¼": "0.25", "¾": "0.75", "⅓": "0.333", "⅔": "0.667", "⅛": "0.125"}
UNITS = {
    "g", "hg", "kg", "dl", "cl", "ml", "l", "msk", "tsk", "krm", "st", "kryddmått",
    "förp", "förpackning", "paket", "pkt", "burk", "påse", "klyfta", "klyftor", "nypa",
    "port", "portioner", "skiva", "skivor", "kruka", "gram", "liter",
}


def _guard_url(url: str) -> str:
    """Only public http(s) hosts - the backend must not be a proxy into the LAN."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=422, detail="Only http(s) recipe links are supported")
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise HTTPException(status_code=502, detail=f"Could not resolve {parsed.hostname}") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            raise HTTPException(status_code=422, detail="That link points to a private address")
    return parsed.geturl()


def fetch_page(url: str) -> str:
    safe_url = _guard_url(url)
    request = Request(safe_url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    try:
        with urlopen(request, timeout=FETCH_TIMEOUT) as response:
            raw = response.read(MAX_PAGE_BYTES)
            charset = response.headers.get_content_charset() or "utf-8"
    except OSError as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch that page: {exc}") from exc
    return raw.decode(charset, errors="replace")


def fetch_image(url: str) -> bytes | None:
    try:
        safe_url = _guard_url(url)
        request = Request(safe_url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=FETCH_TIMEOUT) as response:
            return response.read(MAX_IMAGE_BYTES)
    except (OSError, HTTPException):
        return None


def _iter_nodes(data: Any):
    if isinstance(data, list):
        for item in data:
            yield from _iter_nodes(item)
    elif isinstance(data, dict):
        yield data
        for key in ("@graph", "itemListElement", "mainEntity"):
            if key in data:
                yield from _iter_nodes(data[key])


def _is_recipe(node: dict) -> bool:
    node_type = node.get("@type")
    types = [node_type] if isinstance(node_type, str) else (node_type or [])
    return any(isinstance(value, str) and value.lower() == "recipe" for value in types)


def find_recipe_node(page: str, url: str | None = None) -> dict | None:
    """Pick the page's own recipe.

    Many sites embed related-recipe cards in the same markup, so prefer the node
    whose canonical url matches the page, then the one with the most ingredients.
    """
    candidates: list[dict] = []
    for block in LD_JSON_PATTERN.findall(page):
        try:
            data = json.loads(html.unescape(block.strip()))
        except json.JSONDecodeError:
            continue
        candidates.extend(node for node in _iter_nodes(data) if _is_recipe(node))

    if not candidates:
        return None
    if url:
        wanted = url.rstrip("/")
        for node in candidates:
            node_url = node.get("url") or node.get("@id")
            if isinstance(node_url, str) and node_url.rstrip("/") == wanted:
                return node
    return max(candidates, key=lambda node: len(node.get("recipeIngredient") or []))


def canonical_url(node: dict, page: str, fallback: str) -> str:
    """The url the recipe actually lives at, after any redirect or slug fixup."""
    node_url = node.get("url") or node.get("@id")
    if isinstance(node_url, str) and node_url.startswith("http"):
        return node_url
    match = re.search(r'property=["\']og:url["\'][^>]*content=["\']([^"\']+)["\']', page, re.IGNORECASE)
    return match.group(1) if match else fallback


def page_to_text(page: str, limit: int = 24000) -> str:
    text = TAG_PATTERN.sub(" ", page)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()[:limit]


def parse_duration(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    match = DURATION_PATTERN.fullmatch(value.strip())
    if not match or not any(match.groups()):
        return None
    days, hours, minutes = (int(group) if group else 0 for group in match.groups())
    total = days * 1440 + hours * 60 + minutes
    return total or None


def parse_yield(value: Any) -> int | None:
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if match:
            return int(match.group())
    return None


def _as_number(token: str) -> float | None:
    """A leading range ("2-3 dl") keeps its lower bound; source_text has the rest."""
    candidate = token.replace(",", ".").split("-")[0].split("–")[0]
    try:
        return float(candidate)
    except ValueError:
        return None


def parse_ingredient(line: str) -> Ingredient:
    """Split a printed ingredient line into quantity / unit / name.

    Handles both orders: "2 dl grädde" (most schema.org sites) and
    "Mjölk ½ dl" (how Swedish recipe cards print it).
    """
    source_text = re.sub(r"\s+", " ", line).strip()
    working = source_text
    for symbol, decimal in FRACTIONS.items():
        working = working.replace(symbol, f" {decimal} ")

    tokens = working.split()
    if not tokens:
        return Ingredient(name=source_text, source_text=source_text)

    # Amount first: "2 dl grädde"
    quantity = _as_number(tokens[0])
    if quantity is not None:
        index = 1
        unit = None
        if index < len(tokens) and tokens[index].lower().rstrip(".") in UNITS:
            unit = tokens[index].lower().rstrip(".")
            index += 1
        name = " ".join(tokens[index:]).strip() or source_text
        return Ingredient(name=name, quantity=quantity, unit=unit, source_text=source_text)

    # Amount last: "Mjölk 0.5 dl", "Kalkonfärs 450 g", "Ägg 1 st"
    tail_unit: str | None = None
    tail_index = len(tokens)
    if tokens[-1].lower().rstrip(".") in UNITS and len(tokens) >= 2:
        tail_unit = tokens[-1].lower().rstrip(".")
        tail_index = len(tokens) - 1
    if tail_index >= 1:
        quantity = _as_number(tokens[tail_index - 1])
        if quantity is not None:
            name = " ".join(tokens[: tail_index - 1]).strip()
            if name:
                return Ingredient(name=name, quantity=quantity, unit=tail_unit, source_text=source_text)

    return Ingredient(name=source_text, source_text=source_text)


def parse_instructions(value: Any) -> list[Step]:
    steps: list[Step] = []

    def add(text: str, section: str | None) -> None:
        cleaned = re.sub(r"\s+", " ", TAG_PATTERN.sub(" ", str(text))).strip()
        if cleaned:
            steps.append(Step(step=len(steps) + 1, section=section, text=cleaned))

    def walk(node: Any, section: str | None) -> None:
        if isinstance(node, str):
            add(node, section)
        elif isinstance(node, list):
            for item in node:
                walk(item, section)
        elif isinstance(node, dict):
            node_type = node.get("@type", "")
            if node_type == "HowToSection":
                walk(node.get("itemListElement", []), node.get("name") or section)
            else:
                walk(node.get("text") or node.get("name") or "", section)

    walk(value, None)
    return steps


def first_image_url(node: dict, base_url: str) -> str | None:
    image = node.get("image")
    while isinstance(image, list):
        image = image[0] if image else None
    if isinstance(image, dict):
        image = image.get("url") or image.get("contentUrl")
    return urljoin(base_url, image) if isinstance(image, str) and image else None


def _publisher_name(node: dict, url: str) -> str:
    for key in ("publisher", "author"):
        value = node.get(key)
        if isinstance(value, list):
            value = value[0] if value else None
        if isinstance(value, dict) and value.get("name"):
            return str(value["name"])
        if isinstance(value, str) and value.strip():
            return value.strip()
    return urlparse(url).hostname or "webb"


def from_json_ld(node: dict, url: str) -> ExtractedRecipe:
    ingredient_lines = [line for line in node.get("recipeIngredient", []) if isinstance(line, str)]
    tags = [
        tag.strip()
        for key in ("recipeCategory", "recipeCuisine", "keywords")
        for tag in (node.get(key) if isinstance(node.get(key), list) else str(node.get(key) or "").split(","))
        if isinstance(tag, str) and tag.strip()
    ]
    return ExtractedRecipe(
        title=str(node.get("name") or "Namnlöst recept").strip(),
        servings=parse_yield(node.get("recipeYield")),
        total_minutes=parse_duration(node.get("totalTime")) or parse_duration(node.get("cookTime")),
        publisher=_publisher_name(node, url),
        source_tag=(str(node.get("description")).strip()[:180] or None) if node.get("description") else None,
        tags=tags[:8],
        ingredients=[parse_ingredient(line) for line in ingredient_lines],
        steps=parse_instructions(node.get("recipeInstructions")),
    )
