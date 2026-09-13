from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.forkcast.game.engine import DAYS, MEALS
from backend.forkcast.game.manual_weeks import ManualWeekDayPlan, SaveManualWeekRequest, save_manual_week
from backend.forkcast.ai.forkcast_ai import ForkcastAI, apply_ranking
from backend.forkcast.swipe import deck as deck_module
from backend.forkcast.swipe import reasons as reasons_module
from backend.forkcast.swipe import store
from backend.forkcast.swipe.models import DayPick, Member, RoundStatus, SwipeRound, Verdict, WeekCandidate
from backend.forkcast.swipe.solver import assign_chefs, solve

router = APIRouter(prefix="/api/swipe")

# Weeks this close to the best one count as equally good, and are the only
# thing the AI layer is allowed to choose between.
NEAR_TIE_EPSILON = 0.12


class RegisterMemberRequest(BaseModel):
    name: str
    avatar: str = "🍽️"
    member_id: str | None = None


class VerdictsRequest(BaseModel):
    member_id: str
    week_id: str
    year: int
    week: int
    verdicts: dict[str, Verdict] = Field(default_factory=dict)


class WeekRequest(BaseModel):
    year: int
    week: int
    day: str | None = None


class VolunteerRequest(BaseModel):
    year: int
    week: int
    day: str
    member_id: str
    role: str  # "chef" or "cleanup"


class MemberSummary(BaseModel):
    member_id: str
    name: str
    avatar: str
    swiped_total: int
    swiped_this_round: bool
    remaining_in_deck: int


class RoundView(BaseModel):
    round: SwipeRound
    members: list[MemberSummary]
    # True when someone swiped after the proposal was built.
    proposal_stale: bool = False
    note: str | None = None


def _member_summaries(swipe_round: SwipeRound, members: list[Member]) -> list[MemberSummary]:
    return [
        MemberSummary(
            member_id=member.member_id,
            name=member.name,
            avatar=member.avatar,
            swiped_total=len(member.verdicts),
            swiped_this_round=member.member_id in swipe_round.participants,
            remaining_in_deck=len(deck_module.build_deck(member)),
        )
        for member in members
    ]


def _view(swipe_round: SwipeRound, note: str | None = None) -> RoundView:
    return RoundView(
        round=swipe_round,
        members=_member_summaries(swipe_round, store.list_members()),
        proposal_stale=bool(
            swipe_round.proposal is not None
            and swipe_round.proposal_revision != swipe_round.verdicts_revision
        ),
        note=note,
    )


@router.get("/members")
def list_members() -> list[Member]:
    return store.list_members()


@router.post("/members")
def register_member(request: RegisterMemberRequest) -> Member:
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Skriv ett namn")

    if request.member_id:
        try:
            member = store.get_member(request.member_id)
            member.name = name
            member.avatar = request.avatar
            return store.save_member(member)
        except HTTPException:
            pass  # An id from a wiped or restored install: fall through.

    # No id - most often the same person on a second phone. Reuse the existing
    # member rather than creating a twin, which would split their swiping
    # history in two and inflate "x av y har swipat".
    existing = store.find_by_name(name)
    if existing:
        existing.avatar = request.avatar
        return store.save_member(existing)

    return store.save_member(
        Member(member_id=request.member_id or store.new_member_id(), name=name, avatar=request.avatar)
    )


@router.get("/deck")
def get_deck(member_id: str = Query(...), limit: int = Query(deck_module.DEFAULT_LIMIT)) -> list[deck_module.DeckCard]:
    return deck_module.build_deck(store.get_member(member_id), limit=limit)


@router.get("/summary")
def get_summary(member_id: str = Query(...)) -> list[deck_module.DeckCard]:
    """What this member has voted on so far, so they can check and correct it."""
    return deck_module.build_summary(store.get_member(member_id))


@router.post("/verdicts")
def record_verdicts(request: VerdictsRequest) -> RoundView:
    """Idempotent batch. Phones lose the LAN mid-deck, so swipes are sent as
    they happen and again on completion."""
    store.get_member(request.member_id)
    if request.verdicts:
        store.record_verdicts(request.member_id, request.verdicts)
    swipe_round = store.touch_round(request.week_id, request.year, request.week, request.member_id)
    return _view(swipe_round)


