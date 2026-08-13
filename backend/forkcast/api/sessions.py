from fastapi import APIRouter, Query

from backend.forkcast.api.school_menu import fetch_matilda_school_menu
from backend.forkcast.api.websocket import manager
from backend.forkcast.game.engine import engine
from backend.forkcast.game.models import (
    CardPlayRequest,
    CreateSessionRequest,
    DeleteSessionRequest,
    GeneralAssemblyRequest,
    JoinRequest,
    LockDayRequest,
    MealSelectionRequest,
    PassTurnRequest,
    PlacementRequest,
    PlayerActionRequest,
    RealtimeFreezeRequest,
    RealtimeHeartRequest,
    RealtimeOverrideRequest,
    ReorderWeekRequest,
    Session,
    UnlockDayRequest,
    VoteRequest,
)
from backend.forkcast.game.saved_weeks import SaveWeekRequest, SavedWeek, get_saved_week, list_saved_weeks, save_week

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/meals")
def meals() -> list[dict]:
    return [meal.model_dump(mode="json") for meal in engine.all_meals()]


@router.get("/school-menu")
def school_menu(url: str = Query(...)) -> dict:
    return fetch_matilda_school_menu(url)


@router.get("/saved-weeks")
def saved_weeks() -> list[SavedWeek]:
    return list_saved_weeks()


@router.get("/saved-weeks/{saved_week_id}")
def saved_week(saved_week_id: str) -> SavedWeek:
    return get_saved_week(saved_week_id)


@router.post("/saved-weeks")
def save_completed_week(request: SaveWeekRequest) -> SavedWeek:
    session = engine.get_session(request.session_id)
    return save_week(session, request)


@router.post("/sessions")
async def create_session(request: CreateSessionRequest | None = None) -> Session:
    session = engine.create_session(request)
    await manager.broadcast(session)
    return session


@router.get("/sessions")
def active_sessions() -> list[Session]:
    return [session for session in engine.sessions.values() if session.phase != "COMPLETE"]


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> Session:
    return engine.get_session(session_id)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: DeleteSessionRequest | None = None) -> dict[str, str]:
    engine.delete_session(session_id, request)
    await manager.broadcast_deleted(session_id)
    return {"status": "deleted"}


@router.post("/sessions/{session_id}/join")
async def join_session(session_id: str, request: JoinRequest) -> Session:
    session = engine.join(session_id, request)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/simulate/add-players")
async def add_simulated_players(session_id: str) -> Session:
    session = engine.add_simulated_players(session_id, count=3)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/simulate/next")
async def simulate_next(session_id: str) -> Session:
    session = engine.simulate_next(session_id)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/start")
async def start_session(session_id: str) -> Session:
    session = engine.start(session_id)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/restart")
async def restart_session(session_id: str, request: PlayerActionRequest) -> Session:
    session = engine.restart_session(session_id, request)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/meal-selection")
async def select_meals(session_id: str, request: MealSelectionRequest) -> Session:
    session = engine.select_meals(session_id, request)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/placement")
async def place_meals(session_id: str, request: PlacementRequest) -> Session:
    session = engine.place_meals(session_id, request)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/reveal/continue")
async def begin_negotiation(session_id: str) -> Session:
    session = engine.begin_negotiation(session_id)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/realtime/heart")
async def realtime_heart(session_id: str, request: RealtimeHeartRequest) -> Session:
    session = engine.realtime_heart(session_id, request)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/realtime/freeze")
async def realtime_freeze(session_id: str, request: RealtimeFreezeRequest) -> Session:
    session = engine.realtime_freeze(session_id, request)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/realtime/override")
async def realtime_override(session_id: str, request: RealtimeOverrideRequest) -> Session:
    session = engine.realtime_override(session_id, request)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/realtime/tick")
async def realtime_tick(session_id: str) -> Session:
    session = engine.realtime_tick(session_id)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/vote")
async def vote(session_id: str, request: VoteRequest) -> Session:
    session = engine.vote(session_id, request)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/cards/play")
async def play_card(session_id: str, request: CardPlayRequest) -> Session:
    session = engine.play_card(session_id, request)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/pass-turn")
async def pass_turn(session_id: str, request: PassTurnRequest) -> Session:
    session = engine.pass_turn(session_id, request)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/lock-day")
async def lock_day(session_id: str, request: LockDayRequest) -> Session:
    session = engine.lock_day(session_id, request)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/general-assembly")
async def call_general_assembly(session_id: str, request: GeneralAssemblyRequest) -> Session:
    session = engine.call_general_assembly(session_id, request)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/unlock-day")
async def unlock_day(session_id: str, request: UnlockDayRequest) -> Session:
    session = engine.unlock_day(session_id, request)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/complete")
async def complete(session_id: str) -> Session:
    session = engine.complete(session_id)
    await manager.broadcast(session)
    return session


@router.post("/sessions/{session_id}/week/reorder")
async def reorder_week(session_id: str, request: ReorderWeekRequest) -> Session:
    session = engine.reorder_week(session_id, request)
    await manager.broadcast(session)
    return session
