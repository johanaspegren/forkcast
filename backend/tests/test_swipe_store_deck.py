"""Durable preferences and what each round asks about."""

from datetime import datetime, timedelta, timezone

import pytest

from backend.forkcast.game.models import Meal
from backend.forkcast.swipe import deck as deck_module
from backend.forkcast.swipe import store
from backend.forkcast.swipe.models import Member, Verdict

NOW = datetime(2026, 9, 13, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    """Never let a test touch the family's real .forkcast-data."""
    monkeypatch.setattr(store, "MEMBERS_DIR", tmp_path / "members")
    monkeypatch.setattr(store, "ROUNDS_DIR", tmp_path / "rounds")
    # The deck reads the recipe collection only for photos and cooking times.
    monkeypatch.setattr(deck_module, "recipe_index", dict)


MEALS = {
    "a": Meal(id="a", name="Alpha", emoji="🅰️"),
    "b": Meal(id="b", name="Beta", emoji="🅱️"),
    "c": Meal(id="c", name="Gamma", emoji="🌀"),
}


def test_members_round_trip_and_list_in_creation_order():
    store.save_member(Member(member_id="m1", name="Elsa"))
    store.save_member(Member(member_id="m2", name="Oscar"))
    assert [m.name for m in store.list_members()] == ["Elsa", "Oscar"]
    assert store.get_member("m1").name == "Elsa"


def test_empty_store_bootstraps_default_family_members():
    assert [m.name for m in store.list_members()] == ["Mamma", "Pappa", "Amanda"]


def test_unknown_member_is_a_404_not_a_crash():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        store.get_member("nobody")
    assert excinfo.value.status_code == 404


def test_recording_verdicts_is_idempotent():
    store.save_member(Member(member_id="m1", name="Elsa"))
    store.record_verdicts("m1", {"a": Verdict.LIKE})
    first = store.get_member("m1").verdicts["a"]

    store.record_verdicts("m1", {"a": Verdict.LIKE})
    again = store.get_member("m1")
    assert len(again.verdicts) == 1
    assert again.verdicts["a"].verdict is Verdict.LIKE
    assert again.verdicts["a"].updated_at >= first.updated_at


def test_a_later_swipe_overwrites_an_earlier_one():
    store.save_member(Member(member_id="m1", name="Elsa"))
    store.record_verdicts("m1", {"a": Verdict.LIKE})
    store.record_verdicts("m1", {"a": Verdict.DISLIKE})
    assert store.get_member("m1").verdicts["a"].verdict is Verdict.DISLIKE


def test_a_swipe_bumps_the_round_revision_so_a_proposal_goes_stale():
    store.save_member(Member(member_id="m1", name="Elsa"))
    first = store.touch_round("2026-W38", 2026, 38, "m1")
    assert first.participants == ["m1"]
    assert first.verdicts_revision == 1

    second = store.touch_round("2026-W38", 2026, 38, "m1")
    assert second.participants == ["m1"], "the same member is not added twice"
    assert second.verdicts_revision == 2


def test_deck_asks_about_unswiped_meals_first():
    member = Member(
        member_id="m1", name="Elsa",
        verdicts={"a": {"verdict": "like", "updated_at": NOW.isoformat()}},
    )
    cards = deck_module.build_deck(member, list(MEALS.values()), now=NOW)
    assert [c.meal_id for c in cards] == ["b", "c"], "a fresh verdict should not be re-asked"


def test_deck_re_asks_about_verdicts_that_have_gone_stale():
    old = (NOW - timedelta(days=200)).isoformat()
    member = Member(
        member_id="m1", name="Elsa",
        verdicts={
            "a": {"verdict": "like", "updated_at": old},
            "b": {"verdict": "like", "updated_at": NOW.isoformat()},
        },
    )
    ids = [c.meal_id for c in deck_module.build_deck(member, list(MEALS.values()), now=NOW)]
    assert ids == ["c", "a"], "unswiped first, then the stale one"
    assert deck_module.build_deck(member, list(MEALS.values()), now=NOW)[1].previous_verdict is Verdict.LIKE


def test_deck_is_capped_so_a_round_stays_short():
    member = Member(member_id="m1", name="Elsa")
    assert len(deck_module.build_deck(member, list(MEALS.values()), limit=2, now=NOW)) == 2


def test_resolve_meals_drops_ids_whose_recipe_was_deleted():
    assert [m.id for m in deck_module.resolve_meals(["tacos", "recipe-deleted", "salmon"])] == [
        "tacos", "salmon",
    ]


def test_summary_lists_votes_with_favourites_first():
    member = Member(
        member_id="m1", name="Elsa",
        verdicts={
            "a": {"verdict": "dislike", "updated_at": NOW.isoformat()},
            "b": {"verdict": "superlike", "updated_at": NOW.isoformat()},
            "c": {"verdict": "like", "updated_at": NOW.isoformat()},
        },
    )
    cards = deck_module.build_summary(member, list(MEALS.values()))
    assert [c.meal_id for c in cards] == ["b", "c", "a"]
    assert [c.previous_verdict for c in cards] == [Verdict.SUPERLIKE, Verdict.LIKE, Verdict.DISLIKE]


def test_summary_skips_meals_that_no_longer_exist():
    member = Member(
        member_id="m1", name="Elsa",
        verdicts={
            "a": {"verdict": "like", "updated_at": NOW.isoformat()},
            "recipe-deleted": {"verdict": "like", "updated_at": NOW.isoformat()},
        },
    )
    assert [c.meal_id for c in deck_module.build_summary(member, list(MEALS.values()))] == ["a"]


def test_summary_is_empty_before_anyone_votes():
    assert deck_module.build_summary(Member(member_id="m1", name="Elsa"), list(MEALS.values())) == []


def test_find_by_name_ignores_case_and_padding():
    store.save_member(Member(member_id="m1", name="Elsa"))
    assert store.find_by_name("elsa").member_id == "m1"
    assert store.find_by_name("  ELSA  ").member_id == "m1"
    assert store.find_by_name("Oscar") is None


def test_find_by_name_is_how_a_second_phone_avoids_making_a_twin():
    """Registering without an id must not fork an existing member's history."""
    store.save_member(Member(member_id="m1", name="Johan"))
    store.record_verdicts("m1", {"a": Verdict.LIKE})

    same_person = store.find_by_name("Johan")
    assert same_person is not None
    assert len(same_person.verdicts) == 1, "the existing history is reused, not lost"
    assert len(store.list_members()) == 1