@router.get("/rounds/{week_id}")
def get_round(week_id: str, year: int = Query(...), week: int = Query(...)) -> RoundView:
    return _view(store.ensure_round(week_id, year, week))


def _build_proposal(pinned: dict[str, str] | None = None) -> tuple[WeekCandidate, list[WeekCandidate]]:
    """Solve using every registered member's durable preferences.

    Durable preferences are the point of the async design: someone who did not
    swipe this week still counts, they simply added nothing new.
    """
    members = store.list_members()
    if not members:
        raise HTTPException(status_code=409, detail="Ingen i familjen har swipat än")

    candidates = solve(
        list(MEALS.values()),
        members,
        DAYS,
        pinned=pinned,
        meal_minutes=deck_module.meal_minutes(),
        epsilon=NEAR_TIE_EPSILON,
    )
    if not candidates:
        raise HTTPException(status_code=409, detail="För få rätter — lägg till fler recept")
    chosen = reasons_module.fill(assign_chefs(candidates[0], members), members)
    return chosen, candidates


@router.post("/rounds/{week_id}/propose")
def propose(week_id: str, request: WeekRequest) -> RoundView:
    swipe_round = store.ensure_round(week_id, request.year, request.week)
    if swipe_round.status is RoundStatus.LOCKED:
        raise HTTPException(status_code=409, detail="Veckan är redan låst")

    proposal, candidates = _build_proposal()
    swipe_round.candidates = candidates[:5]
    swipe_round.proposal = proposal
    swipe_round.proposal_revision = swipe_round.verdicts_revision
    swipe_round.proposal_ai_used = False
    swipe_round.status = RoundStatus.PROPOSED
    swipe_round.shown_sets = [sorted(proposal.meal_ids)]
    note = _shortfall_note(proposal)
    return _view(store.save_round(swipe_round), note)


def _shortfall_note(proposal: WeekCandidate) -> str | None:
    if len(proposal.picks) < len(DAYS):
        return "För få rätter för hela veckan — lägg till fler recept i receptsamlingen."
    if proposal.rule_exceptions:
        broken = ", ".join(proposal.rule_exceptions)
        return f"Förslaget bryter mot en husregel ({broken}). Godkänner ni det blir det veckans undantag."
    return None


@router.post("/rounds/{week_id}/reroll")
def reroll(week_id: str, request: WeekRequest) -> RoundView:
    swipe_round = store.ensure_round(week_id, request.year, request.week)
    if swipe_round.status is RoundStatus.LOCKED:
        raise HTTPException(status_code=409, detail="Veckan är redan låst")
    if not swipe_round.proposal:
        raise HTTPException(status_code=409, detail="Det finns inget förslag att göra om")

    current = {pick.day: pick.meal_id for pick in swipe_round.proposal.picks}
    members = store.list_members()
    already_shown = {tuple(meal_set) for meal_set in swipe_round.shown_sets}

    def is_new(candidate: WeekCandidate) -> bool:
        return tuple(sorted(candidate.meal_ids)) not in already_shown

    if request.day:
        if request.day not in current:
            raise HTTPException(status_code=422, detail="Okänd dag")
        pinned = {day: meal_id for day, meal_id in current.items() if day != request.day}
        candidates = solve(
            list(MEALS.values()), members, DAYS,
            pinned=pinned, meal_minutes=deck_module.meal_minutes(),
        )
        replacement = next(
            (
                c for c in candidates
                if is_new(c)
                and dict((p.day, p.meal_id) for p in c.picks).get(request.day) != current[request.day]
            ),
            None,
        )
    else:
        candidates = solve(
            list(MEALS.values()), members, DAYS, meal_minutes=deck_module.meal_minutes(),
        )
        replacement = next((c for c in candidates if is_new(c)), None)

    if replacement is None:
        return _view(swipe_round, "Inga andra förslag som funkar lika bra — det här är veckan.")

    swipe_round.proposal = reasons_module.fill(assign_chefs(replacement, members), members)
    swipe_round.candidates = [c for c in candidates if c.meal_ids != replacement.meal_ids][:4]
    swipe_round.proposal_revision = swipe_round.verdicts_revision
    swipe_round.proposal_ai_used = False
    swipe_round.rerolls += 1
    swipe_round.shown_sets.append(sorted(replacement.meal_ids))
    note = _shortfall_note(replacement)
    if swipe_round.rerolls >= 3 and not note:
        note = f"Ni har gjort om {swipe_round.rerolls} gånger nu. Någon måste bestämma. 🙂"
    return _view(store.save_round(swipe_round), note)


