from enum import StrEnum
from pydantic import BaseModel, Field


class GamePhase(StrEnum):
    LOBBY = "LOBBY"
    MEAL_SELECTION = "MEAL_SELECTION"
    SECRET_PLACEMENT = "SECRET_PLACEMENT"
    REVEAL = "REVEAL"
    NEGOTIATION = "NEGOTIATION"
    REALTIME_RUSH = "REALTIME_RUSH"
    FINAL_VOTE = "FINAL_VOTE"
    COMPLETE = "COMPLETE"


class GameMode(StrEnum):
    CLASSIC_DRAFT = "CLASSIC_DRAFT"
    REALTIME_RUSH = "REALTIME_RUSH"


class Meal(BaseModel):
    id: str
    name: str
    emoji: str
    tags: list[str] = Field(default_factory=list)
    protein_type: str | None = None
    minced_meat: bool = False
    fish: bool = False


class Player(BaseModel):
    id: str
    name: str
    avatar: str
    favourite_meals: list[str]
    simulated: bool = False


class Proposal(BaseModel):
    id: str
    meal_id: str
    day: str
    owners: list[str]
    voting_points: int
    supporters: list[str]
    support_points: dict[str, int] = Field(default_factory=dict)
    downvote_points: dict[str, int] = Field(default_factory=dict)
    downvotes: int = 0
    status: str = "ACTIVE"
    chef_volunteers: list[str] = Field(default_factory=list)
    cleanup_volunteers: list[str] = Field(default_factory=list)


class PlayerSession(BaseModel):
    player_id: str
    voting_points_remaining: int
    meal_cards: list[str] = Field(default_factory=list)
    action_cards: list[str] = Field(default_factory=list)
    action_cards_played: list[str] = Field(default_factory=list)
    cook_commitments: list[str] = Field(default_factory=list)
    clean_commitments: list[str] = Field(default_factory=list)
    selected_meals: list[str] = Field(default_factory=list)
    placed: bool = False


class WeekEntry(BaseModel):
    meal_id: str
    chef: list[str] = Field(default_factory=list)
    cleanup: list[str] = Field(default_factory=list)
    rule_exceptions: list[str] = Field(default_factory=list)


class RuleStatus(BaseModel):
    id: str
    label: str
    level: str
    satisfied: bool
    detail: str


class RealtimeOverrideWindow(BaseModel):
    id: str
    rule_id: str
    proposal_ids: list[str] = Field(default_factory=list)
    message: str
    opened_at: float
    closes_at: float
    votes: dict[str, bool] = Field(default_factory=dict)
    threshold: int
    status: str = "OPEN"


class RealtimeStats(BaseModel):
    hearts_by_player: dict[str, int] = Field(default_factory=dict)
    hearts_by_proposal: dict[str, int] = Field(default_factory=dict)
    own_hearts_by_player: dict[str, int] = Field(default_factory=dict)
    freezes_by_player: dict[str, int] = Field(default_factory=dict)
    awards: list[str] = Field(default_factory=list)


class Session(BaseModel):
    id: str
    join_code: str
    phase: GamePhase
    game_mode: GameMode = GameMode.CLASSIC_DRAFT
    days: list[str]
    players: dict[str, Player] = Field(default_factory=dict)
    player_state: dict[str, PlayerSession] = Field(default_factory=dict)
    proposals: dict[str, Proposal] = Field(default_factory=dict)
    week: dict[str, WeekEntry | None]
    rules: list[RuleStatus] = Field(default_factory=list)
    turn_order: list[str] = Field(default_factory=list)
    current_turn_index: int = 0
    turn_log: list[str] = Field(default_factory=list)
    max_players: int = 4
    starting_voting_points: int = 10
    max_selected_meals: int = 3
    max_action_cards_played: int = 2
    rule_overrides: list[str] = Field(default_factory=list)
    general_assembly: dict[str, dict[str, int]] = Field(default_factory=dict)
    general_assembly_threshold: int = 4
    realtime_started_at: float | None = None
    realtime_ends_at: float | None = None
    realtime_freeze_until: dict[str, float] = Field(default_factory=dict)
    realtime_freezes_used: list[str] = Field(default_factory=list)
    realtime_override_window: RealtimeOverrideWindow | None = None
    realtime_stats: RealtimeStats = Field(default_factory=RealtimeStats)


class JoinRequest(BaseModel):
    name: str
    avatar: str | None = None


class CreateSessionRequest(BaseModel):
    max_selected_meals: int = 3
    game_mode: GameMode = GameMode.CLASSIC_DRAFT


class MealSelectionRequest(BaseModel):
    player_id: str
    meal_ids: list[str]


class PlacementItem(BaseModel):
    meal_id: str
    day: str
    points: int = 0


class PlacementRequest(BaseModel):
    player_id: str
    placements: list[PlacementItem]


class VoteRequest(BaseModel):
    player_id: str
    proposal_id: str
    kind: str


class LockDayRequest(BaseModel):
    player_id: str | None = None
    day: str
    proposal_id: str
    rule_exceptions: list[str] = Field(default_factory=list)


class PassTurnRequest(BaseModel):
    player_id: str


class GeneralAssemblyRequest(BaseModel):
    player_id: str
    rule_id: str
    points: int


class UnlockDayRequest(BaseModel):
    player_id: str
    day: str


class CardPlayRequest(BaseModel):
    player_id: str
    card: str
    proposal_id: str | None = None
    day: str | None = None
    target_day: str | None = None
    meal_id: str | None = None


class RealtimeHeartRequest(BaseModel):
    player_id: str
    proposal_id: str


class RealtimeFreezeRequest(BaseModel):
    player_id: str
    proposal_id: str


class RealtimeOverrideRequest(BaseModel):
    player_id: str
    window_id: str
