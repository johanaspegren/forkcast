from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps

from .models import DishBox
from .store import IMAGES_DIR, THUMBS_DIR, ensure_dirs

MAX_STORED_EDGE = 2000
MAX_VISION_EDGE = 1600
THUMB_SIZE = 480
ANALYSIS_WIDTH = 160


def load_normalised(data: bytes) -> Image.Image:
    """Decode and apply the EXIF orientation so every later coordinate agrees."""
    try:
        image = Image.open(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001 - Pillow raises a wide range here
        raise ValueError("Could not read that image file") from exc
    return ImageOps.exif_transpose(image).convert("RGB")


def _downscale(image: Image.Image, max_edge: int) -> Image.Image:
    width, height = image.size
    if max(width, height) <= max_edge:
        return image
    scale = max_edge / max(width, height)
    return image.resize((round(width * scale), round(height * scale)), Image.LANCZOS)


def store_source_image(image: Image.Image, recipe_id: str) -> str:
    """Keep a readable copy of the card as the source reference."""
    ensure_dirs()
    filename = f"{recipe_id}.jpg"
    _downscale(image, MAX_STORED_EDGE).save(IMAGES_DIR / filename, "JPEG", quality=86, optimize=True)
    return filename


def to_vision_jpeg(image: Image.Image) -> bytes:
    """A downscaled JPEG for the model - full 4032px originals waste tokens."""
    buffer = io.BytesIO()
    _downscale(image, MAX_VISION_EDGE).save(buffer, "JPEG", quality=82, optimize=True)
    return buffer.getvalue()


def heuristic_dish_box(image: Image.Image) -> DishBox:
    """Fallback when no model box is available.

    Recipe cards are bright paper with one saturated food photo on them. Find
    the paper first (so a wooden table around the page is excluded), then the
    saturated block inside it. Rough, but better than a centre crop.
    """
    width, height = image.size
    grid_height = max(1, round(ANALYSIS_WIDTH * height / width))
    hsv = image.resize((ANALYSIS_WIDTH, grid_height), Image.BOX).convert("HSV")
    pixels = hsv.load()

    def span(values: list[float], threshold: float) -> tuple[int, int]:
        hits = [index for index, value in enumerate(values) if value >= threshold]
        return (hits[0], hits[-1]) if hits else (0, len(values) - 1)

    paper = [[1 if pixels[x, y][2] > 150 else 0 for x in range(ANALYSIS_WIDTH)] for y in range(grid_height)]
    top, bottom = span([sum(row) / ANALYSIS_WIDTH for row in paper], 0.55)
    left, right = span(
        [sum(paper[y][x] for y in range(grid_height)) / grid_height for x in range(ANALYSIS_WIDTH)], 0.55
    )

    inner_width = max(1, right - left + 1)
    inner_height = max(1, bottom - top + 1)
    saturated = [[0] * ANALYSIS_WIDTH for _ in range(grid_height)]
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            _, saturation, value = pixels[x, y]
            saturated[y][x] = 1 if saturation > 60 and value > 40 else 0

    photo_top, photo_bottom = span(
        [sum(saturated[y][left : right + 1]) / inner_width for y in range(grid_height)], 0.30
    )
    photo_left, photo_right = span(
        [sum(saturated[y][x] for y in range(top, bottom + 1)) / inner_height for x in range(ANALYSIS_WIDTH)],
        0.30,
    )

    return DishBox(
        x=photo_left / ANALYSIS_WIDTH,
        y=photo_top / grid_height,
        width=(photo_right - photo_left + 1) / ANALYSIS_WIDTH,
        height=(photo_bottom - photo_top + 1) / grid_height,
    )


def make_thumbnail(image: Image.Image, recipe_id: str, box: DishBox | None) -> str:
    """Square thumbnail centred on the served dish."""
    ensure_dirs()
    width, height = image.size
    box = box or heuristic_dish_box(image)

    left = max(0.0, min(1.0, box.x)) * width
    top = max(0.0, min(1.0, box.y)) * height
    right = min(float(width), left + max(0.01, box.width) * width)
    bottom = min(float(height), top + max(0.01, box.height) * height)

    # Square up around the centre so plates are not stretched or sliced.
    centre_x, centre_y = (left + right) / 2, (top + bottom) / 2
    side = min(max(right - left, bottom - top), float(width), float(height))
    half = side / 2
    centre_x = min(max(centre_x, half), width - half)
    centre_y = min(max(centre_y, half), height - half)
    crop = (round(centre_x - half), round(centre_y - half), round(centre_x + half), round(centre_y + half))

    filename = f"{recipe_id}.jpg"
    image.crop(crop).resize((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS).save(
        THUMBS_DIR / filename, "JPEG", quality=85, optimize=True
    )
    return filename


def thumbnail_from_bytes(data: bytes, recipe_id: str) -> str:
    """Thumbnail a photo fetched from a recipe web page."""
    return make_thumbnail(load_normalised(data), recipe_id, DishBox(x=0, y=0, width=1, height=1))


def existing_file(directory: Path, name: str | None) -> Path | None:
    if not name:
        return None
    path = directory / name
    return path if path.exists() else None