@router.post("/rounds/{week_id}/enhance")
def enhance(week_id: str, request: WeekRequest) -> RoundView:
    """Let the AI pick between near-tied weeks and write the reasons.

    Called after the deterministic proposal is already on screen, so the family
    never waits on it. With no API key this is a no-op and the screens look the
    same - which is the point.
    """
    swipe_round = store.ensure_round(week_id, request.year, request.week)
    if not swipe_round.proposal or swipe_round.status is RoundStatus.LOCKED:
        return _view(swipe_round)

    forkcast_ai = ForkcastAI()
    if not forkcast_ai.available:
        return _view(swipe_round)

    members = store.list_members()
    options = [swipe_round.proposal, *swipe_round.candidates]
    ranking = forkcast_ai.rank_week_candidates(options, members)
    if ranking is None:
        return _view(swipe_round)

    chosen = options[ranking.choice_index]
    swipe_round.proposal = apply_ranking(
        reasons_module.fill(assign_chefs(chosen, members), members), ranking
    )
    swipe_round.proposal_ai_used = True
    return _view(store.save_round(swipe_round), None)


@router.post("/rounds/{week_id}/volunteer")
def volunteer(week_id: str, request: VolunteerRequest) -> RoundView:
    """Take or drop a chore on a day.

    A super-like already offers to cook, but most days have no super-liker, and
    nobody swipes to do the washing up. So this is a plain tap on the proposal.
    """
    if request.role not in {"chef", "cleanup"}:
        raise HTTPException(status_code=422, detail="Okänd syssla")

    swipe_round = store.ensure_round(week_id, request.year, request.week)
    if not swipe_round.proposal or swipe_round.status is RoundStatus.LOCKED:
        raise HTTPException(status_code=409, detail="Veckan går inte att ändra")
    store.get_member(request.member_id)

    pick = next((p for p in swipe_round.proposal.picks if p.day == request.day), None)
    if pick is None:
        raise HTTPException(status_code=422, detail="Okänd dag")

    holders = pick.chef if request.role == "chef" else pick.cleanup
    if request.member_id in holders:
        holders.remove(request.member_id)
    else:
        holders.append(request.member_id)
    return _view(store.save_round(swipe_round))


@router.post("/rounds/{week_id}/confirm")
def confirm(week_id: str, request: WeekRequest) -> RoundView:
    swipe_round = store.ensure_round(week_id, request.year, request.week)
    if not swipe_round.proposal:
        raise HTTPException(status_code=409, detail="Det finns inget förslag att låsa")

    names = {member.member_id: member.name for member in store.list_members()}
    plan: dict[str, ManualWeekDayPlan | None] = {day: None for day in DAYS}
    for pick in swipe_round.proposal.picks:
        plan[pick.day] = ManualWeekDayPlan(
            meal_name=pick.meal_name,
            meal_emoji=pick.meal_emoji,
            chef=[names.get(member_id, member_id) for member_id in pick.chef],
            cleanup=[names.get(member_id, member_id) for member_id in pick.cleanup],
            meal_id=pick.meal_id,
            note=pick.reason,
        )

    # Published so the hallway tablet picks it up for this week.
    save_manual_week(SaveManualWeekRequest(year=request.year, week=request.week, days=DAYS, plan=plan))

    swipe_round.status = RoundStatus.LOCKED
    return _view(store.save_round(swipe_round), "Veckan är låst och syns på tavlan.")
