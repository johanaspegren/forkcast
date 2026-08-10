from fastapi import APIRouter

from backend.forkcast.api.websocket import manager
from backend.forkcast.game.engine import engine
from backend.forkcast.game.models import (
    CardPlayRequest,
    CreateSessionRequest,
    JoinRequest,
    LockDayRequest,
    MealSelectionRequest,
    PassTurnRequest,
    PlacementRequest,
    Session,
    VoteRequest,
)

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/meals")
def meals() -> list[dict]:
    return [meal.model_dump(mode="json") for meal in engine.all_meals()]


@router.post("/sessions")
async def create_session(request: CreateSessionRequest | None = None) -> Session:
    session = engine.create_session(request)
    await manager.broadcast(session)
    return session


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> Session:
    return engine.get_session(session_id)


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


@router.post("/sessions/{session_id}/complete")
async def complete(session_id: str) -> Session:
    session = engine.complete(session_id)
    await manager.broadcast(session)
    return session
