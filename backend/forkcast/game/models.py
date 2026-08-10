from enum import StrEnum
from pydantic import BaseModel, Field


class GamePhase(StrEnum):
    LOBBY = "LOBBY"
    MEAL_SELECTION = "MEAL_SELECTION"
    SECRET_PLACEMENT = "SECRET_PLACEMENT"
    REVEAL = "REVEAL"
    NEGOTIATION = "NEGOTIATION"
    FINAL_VOTE = "FINAL_VOTE"
    COMPLETE = "COMPLETE"


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


class Session(BaseModel):
    id: str
    join_code: str
    phase: GamePhase
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


class JoinRequest(BaseModel):
    name: str
    avatar: str | None = None


class CreateSessionRequest(BaseModel):
    max_selected_meals: int = 3


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
