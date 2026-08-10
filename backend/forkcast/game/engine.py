from __future__ import annotations

import random
import string
import uuid
from fastapi import HTTPException

from .models import (
    GamePhase,
    JoinRequest,
    LockDayRequest,
    Meal,
    MealSelectionRequest,
    PlacementRequest,
    Player,
    PlayerSession,
    Proposal,
    RuleStatus,
    Session,
    VoteRequest,
    WeekEntry,
)

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
AVATARS = ["🥘", "🍕", "🌮", "🍜", "🥗", "🍛", "🐟", "🍳"]
ACTION_DECK = ["ROULETTE", "SWAP", "ILL_COOK", "ILL_CLEAN", "COALITION", "WILD_CARD"]
SIMULATED_PLAYERS = [
    ("Anna", "🍕"),
    ("Elsa", "🌮"),
    ("Oscar", "🍜"),
    ("Mira", "🥗"),
    ("Noah", "🍛"),
]

MEALS: dict[str, Meal] = {
    "yakiniku": Meal(id="yakiniku", name="Yakiniku", emoji="🥩", tags=["beef", "japanese"], protein_type="beef"),
    "tacos": Meal(id="tacos", name="Tacos", emoji="🌮", tags=["minced", "family"], protein_type="beef", minced_meat=True),
    "salmon": Meal(id="salmon", name="Salmon", emoji="🐟", tags=["fish", "quick"], protein_type="fish", fish=True),
    "tomato_soup": Meal(id="tomato_soup", name="Tomato Soup", emoji="🥣", tags=["vegetarian"], protein_type="vegetarian"),
    "chicken_curry": Meal(id="chicken_curry", name="Chicken Curry", emoji="🍛", tags=["chicken", "spiced"], protein_type="chicken"),
    "pizza": Meal(id="pizza", name="Pizza", emoji="🍕", tags=["weekend", "family"], protein_type="mixed"),
    "pasta": Meal(id="pasta", name="Pasta", emoji="🍝", tags=["quick", "vegetarian"], protein_type="vegetarian"),
    "burgers": Meal(id="burgers", name="Burgers", emoji="🍔", tags=["minced"], protein_type="beef", minced_meat=True),
    "teriyaki_bowl": Meal(id="teriyaki_bowl", name="Teriyaki Bowl", emoji="🍚", tags=["japanese", "chicken"], protein_type="chicken"),
    "veggie_chili": Meal(id="veggie_chili", name="Veggie Chili", emoji="🥦", tags=["vegetarian", "beans"], protein_type="vegetarian"),
}

FAVOURITE_ROTATION = [
    ["yakiniku", "salmon", "tacos", "pasta"],
    ["tomato_soup", "chicken_curry", "salmon", "pizza"],
    ["pizza", "tacos", "pasta", "burgers"],
    ["teriyaki_bowl", "veggie_chili", "yakiniku", "tomato_soup"],
]


