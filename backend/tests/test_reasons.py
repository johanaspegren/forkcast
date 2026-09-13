"""The no-LLM explanations have to read like Swedish, not like a template."""

from backend.forkcast.swipe.models import Member
from backend.forkcast.swipe.reasons import describe


def member(name: str, **verdicts) -> Member:
    return Member(
        member_id=name, name=name,
        verdicts={meal: {"verdict": v, "updated_at": "2026-09-10T00:00:00+00:00"} for meal, v in verdicts.items()},
    )


def test_a_single_super_like_names_the_person_who_asked_for_it():
    assert describe("tacos", [member("Elsa", tacos="superlike")]) == "Elsa önskade den här."


def test_two_people_both_liked_it():
    people = [member("Elsa", tacos="like"), member("Oscar", tacos="like")]
    assert describe("tacos", people) == "Elsa och Oscar gillade båda den här."


def test_three_people_drops_the_dual_form():
    people = [member(n, tacos="like") for n in ("Elsa", "Oscar", "Johan")]
    assert describe("tacos", people) == "Elsa, Oscar och Johan gillade den här."


def test_a_super_like_outranks_plain_likes():
    people = [member("Elsa", tacos="like"), member("Oscar", tacos="superlike")]
    assert describe("tacos", people) == "Oscar önskade den här."


def test_a_dish_nobody_rated_still_gets_a_sentence():
    assert describe("tacos", [member("Elsa", pizza="like")]) == "Ingen hade något emot den här."
