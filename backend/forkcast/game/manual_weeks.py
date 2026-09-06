from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parents[3] / ".forkcast-data"
MANUAL_WEEKS_FILE = DATA_DIR / "manual-weeks.json"


class ManualWeekDayPlan(BaseModel):
    meal_name: str
    meal_emoji: str = "🍽️"
    chef: list[str] = Field(default_factory=list)
    cleanup: list[str] = Field(default_factory=list)


class SaveManualWeekRequest(BaseModel):
    year: int
    week: int
    days: list[str]
    plan: dict[str, ManualWeekDayPlan | None]


class ManualWeek(BaseModel):
    id: str
    updated_at: str
    year: int
    week: int
    days: list[str]
    plan: dict[str, ManualWeekDayPlan | None]


def _read_manual_weeks() -> dict[str, Any]:
    if not MANUAL_WEEKS_FILE.exists():
        return {}
    with MANUAL_WEEKS_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_manual_weeks(manual_weeks: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with MANUAL_WEEKS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(manual_weeks, handle, ensure_ascii=False, indent=2, sort_keys=True)


def save_manual_week(request: SaveManualWeekRequest) -> ManualWeek:
    if request.week < 1 or request.week > 53:
        raise HTTPException(status_code=400, detail="Week must be in range 1..53")

    manual_week_id = f"{request.year}-W{request.week:02d}"
    manual_week = ManualWeek(
        id=manual_week_id,
        updated_at=datetime.now(timezone.utc).isoformat(),
        year=request.year,
        week=request.week,
        days=request.days,
        plan=request.plan,
    )

    manual_weeks = _read_manual_weeks()
    manual_weeks[manual_week.id] = manual_week.model_dump(mode="json")
    _write_manual_weeks(manual_weeks)
    return manual_week


def get_manual_week(manual_week_id: str) -> ManualWeek:
    manual_weeks = _read_manual_weeks()
    manual_week = manual_weeks.get(manual_week_id)
    if not manual_week:
        raise HTTPException(status_code=404, detail="Manual week not found")
    return ManualWeek.model_validate(manual_week)