class GameEngine:
    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}

    def create_session(self) -> Session:
        session_id = uuid.uuid4().hex[:8]
        session = Session(
            id=session_id,
            join_code=f"FORK-{self._join_suffix()}",
            phase=GamePhase.LOBBY,
            days=DAYS.copy(),
            week={day: None for day in DAYS},
        )
        self.sessions[session_id] = session
        return self._refresh_rules(session)

    def get_session(self, session_id: str) -> Session:
        session = self.sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return self._refresh_rules(session)

    def all_meals(self) -> list[Meal]:
        return list(MEALS.values())

    def join(self, session_id: str, request: JoinRequest) -> Session:
        session = self.get_session(session_id)
        if session.phase != GamePhase.LOBBY:
            raise HTTPException(status_code=409, detail="Session already started")
        if len(session.players) >= session.max_players:
            raise HTTPException(status_code=409, detail="Session is full")
        return self._add_player(session, request.name, request.avatar, simulated=False)

    def add_simulated_players(self, session_id: str, count: int = 3) -> Session:
        session = self.get_session(session_id)
        if session.phase != GamePhase.LOBBY:
            raise HTTPException(status_code=409, detail="Simulated players can only join in the lobby")

        existing_names = {player.name for player in session.players.values()}
        for name, avatar in SIMULATED_PLAYERS:
            if len(session.players) >= session.max_players or count <= 0:
                break
            if name in existing_names:
                continue
            self._add_player(session, name, avatar, simulated=True)
            count -= 1
        return self._refresh_rules(session)

    def simulate_next(self, session_id: str) -> Session:
        session = self.get_session(session_id)
        simulated_ids = [player.id for player in session.players.values() if player.simulated]
        if not simulated_ids:
            raise HTTPException(status_code=409, detail="No simulated players in this session")

        if session.phase == GamePhase.MEAL_SELECTION:
            for player_id in simulated_ids:
                state = session.player_state[player_id]
                if not state.selected_meals:
                    state.selected_meals = random.sample(state.meal_cards, session.max_selected_meals)
            if all(state.selected_meals for state in session.player_state.values()):
                session.phase = GamePhase.SECRET_PLACEMENT
            return self._refresh_rules(session)

        if session.phase == GamePhase.SECRET_PLACEMENT:
            for player_id in simulated_ids:
                state = session.player_state[player_id]
                if state.placed:
                    continue
                placements = []
                total_points = random.randint(2, min(6, state.voting_points_remaining))
                point_budget = total_points
                days = random.sample(session.days, len(state.selected_meals))
                for index, meal_id in enumerate(state.selected_meals):
                    points = point_budget if index == len(state.selected_meals) - 1 else random.randint(0, point_budget)
                    point_budget -= points
                    placements.append((meal_id, days[index], points))
                for meal_id, day, points in placements:
                    self._upsert_proposal(session, player_id, meal_id, day, points)
                    state.voting_points_remaining -= points
                state.placed = True
            if all(state.placed for state in session.player_state.values()):
                session.phase = GamePhase.REVEAL
            return self._refresh_rules(session)

        if session.phase == GamePhase.REVEAL:
            session.phase = GamePhase.NEGOTIATION
            return self._refresh_rules(session)

        if session.phase == GamePhase.NEGOTIATION:
            self._simulate_votes(session, simulated_ids)
            self._lock_week_from_leaders(session)
            if all(session.week.values()):
                session.phase = GamePhase.FINAL_VOTE
            return self._refresh_rules(session)

        if session.phase == GamePhase.FINAL_VOTE:
            try:
                return self.complete(session_id)
            except HTTPException:
                return self._refresh_rules(session)

        return self._refresh_rules(session)

    def _add_player(self, session: Session, name: str, avatar: str | None, simulated: bool) -> Session:
        if len(session.players) >= session.max_players:
            raise HTTPException(status_code=409, detail="Session is full")

        player_id = self._slug(name)
        if player_id in session.players:
            player_id = f"{player_id}-{len(session.players) + 1}"

        rotation = FAVOURITE_ROTATION[len(session.players) % len(FAVOURITE_ROTATION)]
        player = Player(
            id=player_id,
            name=name.strip() or f"Player {len(session.players) + 1}",
            avatar=avatar or AVATARS[len(session.players) % len(AVATARS)],
            favourite_meals=rotation,
            simulated=simulated,
        )
        session.players[player_id] = player
        session.player_state[player_id] = PlayerSession(
            player_id=player_id,
            voting_points_remaining=session.starting_voting_points,
            meal_cards=rotation,
            action_cards=random.sample(ACTION_DECK, 3),
        )
        return self._refresh_rules(session)

    def start(self, session_id: str) -> Session:
        session = self.get_session(session_id)
        if not session.players:
            raise HTTPException(status_code=409, detail="At least one player must join")
        session.phase = GamePhase.MEAL_SELECTION
        return self._refresh_rules(session)

    def select_meals(self, session_id: str, request: MealSelectionRequest) -> Session:
        session = self._require_phase(session_id, GamePhase.MEAL_SELECTION)
        player_state = self._player_state(session, request.player_id)
        chosen = request.meal_ids[: session.max_selected_meals]
        if len(chosen) != session.max_selected_meals:
            raise HTTPException(status_code=422, detail=f"Choose {session.max_selected_meals} meals")
        if any(meal_id not in MEALS for meal_id in chosen):
            raise HTTPException(status_code=422, detail="Unknown meal")
        player_state.selected_meals = chosen

        if all(state.selected_meals for state in session.player_state.values()):
            session.phase = GamePhase.SECRET_PLACEMENT
        return self._refresh_rules(session)

    def place_meals(self, session_id: str, request: PlacementRequest) -> Session:
        session = self._require_phase(session_id, GamePhase.SECRET_PLACEMENT)
        player_state = self._player_state(session, request.player_id)
        if player_state.placed:
            raise HTTPException(status_code=409, detail="Player already placed meals")
        if sum(item.points for item in request.placements) > player_state.voting_points_remaining:
            raise HTTPException(status_code=422, detail="Not enough Voting Points")

        for item in request.placements:
            if item.meal_id not in player_state.selected_meals:
                raise HTTPException(status_code=422, detail="Place only selected meals")
            if item.day not in session.days:
                raise HTTPException(status_code=422, detail="Unknown day")
            if item.points < 0:
                raise HTTPException(status_code=422, detail="Voting Points must be positive")

        for item in request.placements:
            self._upsert_proposal(session, request.player_id, item.meal_id, item.day, item.points)
            player_state.voting_points_remaining -= item.points
        player_state.placed = True

        if all(state.placed for state in session.player_state.values()):
            session.phase = GamePhase.REVEAL
        return self._refresh_rules(session)

    def begin_negotiation(self, session_id: str) -> Session:
        session = self._require_phase(session_id, GamePhase.REVEAL)
        session.phase = GamePhase.NEGOTIATION
        return self._refresh_rules(session)

    def vote(self, session_id: str, request: VoteRequest) -> Session:
        session = self._require_phase(session_id, GamePhase.NEGOTIATION)
        player_state = self._player_state(session, request.player_id)
        proposal = session.proposals.get(request.proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        if request.kind == "support":
            cost = 1
            delta = 1
            if request.player_id in proposal.owners:
                cost = 2
        elif request.kind == "downvote":
            cost = 3
            delta = -1
        else:
            raise HTTPException(status_code=422, detail="Unknown vote kind")

        if player_state.voting_points_remaining < cost:
            raise HTTPException(status_code=409, detail="Not enough Voting Points")
        player_state.voting_points_remaining -= cost
        proposal.voting_points += delta
        if request.kind == "support" and request.player_id not in proposal.supporters:
            proposal.supporters.append(request.player_id)
        if request.kind == "downvote":
            proposal.downvotes += 1
        return self._refresh_rules(session)

    def lock_day(self, session_id: str, request: LockDayRequest) -> Session:
        session = self._require_phase(session_id, GamePhase.NEGOTIATION, GamePhase.FINAL_VOTE)
        proposal = session.proposals.get(request.proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        if proposal.day != request.day:
            raise HTTPException(status_code=422, detail="Proposal is for a different day")
        session.week[request.day] = WeekEntry(
            meal_id=proposal.meal_id,
            chef=request.chef,
            cleanup=request.cleanup,
            rule_exceptions=request.rule_exceptions,
        )
        proposal.status = "LOCKED"
        if all(session.week.values()):
            session.phase = GamePhase.FINAL_VOTE
        return self._refresh_rules(session)

    def complete(self, session_id: str) -> Session:
        session = self._require_phase(session_id, GamePhase.FINAL_VOTE)
        if not all(session.week.values()):
            raise HTTPException(status_code=409, detail="All days need meals")
        blocking = [rule for rule in self._refresh_rules(session).rules if rule.level == "HOUSE" and not rule.satisfied]
        if blocking:
            raise HTTPException(status_code=409, detail="House rules still need exceptions")
        session.phase = GamePhase.COMPLETE
        return self._refresh_rules(session)

    def _upsert_proposal(self, session: Session, player_id: str, meal_id: str, day: str, points: int) -> None:
        for proposal in session.proposals.values():
            if proposal.meal_id == meal_id and proposal.day == day and proposal.status == "ACTIVE":
                if player_id not in proposal.owners:
                    proposal.owners.append(player_id)
                if player_id not in proposal.supporters:
                    proposal.supporters.append(player_id)
                proposal.voting_points += points
                return
        proposal_id = f"proposal_{len(session.proposals) + 1}"
        session.proposals[proposal_id] = Proposal(
            id=proposal_id,
            meal_id=meal_id,
            day=day,
            owners=[player_id],
            voting_points=points,
            supporters=[player_id],
        )

    def _refresh_rules(self, session: Session) -> Session:
        locked_meals = [entry.meal_id for entry in session.week.values() if entry]
        fish_count = sum(1 for meal_id in locked_meals if MEALS[meal_id].fish)
        minced_count = sum(1 for meal_id in locked_meals if MEALS[meal_id].minced_meat)
        session.rules = [
            RuleStatus(
                id="one_fish",
                label="At least 1 fish meal per week",
                level="HOUSE",
                satisfied=fish_count >= 1 or not all(session.week.values()),
                detail=f"{fish_count} fish meals locked",
            ),
            RuleStatus(
                id="max_one_minced",
                label="Maximum 1 minced-meat meal per week",
                level="HOUSE",
                satisfied=minced_count <= 1,
                detail=f"{minced_count} minced-meat meals locked",
            ),
        ]
        return session

    def _simulate_votes(self, session: Session, simulated_ids: list[str]) -> None:
        active = [proposal for proposal in session.proposals.values() if proposal.status == "ACTIVE"]
        if not active:
            return

        for player_id in simulated_ids:
            state = session.player_state[player_id]
            for _ in range(random.randint(1, 2)):
                candidates = [proposal for proposal in active if session.week[proposal.day] is None]
                if not candidates:
                    return
                proposal = random.choice(candidates)
                kind = "support" if random.random() < 0.82 else "downvote"
                cost = 2 if kind == "support" and player_id in proposal.owners else 1 if kind == "support" else 3
                if state.voting_points_remaining < cost:
                    continue
                state.voting_points_remaining -= cost
                proposal.voting_points += 1 if kind == "support" else -1
                if kind == "support" and player_id not in proposal.supporters:
                    proposal.supporters.append(player_id)
                if kind == "downvote":
                    proposal.downvotes += 1

    def _lock_week_from_leaders(self, session: Session) -> None:
        locked_meal_ids = [entry.meal_id for entry in session.week.values() if entry]
        fish_locked = any(MEALS[meal_id].fish for meal_id in locked_meal_ids)
        minced_count = sum(1 for meal_id in locked_meal_ids if MEALS[meal_id].minced_meat)

        for day in session.days:
            if session.week[day] is not None:
                continue
            day_proposals = [
                proposal for proposal in session.proposals.values() if proposal.day == day and proposal.status == "ACTIVE"
            ]
            remaining_days = [future_day for future_day in session.days if session.week[future_day] is None]
            if not day_proposals:
                fallback_meal_id = "salmon" if not fish_locked and day == remaining_days[-1] else random.choice(list(MEALS))
                fallback_owner = random.choice(list(session.players))
                self._upsert_proposal(session, fallback_owner, fallback_meal_id, day, 0)
                day_proposals = [
                    proposal for proposal in session.proposals.values() if proposal.day == day and proposal.status == "ACTIVE"
                ]

            eligible = day_proposals
            if minced_count >= 1:
                non_minced = [proposal for proposal in eligible if not MEALS[proposal.meal_id].minced_meat]
                if not non_minced:
                    fallback_owner = random.choice(list(session.players))
                    self._upsert_proposal(session, fallback_owner, "pasta", day, 0)
                    non_minced = [
                        proposal
                        for proposal in session.proposals.values()
                        if proposal.day == day and proposal.status == "ACTIVE" and not MEALS[proposal.meal_id].minced_meat
                    ]
                eligible = non_minced

            if not fish_locked and day == remaining_days[-1]:
                fish_options = [proposal for proposal in day_proposals if MEALS[proposal.meal_id].fish]
                if not fish_options:
                    fallback_owner = random.choice(list(session.players))
                    self._upsert_proposal(session, fallback_owner, "salmon", day, 0)
                    fish_options = [
                        proposal
                        for proposal in session.proposals.values()
                        if proposal.day == day and proposal.status == "ACTIVE" and MEALS[proposal.meal_id].fish
                    ]
                if fish_options:
                    eligible = fish_options
            elif not fish_locked:
                fish_options = [proposal for proposal in eligible if MEALS[proposal.meal_id].fish]
                if fish_options and random.random() < 0.45:
                    eligible = fish_options

            winner = max(eligible, key=lambda proposal: (proposal.voting_points, len(proposal.supporters)))
            chef = random.choice(winner.owners)
            cleanup_options = [player_id for player_id in session.players if player_id != chef] or [chef]
            cleanup = random.choice(cleanup_options)
            session.week[day] = WeekEntry(meal_id=winner.meal_id, chef=[chef], cleanup=[cleanup])
            winner.status = "LOCKED"
            fish_locked = fish_locked or MEALS[winner.meal_id].fish
            minced_count += 1 if MEALS[winner.meal_id].minced_meat else 0

    def _require_phase(self, session_id: str, *phases: GamePhase) -> Session:
        session = self.get_session(session_id)
        if session.phase not in phases:
            expected = ", ".join(phases)
            raise HTTPException(status_code=409, detail=f"Expected phase {expected}, got {session.phase}")
        return session

    def _player_state(self, session: Session, player_id: str) -> PlayerSession:
        player_state = session.player_state.get(player_id)
        if not player_state:
            raise HTTPException(status_code=404, detail="Player not found")
        return player_state

    def _join_suffix(self) -> str:
        return "".join(random.choice(string.digits) for _ in range(2))

    def _slug(self, value: str) -> str:
        slug = "".join(char.lower() for char in value.strip() if char.isalnum())
        return slug or f"player-{uuid.uuid4().hex[:4]}"


engine = GameEngine()
