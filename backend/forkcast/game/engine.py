from __future__ import annotations

import random
import string
import time
import uuid
from fastapi import HTTPException

from .models import (
    CardPlayRequest,
    CreateSessionRequest,
    GamePhase,
    GameMode,
    GeneralAssemblyRequest,
    JoinRequest,
    LockDayRequest,
    Meal,
    MealSelectionRequest,
    PassTurnRequest,
    PlacementRequest,
    Player,
    PlayerSession,
    Proposal,
    RealtimeFreezeRequest,
    RealtimeHeartRequest,
    RealtimeOverrideRequest,
    RealtimeOverrideWindow,
    RealtimeStats,
    RuleStatus,
    Session,
    UnlockDayRequest,
    VoteRequest,
    WeekEntry,
)

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
AVATARS = ["🥘", "🍕", "🌮", "🍜", "🥗", "🍛", "🐟", "🍳"]
ACTION_DECK = ["ILL_COOK", "ILL_CLEAN"]
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

    def create_session(self, request: CreateSessionRequest | None = None) -> Session:
        session_id = uuid.uuid4().hex[:8]
        max_selected_meals = request.max_selected_meals if request else 3
        max_selected_meals = max(1, min(5, max_selected_meals))
        session = Session(
            id=session_id,
            join_code=f"FORK-{self._join_suffix()}",
            phase=GamePhase.LOBBY,
            game_mode=request.game_mode if request else GameMode.CLASSIC_DRAFT,
            days=DAYS.copy(),
            week={day: None for day in DAYS},
            max_selected_meals=max_selected_meals,
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
            self._begin_negotiation_phase(session)
            return self._refresh_rules(session)

        if session.phase == GamePhase.REALTIME_RUSH:
            for player_id in simulated_ids:
                now = time.time()
                active = [
                    proposal
                    for proposal in session.proposals.values()
                    if proposal.status == "ACTIVE" and session.realtime_freeze_until.get(proposal.id, 0) <= now
                ]
                if active:
                    proposal = random.choice(active)
                    if random.random() < 0.12 and player_id not in session.realtime_freezes_used:
                        self.realtime_freeze(session.id, RealtimeFreezeRequest(player_id=player_id, proposal_id=proposal.id))
                    else:
                        self.realtime_heart(session.id, RealtimeHeartRequest(player_id=player_id, proposal_id=proposal.id))
            return self.realtime_tick(session_id)

        if session.phase == GamePhase.NEGOTIATION:
            current_player_id = self._current_player_id(session)
            if current_player_id and session.players[current_player_id].simulated:
                self._simulate_turn(session, current_player_id)
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
            meal_cards=list(MEALS),
            action_cards=["ILL_COOK", "ILL_CLEAN"],
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
        self._begin_negotiation_phase(session)
        return self._refresh_rules(session)

    def realtime_heart(self, session_id: str, request: RealtimeHeartRequest) -> Session:
        session = self._require_phase(session_id, GamePhase.REALTIME_RUSH)
        self._player_state(session, request.player_id)
        self._realtime_tick(session)
        if session.phase != GamePhase.REALTIME_RUSH:
            return self._refresh_rules(session)
        proposal = self._active_proposal(session, request.proposal_id)
        now = time.time()
        if session.realtime_started_at and now < session.realtime_started_at + 3:
            raise HTTPException(status_code=409, detail="Rush has not started yet")
        if session.realtime_freeze_until.get(proposal.id, 0) > now:
            raise HTTPException(status_code=409, detail="That meal is frozen for a few seconds")

        proposal.voting_points += 1
        if request.player_id not in proposal.supporters:
            proposal.supporters.append(request.player_id)
        proposal.support_points[request.player_id] = proposal.support_points.get(request.player_id, 0) + 1
        stats = session.realtime_stats
        stats.hearts_by_player[request.player_id] = stats.hearts_by_player.get(request.player_id, 0) + 1
        stats.hearts_by_proposal[proposal.id] = stats.hearts_by_proposal.get(proposal.id, 0) + 1
        if request.player_id in proposal.owners:
            stats.own_hearts_by_player[request.player_id] = stats.own_hearts_by_player.get(request.player_id, 0) + 1

        player_name = session.players[request.player_id].name
        owner_name = session.players[proposal.owners[0]].name if proposal.owners else "the table"
        day = proposal.day.capitalize()
        meal_name = MEALS[proposal.meal_id].name
        lines = [
            f"{player_name} LOVES {owner_name}'s {meal_name} on {day}!!!",
            f"{day} is looking like {meal_name}, folks!!!",
            f"{player_name} just lovebombed {meal_name}.",
        ]
        self._log(session, random.choice(lines))
        self._check_realtime_rules(session, now)
        return self._refresh_rules(session)

    def realtime_freeze(self, session_id: str, request: RealtimeFreezeRequest) -> Session:
        session = self._require_phase(session_id, GamePhase.REALTIME_RUSH)
        self._player_state(session, request.player_id)
        self._realtime_tick(session)
        if session.phase != GamePhase.REALTIME_RUSH:
            return self._refresh_rules(session)
        proposal = self._active_proposal(session, request.proposal_id)
        now = time.time()
        if session.realtime_started_at and now < session.realtime_started_at + 3:
            raise HTTPException(status_code=409, detail="Rush has not started yet")
        if request.player_id in session.realtime_freezes_used:
            raise HTTPException(status_code=409, detail="Freeze has already been used")
        until = now + 5
        session.realtime_freezes_used.append(request.player_id)
        session.realtime_freeze_until[proposal.id] = until
        stats = session.realtime_stats
        stats.freezes_by_player[request.player_id] = stats.freezes_by_player.get(request.player_id, 0) + 1
        self._log(session, f"{session.players[request.player_id].name} froze {MEALS[proposal.meal_id].name} for 5 seconds.")
        return self._refresh_rules(session)

    def realtime_override(self, session_id: str, request: RealtimeOverrideRequest) -> Session:
        session = self._require_phase(session_id, GamePhase.REALTIME_RUSH)
        self._player_state(session, request.player_id)
        self._realtime_tick(session)
        window = session.realtime_override_window
        if not window or window.id != request.window_id or window.status != "OPEN":
            raise HTTPException(status_code=409, detail="No active override vote")
        window.votes[request.player_id] = True
        if sum(1 for agreed in window.votes.values() if agreed) >= window.threshold:
            window.status = "PASSED"
            if window.rule_id not in session.rule_overrides:
                session.rule_overrides.append(window.rule_id)
            self._log(session, f"Override passed: {window.message}")
        return self._refresh_rules(session)

    def realtime_tick(self, session_id: str) -> Session:
        session = self._require_phase(session_id, GamePhase.REALTIME_RUSH)
        self._realtime_tick(session)
        return self._refresh_rules(session)

    def vote(self, session_id: str, request: VoteRequest) -> Session:
        session = self._require_phase(session_id, GamePhase.NEGOTIATION)
        self._require_turn(session, request.player_id)
        player_state = self._player_state(session, request.player_id)
        proposal = session.proposals.get(request.proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        if request.kind == "support":
            current_downvote = proposal.downvote_points.get(request.player_id, 0)
            if current_downvote > 0:
                proposal.downvote_points[request.player_id] = current_downvote - 1
                if proposal.downvote_points[request.player_id] <= 0:
                    proposal.downvote_points.pop(request.player_id)
                proposal.downvotes = max(0, proposal.downvotes - 1)
                proposal.voting_points += 1
                player_state.voting_points_remaining += 3
                self._log(session, f"{session.players[request.player_id].name} withdrew a downvote from {MEALS[proposal.meal_id].name}.")
                return self._refresh_rules(session)
            cost = 1
            delta = 1
            if request.player_id in proposal.owners:
                cost = 2
        elif request.kind == "withdraw":
            current_support = proposal.support_points.get(request.player_id, 0)
            if current_support > 0:
                refund = 2 if request.player_id in proposal.owners else 1
                proposal.support_points[request.player_id] = current_support - 1
                if proposal.support_points[request.player_id] <= 0:
                    proposal.support_points.pop(request.player_id)
                proposal.voting_points -= 1
                player_state.voting_points_remaining += refund
                if proposal.support_points.get(request.player_id, 0) == 0 and request.player_id in proposal.supporters:
                    proposal.supporters.remove(request.player_id)
                self._log(session, f"{session.players[request.player_id].name} withdrew support from {MEALS[proposal.meal_id].name}.")
                return self._refresh_rules(session)
            request.kind = "downvote"
            cost = 3
            delta = -1
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
        if request.kind == "support":
            proposal.support_points[request.player_id] = proposal.support_points.get(request.player_id, 0) + 1
        if request.kind == "downvote":
            proposal.downvotes += 1
            proposal.downvote_points[request.player_id] = proposal.downvote_points.get(request.player_id, 0) + 1
        self._log(session, f"{session.players[request.player_id].name} {'supported' if request.kind == 'support' else 'downvoted'} {MEALS[proposal.meal_id].name}.")
        return self._refresh_rules(session)

    def play_card(self, session_id: str, request: CardPlayRequest) -> Session:
        session = self._require_phase(session_id, GamePhase.NEGOTIATION, GamePhase.REALTIME_RUSH)
        if session.phase == GamePhase.NEGOTIATION:
            self._require_turn(session, request.player_id)
        if session.phase == GamePhase.REALTIME_RUSH:
            self._realtime_tick(session)
            if session.phase != GamePhase.REALTIME_RUSH:
                return self._refresh_rules(session)
            if session.realtime_started_at and time.time() < session.realtime_started_at + 3:
                raise HTTPException(status_code=409, detail="Rush has not started yet")
        player_state = self._player_state(session, request.player_id)
        if request.card not in player_state.action_cards:
            raise HTTPException(status_code=422, detail="Card is not in this player's hand")

        if request.card == "ILL_COOK":
            proposal = self._active_proposal(session, request.proposal_id)
            if proposal.id in player_state.cook_commitments:
                player_state.cook_commitments.remove(proposal.id)
                if request.player_id in proposal.chef_volunteers:
                    proposal.chef_volunteers.remove(request.player_id)
                self._log(session, f"{session.players[request.player_id].name} is no longer cooking {MEALS[proposal.meal_id].name}.")
                return self._refresh_rules(session)
            if request.player_id not in proposal.chef_volunteers:
                proposal.chef_volunteers.append(request.player_id)
            player_state.cook_commitments.append(proposal.id)
            self._mark_card_played(player_state, f"ILL_COOK:{proposal.id}")
            self._log(session, f"{session.players[request.player_id].name} will cook {MEALS[proposal.meal_id].name}.")
            return self._refresh_rules(session)

        if request.card == "ILL_CLEAN":
            proposal = self._active_proposal(session, request.proposal_id)
            if proposal.id in player_state.clean_commitments:
                player_state.clean_commitments.remove(proposal.id)
                if request.player_id in proposal.cleanup_volunteers:
                    proposal.cleanup_volunteers.remove(request.player_id)
                self._log(session, f"{session.players[request.player_id].name} is no longer cleaning after {MEALS[proposal.meal_id].name}.")
                return self._refresh_rules(session)
            if request.player_id not in proposal.cleanup_volunteers:
                proposal.cleanup_volunteers.append(request.player_id)
            player_state.clean_commitments.append(proposal.id)
            self._mark_card_played(player_state, f"ILL_CLEAN:{proposal.id}")
            self._log(session, f"{session.players[request.player_id].name} will clean after {MEALS[proposal.meal_id].name}.")
            return self._refresh_rules(session)

        raise HTTPException(status_code=422, detail="Unsupported card")

    def pass_turn(self, session_id: str, request: PassTurnRequest) -> Session:
        session = self._require_phase(session_id, GamePhase.NEGOTIATION)
        self._require_turn(session, request.player_id)
        self._log(session, f"{session.players[request.player_id].name} passed.")
        self._advance_turn(session)
        return self._refresh_rules(session)

    def lock_day(self, session_id: str, request: LockDayRequest) -> Session:
        session = self._require_phase(session_id, GamePhase.NEGOTIATION, GamePhase.FINAL_VOTE)
        if session.phase == GamePhase.NEGOTIATION:
            if not request.player_id:
                raise HTTPException(status_code=422, detail="Player is required to lock during negotiation")
            self._require_turn(session, request.player_id)
        proposal = session.proposals.get(request.proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        if proposal.day != request.day:
            raise HTTPException(status_code=422, detail="Proposal is for a different day")
        self._require_lockable(session, proposal)
        session.week[request.day] = WeekEntry(
            meal_id=proposal.meal_id,
            chef=proposal.chef_volunteers[:1],
            cleanup=proposal.cleanup_volunteers[:1],
            rule_exceptions=request.rule_exceptions,
        )
        proposal.status = "LOCKED"
        actor = session.players[request.player_id].name if request.player_id else "The table"
        self._log(session, f"{actor} locked {MEALS[proposal.meal_id].name} for {request.day}.")
        if all(session.week.values()):
            session.phase = GamePhase.FINAL_VOTE
        return self._refresh_rules(session)

    def call_general_assembly(self, session_id: str, request: GeneralAssemblyRequest) -> Session:
        session = self._require_phase(session_id, GamePhase.NEGOTIATION, GamePhase.FINAL_VOTE)
        rule = next((rule for rule in session.rules if rule.id == request.rule_id), None)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        if rule.level != "HOUSE":
            raise HTTPException(status_code=422, detail="Only house rules can be overridden")
        if request.points <= 0:
            raise HTTPException(status_code=422, detail="Points must be positive")
        player_state = self._player_state(session, request.player_id)
        if player_state.voting_points_remaining < request.points:
            raise HTTPException(status_code=409, detail="Not enough Voting Points")

        player_state.voting_points_remaining -= request.points
        contributions = session.general_assembly.setdefault(request.rule_id, {})
        contributions[request.player_id] = contributions.get(request.player_id, 0) + request.points
        total = sum(contributions.values())
        player_name = session.players[request.player_id].name
        self._log(session, f"{player_name} committed {request.points} Voting Points to a General Assembly on '{rule.label}'.")

        if total >= session.general_assembly_threshold and request.rule_id not in session.rule_overrides:
            session.rule_overrides.append(request.rule_id)
            self._log(session, f"General Assembly passed: '{rule.label}' is overruled ({total} points).")
        return self._refresh_rules(session)

    def unlock_day(self, session_id: str, request: UnlockDayRequest) -> Session:
        session = self._require_phase(session_id, GamePhase.NEGOTIATION, GamePhase.FINAL_VOTE)
        entry = session.week.get(request.day)
        if not entry:
            raise HTTPException(status_code=409, detail="Day is not locked")
        proposal = next(
            (
                proposal
                for proposal in session.proposals.values()
                if proposal.day == request.day and proposal.meal_id == entry.meal_id and proposal.status == "LOCKED"
            ),
            None,
        )
        if proposal:
            proposal.status = "ACTIVE"
        session.week[request.day] = None
        if session.phase == GamePhase.FINAL_VOTE:
            session.phase = GamePhase.NEGOTIATION
        player_name = session.players[request.player_id].name
        self._log(session, f"{player_name} unlocked {MEALS[entry.meal_id].name} for {request.day}.")
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
                proposal.support_points[player_id] = proposal.support_points.get(player_id, 0) + points
                return
        proposal_id = f"proposal_{len(session.proposals) + 1}"
        session.proposals[proposal_id] = Proposal(
            id=proposal_id,
            meal_id=meal_id,
            day=day,
            owners=[player_id],
            voting_points=points,
            supporters=[player_id],
            support_points={player_id: points} if points > 0 else {},
        )

    def _refresh_rules(self, session: Session) -> Session:
        locked_meals = [entry.meal_id for entry in session.week.values() if entry]
        fish_count = sum(1 for meal_id in locked_meals if MEALS[meal_id].fish)
        minced_count = sum(1 for meal_id in locked_meals if MEALS[meal_id].minced_meat)
        rules = [
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
        for rule in rules:
            if not rule.satisfied and rule.id in session.rule_overrides:
                rule.satisfied = True
                rule.detail = f"{rule.detail} — overruled by General Assembly"
        session.rules = rules
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
                if kind == "support":
                    proposal.support_points[player_id] = proposal.support_points.get(player_id, 0) + 1
                if kind == "downvote":
                    proposal.downvotes += 1
                    proposal.downvote_points[player_id] = proposal.downvote_points.get(player_id, 0) + 1
                self._log(session, f"{session.players[player_id].name} {'supported' if kind == 'support' else 'downvoted'} {MEALS[proposal.meal_id].name}.")

    def _simulate_turn(self, session: Session, player_id: str) -> None:
        player_state = session.player_state[player_id]
        playable_cards = []
        playable_cards = [card for card in player_state.action_cards]
        if playable_cards and random.random() < 0.35:
            self._simulate_card(session, player_id, random.choice(playable_cards))
            self._advance_turn(session)
            return

        self._simulate_votes(session, [player_id])
        if random.random() < 0.75:
            self._lock_one_day_from_leader(session, player_id)
        self._advance_turn(session)

    def _simulate_card(self, session: Session, player_id: str, card: str) -> None:
        active = [proposal for proposal in session.proposals.values() if proposal.status == "ACTIVE"]
        if card == "ILL_COOK" and active:
            options = [proposal for proposal in active if proposal.id not in session.player_state[player_id].cook_commitments]
            if options:
                self.play_card(session.id, CardPlayRequest(player_id=player_id, card=card, proposal_id=random.choice(options).id))
            return
        if card == "ILL_CLEAN" and active:
            options = [proposal for proposal in active if proposal.id not in session.player_state[player_id].clean_commitments]
            if options:
                self.play_card(session.id, CardPlayRequest(player_id=player_id, card=card, proposal_id=random.choice(options).id))
            return

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
            fallback_player_id = random.choice(winner.owners)
            self._ensure_chore_commitments(session, winner, fallback_player_id)
            session.week[day] = WeekEntry(
                meal_id=winner.meal_id,
                chef=winner.chef_volunteers[:1],
                cleanup=winner.cleanup_volunteers[:1],
            )
            winner.status = "LOCKED"
            fish_locked = fish_locked or MEALS[winner.meal_id].fish
            minced_count += 1 if MEALS[winner.meal_id].minced_meat else 0

    def _lock_one_day_from_leader(self, session: Session, player_id: str) -> None:
        unlocked_days = [day for day in session.days if session.week[day] is None]
        if not unlocked_days:
            return
        locked_meal_ids = [entry.meal_id for entry in session.week.values() if entry]
        fish_locked = any(MEALS[meal_id].fish for meal_id in locked_meal_ids)
        minced_count = sum(1 for meal_id in locked_meal_ids if MEALS[meal_id].minced_meat)
        day = unlocked_days[-1] if not fish_locked and len(unlocked_days) == 1 else random.choice(unlocked_days)
        day_proposals = [
            proposal for proposal in session.proposals.values() if proposal.day == day and proposal.status == "ACTIVE"
        ]
        if not day_proposals:
            fallback_meal_id = "salmon" if not fish_locked and len(unlocked_days) == 1 else "pasta"
            self._upsert_proposal(session, player_id, fallback_meal_id, day, 0)
            day_proposals = [
                proposal for proposal in session.proposals.values() if proposal.day == day and proposal.status == "ACTIVE"
            ]
        eligible = day_proposals
        if minced_count >= 1:
            non_minced = [proposal for proposal in eligible if not MEALS[proposal.meal_id].minced_meat]
            if not non_minced:
                self._upsert_proposal(session, player_id, "pasta", day, 0)
                non_minced = [
                    proposal
                    for proposal in session.proposals.values()
                    if proposal.day == day and proposal.status == "ACTIVE" and not MEALS[proposal.meal_id].minced_meat
                ]
            if non_minced:
                eligible = non_minced
        if not fish_locked and len(unlocked_days) == 1:
            fish_options = [proposal for proposal in day_proposals if MEALS[proposal.meal_id].fish]
            if not fish_options:
                self._upsert_proposal(session, player_id, "salmon", day, 0)
                fish_options = [
                    proposal
                    for proposal in session.proposals.values()
                    if proposal.day == day and proposal.status == "ACTIVE" and MEALS[proposal.meal_id].fish
                ]
            if fish_options:
                eligible = fish_options
        winner = max(eligible, key=lambda proposal: (proposal.voting_points, len(proposal.supporters)))
        self._ensure_chore_commitments(session, winner, player_id)
        session.week[day] = WeekEntry(
            meal_id=winner.meal_id,
            chef=winner.chef_volunteers[:1],
            cleanup=winner.cleanup_volunteers[:1],
        )
        winner.status = "LOCKED"
        self._log(session, f"{session.players[player_id].name} locked {MEALS[winner.meal_id].name} for {day}.")

    def _ensure_chore_commitments(self, session: Session, proposal: Proposal, player_id: str) -> None:
        if not proposal.chef_volunteers:
            proposal.chef_volunteers.append(player_id)
            self._log(session, f"{session.players[player_id].name} volunteered to cook {MEALS[proposal.meal_id].name}.")
        if not proposal.cleanup_volunteers:
            proposal.cleanup_volunteers.append(player_id)
            self._log(session, f"{session.players[player_id].name} volunteered to clean after {MEALS[proposal.meal_id].name}.")

    def _begin_negotiation_phase(self, session: Session) -> None:
        if session.game_mode == GameMode.REALTIME_RUSH:
            now = time.time()
            session.phase = GamePhase.REALTIME_RUSH
            session.realtime_started_at = now
            session.realtime_ends_at = now + 63
            session.realtime_freeze_until = {}
            session.realtime_freezes_used = []
            session.realtime_override_window = None
            session.realtime_stats = RealtimeStats()
            self._log(session, "Realtime Rush started. Lovebomb your favorites for 60 seconds!")
            return
        session.phase = GamePhase.NEGOTIATION
        self._start_turns(session)

    def _realtime_tick(self, session: Session) -> None:
        if session.phase != GamePhase.REALTIME_RUSH:
            return
        now = time.time()
        session.realtime_freeze_until = {
            proposal_id: until for proposal_id, until in session.realtime_freeze_until.items() if until > now
        }
        window = session.realtime_override_window
        if window and window.status == "OPEN" and now >= window.closes_at:
            window.status = "FAILED"
            for proposal_id in window.proposal_ids:
                session.realtime_freeze_until[proposal_id] = now + 5
            self._log(session, "Override missed. The rule-breaking meal is frozen for 5 seconds.")
        if session.realtime_ends_at and now >= session.realtime_ends_at:
            self._finish_realtime(session)

    def _check_realtime_rules(self, session: Session, now: float) -> None:
        if "max_one_minced" in session.rule_overrides:
            return
        window = session.realtime_override_window
        if window and window.status == "OPEN" and window.closes_at > now:
            return
        leaders = self._realtime_leaders(session)
        minced_leaders = [
            proposal for proposal in leaders.values() if proposal and MEALS[proposal.meal_id].minced_meat
        ]
        if len(minced_leaders) <= 1:
            return
        threshold = max(2, (len(session.players) // 2) + 1)
        session.realtime_override_window = RealtimeOverrideWindow(
            id=uuid.uuid4().hex[:8],
            rule_id="max_one_minced",
            proposal_ids=[proposal.id for proposal in minced_leaders],
            message="Can not have two minced meat dinners. Override?",
            opened_at=now,
            closes_at=now + 3,
            threshold=threshold,
        )
        self._log(session, "WARNING: Can not have two minced meat dinners. Override?")

    def _finish_realtime(self, session: Session) -> None:
        leaders = self._realtime_leaders(session)
        selected: dict[str, Proposal] = {day: proposal for day, proposal in leaders.items() if proposal}
        if "max_one_minced" not in session.rule_overrides:
            minced_days = [day for day, proposal in selected.items() if MEALS[proposal.meal_id].minced_meat]
            for day in minced_days[1:]:
                replacement = self._best_day_proposal(
                    session,
                    day,
                    lambda proposal: not MEALS[proposal.meal_id].minced_meat,
                )
                if replacement:
                    selected[day] = replacement
        if "one_fish" not in session.rule_overrides and not any(MEALS[proposal.meal_id].fish for proposal in selected.values()):
            best_fish = self._best_proposal(session, lambda proposal: MEALS[proposal.meal_id].fish)
            if best_fish:
                selected[best_fish.day] = best_fish

        player_ids = list(session.players)
        for index, day in enumerate(session.days):
            proposal = selected.get(day)
            if not proposal:
                fallback_owner = player_ids[index % len(player_ids)]
                self._upsert_proposal(session, fallback_owner, "salmon" if index == len(session.days) - 1 else "pasta", day, 0)
                proposal = self._realtime_leaders(session).get(day)
            if not proposal:
                continue
            fallback_player_id = proposal.owners[0] if proposal.owners else player_ids[index % len(player_ids)]
            self._ensure_chore_commitments(session, proposal, fallback_player_id)
            session.week[day] = WeekEntry(
                meal_id=proposal.meal_id,
                chef=proposal.chef_volunteers[:1],
                cleanup=proposal.cleanup_volunteers[:1],
                rule_exceptions=[rule_id for rule_id in session.rule_overrides if rule_id in {"one_fish", "max_one_minced"}],
            )
            proposal.status = "LOCKED"

        session.realtime_stats.awards = self._realtime_awards(session)
        session.phase = GamePhase.COMPLETE
        self._log(session, "Time! The Realtime Rush Forkcast is locked.")

    def _realtime_leaders(self, session: Session) -> dict[str, Proposal | None]:
        return {
            day: self._best_day_proposal(session, day, lambda proposal: proposal.status == "ACTIVE")
            for day in session.days
        }

    def _best_day_proposal(self, session: Session, day: str, predicate) -> Proposal | None:
        proposals = [
            proposal
            for proposal in session.proposals.values()
            if proposal.day == day and proposal.status == "ACTIVE" and predicate(proposal)
        ]
        if not proposals:
            return None
        return max(proposals, key=lambda proposal: (proposal.voting_points, len(proposal.supporters)))

    def _best_proposal(self, session: Session, predicate) -> Proposal | None:
        proposals = [proposal for proposal in session.proposals.values() if proposal.status == "ACTIVE" and predicate(proposal)]
        if not proposals:
            return None
        return max(proposals, key=lambda proposal: (proposal.voting_points, len(proposal.supporters)))

    def _realtime_awards(self, session: Session) -> list[str]:
        stats = session.realtime_stats
        awards: list[str] = []
        if stats.hearts_by_proposal:
            proposal_id = max(stats.hearts_by_proposal, key=lambda key: stats.hearts_by_proposal[key])
            proposal = session.proposals.get(proposal_id)
            if proposal:
                owner = session.players[proposal.owners[0]].name if proposal.owners else "the table"
                awards.append(f"Family {MEALS[proposal.meal_id].name.lower()} fan: {owner}!")
        if stats.hearts_by_player:
            player_id = max(stats.hearts_by_player, key=lambda key: stats.hearts_by_player[key])
            awards.append(f"Most hearts per second: {session.players[player_id].name}")
        if stats.own_hearts_by_player:
            player_id = max(stats.own_hearts_by_player, key=lambda key: stats.own_hearts_by_player[key])
            awards.append(f"Most happy with their own selection: {session.players[player_id].name}")
        chef_counts: dict[str, int] = {}
        for entry in session.week.values():
            if entry:
                for player_id in entry.chef:
                    chef_counts[player_id] = chef_counts.get(player_id, 0) + 1
        if chef_counts:
            player_id = max(chef_counts, key=lambda key: chef_counts[key])
            awards.append(f"{session.players[player_id].name} is leading chef with {chef_counts[player_id]} meals!")
        if stats.freezes_by_player:
            player_id = max(stats.freezes_by_player, key=lambda key: stats.freezes_by_player[key])
            awards.append(f"Coolest freeze: {session.players[player_id].name}")
        return awards[:5]

    def _require_lockable(self, session: Session, proposal: Proposal) -> None:
        day_proposals = [
            candidate for candidate in session.proposals.values() if candidate.day == proposal.day and candidate.status == "ACTIVE"
        ]
        leader = max(day_proposals, key=lambda candidate: (candidate.voting_points, len(candidate.supporters)))
        if leader.id != proposal.id:
            raise HTTPException(status_code=409, detail="Only the leading proposal for the day can be locked")
        if not proposal.chef_volunteers or not proposal.cleanup_volunteers:
            raise HTTPException(status_code=409, detail="A proposal needs both chef and cleanup volunteers before locking")

    def _start_turns(self, session: Session) -> None:
        if not session.turn_order:
            session.turn_order = list(session.players)
            session.current_turn_index = 0
            self._log(session, "Negotiation order was set.")

    def _advance_turn(self, session: Session) -> None:
        if not session.turn_order:
            self._start_turns(session)
        if session.phase == GamePhase.NEGOTIATION and session.turn_order:
            session.current_turn_index = (session.current_turn_index + 1) % len(session.turn_order)

    def _current_player_id(self, session: Session) -> str | None:
        if not session.turn_order:
            return None
        return session.turn_order[session.current_turn_index % len(session.turn_order)]

    def _require_turn(self, session: Session, player_id: str) -> None:
        current_player_id = self._current_player_id(session)
        if current_player_id and current_player_id != player_id:
            raise HTTPException(status_code=409, detail=f"It is {session.players[current_player_id].name}'s turn")

    def _mark_card_played(self, player_state: PlayerSession, card: str) -> None:
        player_state.action_cards_played.append(card)

    def _active_proposal(self, session: Session, proposal_id: str | None) -> Proposal:
        if not proposal_id or proposal_id not in session.proposals:
            raise HTTPException(status_code=404, detail="Proposal not found")
        proposal = session.proposals[proposal_id]
        if proposal.status != "ACTIVE":
            raise HTTPException(status_code=409, detail="Proposal is not active")
        return proposal

    def _first_unlocked_day(self, session: Session) -> str | None:
        return next((day for day in session.days if session.week[day] is None), None)

    def _log(self, session: Session, message: str) -> None:
        session.turn_log = [message, *session.turn_log[:7]]

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
