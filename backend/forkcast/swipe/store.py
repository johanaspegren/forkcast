from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException

from .models import Member, MemberVerdict, SwipeRound, Verdict

DATA_DIR = Path(__file__).resolve().parents[3] / ".forkcast-data"
SWIPE_DIR = DATA_DIR / "swipe"
MEMBERS_DIR = SWIPE_DIR / "members"
ROUNDS_DIR = SWIPE_DIR / "rounds"

DEFAULT_MEMBERS = (
    ("mamma", "Mamma", "👩"),
    ("pappa", "Pappa", "👨"),
    ("amanda", "Amanda", "🧒"),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    for directory in (MEMBERS_DIR, ROUNDS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def _write_atomic(path: Path, payload: dict) -> None:
    """Write through a temp file so a concurrent reader never sees a half file."""
    ensure_dirs()
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def _read(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, ValueError):
        return None


# --- members -------------------------------------------------------------

def member_path(member_id: str) -> Path:
    return MEMBERS_DIR / f"{member_id}.json"


def new_member_id() -> str:
    return uuid.uuid4().hex[:12]


def save_member(member: Member) -> Member:
    member.updated_at = now_iso()
    if not member.created_at:
        member.created_at = member.updated_at
    _write_atomic(member_path(member.member_id), member.model_dump(mode="json"))
    return member


def get_member(member_id: str) -> Member:
    data = _read(member_path(member_id))
    if not data:
        raise HTTPException(status_code=404, detail="Okänd familjemedlem")
    return Member.model_validate(data)


def list_members() -> list[Member]:
    members = _load_members()
    if members:
        return members

    base = datetime.now(timezone.utc)
    for index, (member_id, name, avatar) in enumerate(DEFAULT_MEMBERS):
        created_at = (base + timedelta(microseconds=index)).isoformat()
        save_member(Member(member_id=member_id, name=name, avatar=avatar, created_at=created_at))
    return _load_members()


def _load_members() -> list[Member]:
    if not MEMBERS_DIR.exists():
        return []
    members = []
    for path in sorted(MEMBERS_DIR.glob("*.json")):
        data = _read(path)
        if data:
            members.append(Member.model_validate(data))
    members.sort(key=lambda m: (m.created_at or "", m.name))
    return members


def find_by_name(name: str) -> Member | None:
    """Match a member by name, case- and whitespace-insensitively.

    Used only when a device supplies no member id - the "same person, new
    phone" case. Without it, typing your own name on a second phone creates a
    twin and splits your swiping history.
    """
    wanted = name.strip().lower()
    return next((m for m in list_members() if m.name.strip().lower() == wanted), None)


def record_verdicts(member_id: str, verdicts: dict[str, Verdict]) -> Member:
    """Idempotent: re-sending the same swipes just refreshes their timestamps."""
    member = get_member(member_id)
    stamp = now_iso()
    for meal_id, verdict in verdicts.items():
        member.verdicts[meal_id] = MemberVerdict(verdict=verdict, updated_at=stamp)
    return save_member(member)


# --- rounds --------------------------------------------------------------

def round_path(week_id: str) -> Path:
    return ROUNDS_DIR / f"{week_id}.json"


def save_round(swipe_round: SwipeRound) -> SwipeRound:
    swipe_round.updated_at = now_iso()
    _write_atomic(round_path(swipe_round.week_id), swipe_round.model_dump(mode="json"))
    return swipe_round


def get_round(week_id: str) -> SwipeRound | None:
    data = _read(round_path(week_id))
    return SwipeRound.model_validate(data) if data else None


def ensure_round(week_id: str, year: int, week: int) -> SwipeRound:
    existing = get_round(week_id)
    if existing:
        return existing
    return save_round(SwipeRound(week_id=week_id, year=year, week=week))


def touch_round(week_id: str, year: int, week: int, member_id: str) -> SwipeRound:
    """A swipe landed: note the participant and invalidate any live proposal."""
    swipe_round = ensure_round(week_id, year, week)
    if member_id not in swipe_round.participants:
        swipe_round.participants.append(member_id)
    swipe_round.verdicts_revision += 1
    return save_round(swipe_round)
