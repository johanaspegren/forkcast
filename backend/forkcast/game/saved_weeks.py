from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from .engine import MEALS
from .models import GamePhase, Session

DATA_DIR = Path(__file__).resolve().parents[3] / ".forkcast-data"
SAVED_WEEKS_FILE = DATA_DIR / "saved-weeks.json"


class SaveWeekRequest(BaseModel):
    session_id: str
    year: int
    week: int


class SavedWeek(BaseModel):
    id: str
    saved_at: str
    session_id: str
    join_code: str
    year: int
    week: int
    days: list[str]
    plan: dict[str, dict[str, Any] | None]
    rule_overrides: list[str] = Field(default_factory=list)


def _read_saved_weeks() -> dict[str, Any]:
    if not SAVED_WEEKS_FILE.exists():
        return {}
    with SAVED_WEEKS_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_saved_weeks(saved_weeks: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with SAVED_WEEKS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(saved_weeks, handle, ensure_ascii=False, indent=2, sort_keys=True)


def build_saved_week(session: Session, request: SaveWeekRequest) -> SavedWeek:
    if session.phase != GamePhase.COMPLETE:
        raise HTTPException(status_code=409, detail="Only completed Forkcasts can be saved")

    if not all(session.week.values()):
        raise HTTPException(status_code=409, detail="The Forkcast week is not fully locked")

    saved_week_id = f"{request.year}-W{request.week:02d}"
    plan = {}
    for day in session.days:
        entry = session.week[day]
        if not entry:
            plan[day] = None
            continue
        meal = MEALS.get(entry.meal_id)
        plan[day] = {
            "meal_id": entry.meal_id,
            "meal_name": meal.name if meal else entry.meal_id,
            "meal_emoji": meal.emoji if meal else "",
            "chef": [session.players[player_id].name if player_id in session.players else player_id for player_id in entry.chef],
            "cleanup": [
                session.players[player_id].name if player_id in session.players else player_id
                for player_id in entry.cleanup
            ],
            "rule_exceptions": entry.rule_exceptions,
        }

    return SavedWeek(
        id=saved_week_id,
        saved_at=datetime.now(timezone.utc).isoformat(),
        session_id=session.id,
        join_code=session.join_code,
        year=request.year,
        week=request.week,
        days=session.days,
        plan=plan,
        rule_overrides=session.rule_overrides,
    )


def save_week(session: Session, request: SaveWeekRequest) -> SavedWeek:
    saved_week = build_saved_week(session, request)
    saved_weeks = _read_saved_weeks()
    saved_weeks[saved_week.id] = saved_week.model_dump(mode="json")
    _write_saved_weeks(saved_weeks)
    return saved_week


def list_saved_weeks() -> list[SavedWeek]:
    saved_weeks = _read_saved_weeks()
    return [SavedWeek.model_validate(value) for value in saved_weeks.values()]


def get_saved_week(saved_week_id: str) -> SavedWeek:
    saved_weeks = _read_saved_weeks()
    saved_week = saved_weeks.get(saved_week_id)
    if not saved_week:
        raise HTTPException(status_code=404, detail="Saved week not found")
    return SavedWeek.model_validate(saved_week)
