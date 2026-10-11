"""Spec 4 R2 (onboarding checklist) and R3 (NIN verification with Dojah). Dojah is faked (`dojah` fixture)."""

import pytest
from sqlalchemy import text

from tests import helpers


@pytest.fixture
def tutor(client):
    """A tutor with a profile picture and an offer, ready for the NIN step."""
    tutor = helpers.register_tutor(client, full_name="Anthony Ozioko")
    assert helpers.upload_photo(client, tutor["headers"]).status_code == 200
    return tutor


def rename(client, tutor, first_name, surname, middle_name=None):
    return client.post("/v1/tutors/profile", headers=tutor["headers"], json={
        "first_name": first_name, "middle_name": middle_name, "surname": surname, "area": "Lekki"})


def steps(client, tutor) -> dict:
    return {s["key"]: s for s in client.get("/v1/onboarding", headers=tutor["headers"]).json()["steps"]}


# ---------- Checklist (R2) ----------

def test_checklist_starts_with_profile_then_nin_then_review(client):
    tutor = helpers.register_tutor(client)
    checklist = client.get("/v1/onboarding", headers=tutor["headers"]).json()
    assert [s["key"] for s in checklist["steps"]] == ["profile", "nin", "certificates", "quiz", "review"]
    assert checklist["steps"][0] == {"key": "profile", "done": False, "todo": ["Add a profile picture"]}
    assert checklist["vetting_status"] == "pending" and checklist["nin_attempts_left"] == 3

    helpers.upload_photo(client, tutor["headers"])
    assert steps(client, tutor)["profile"]["done"]


def test_tutor_without_a_picture_cannot_start_the_nin_step(client, dojah):
    tutor = helpers.register_tutor(client, full_name="Anthony Ozioko")
    response = helpers.check_nin(client, tutor, dojah.add("Anthony", "Ozioko"))
    assert response.status_code == 409 and "profile picture" in response.json()["detail"]
    assert dojah.lookups == []


def test_only_tutors_have_onboarding(client):
    parent = helpers.register_parent(client)
    assert client.get("/v1/onboarding", headers=parent["headers"]).status_code == 403
    assert helpers.check_nin(client, parent, "12345678901").status_code == 403


def test_approving_without_a_verified_nin_is_409_naming_what_is_missing(client, viewer, admin_headers, tutor):
    response = helpers.vet(client, admin_headers, tutor)
    assert response.status_code == 409
    assert "NIN not verified" in response.json()["detail"]
    assert "NIN not verified" in steps(client, tutor)["review"]["todo"]
    assert client.get(f"/v1/tutors/{tutor['id']}", headers=viewer).status_code == 404  # still hidden (R2.2)


def test_rejecting_is_always_allowed(client, admin_headers, tutor):
    assert helpers.vet(client, admin_headers, tutor, "rejected", "Incomplete").status_code == 200


def test_tutor_who_finished_onboarding_can_be_approved_and_is_listed(client, viewer, admin_headers):
    tutor = helpers.ready_tutor(client, admin_headers)
    assert steps(client, tutor)["nin"]["done"]
    assert helpers.vet(client, admin_headers, tutor).status_code == 200
    assert client.get(f"/v1/tutors/{tutor['id']}", headers=viewer).status_code == 200
    assert steps(client, tutor)["review"]["done"]


# ---------- NIN checks (R3.3, R3.4) ----------

def test_matching_name_and_selfie_verifies(client, dojah, tutor):
    nin = dojah.add("Anthony", "Ozioko")
    result = helpers.check_nin(client, tutor, nin).json()
    assert result["verified"] and result["nin_found"] and result["name_matches"] and result["selfie_matches"]
    assert result["nin_last4"] == nin[-4:]
    assert result["message"] == "Your NIN is verified"


@pytest.mark.parametrize("record", [
    {"first_name": "Antony", "surname": "Ozioko"},                              # spelt differently
    {"first_name": "Anthony", "surname": "Ozioko", "middle_name": "Chidi"},    # tutor left out the middle name
    {"first_name": "Ozioko", "surname": "Anthony"},                            # swapped order
    {"first_name": "Anthony", "surname": "Ozioko-Eze"},
])
def test_any_name_difference_is_a_mismatch(client, dojah, tutor, record):
    result = helpers.check_nin(client, tutor, dojah.add(**record)).json()
    assert not result["verified"] and result["nin_found"] and result["name_matches"] is False
    assert result["message"].startswith("Your name doesn't match your NIN record")


def test_extra_middle_name_is_a_mismatch(client, dojah, tutor):
    rename(client, tutor, "Anthony", "Ozioko", middle_name="Chidi")
    assert helpers.check_nin(client, tutor, dojah.add("Anthony", "Ozioko")).json()["name_matches"] is False


def test_only_capitals_and_spacing_may_differ(client, dojah, tutor):
    rename(client, tutor, "  anthony ", "OZIOKO", middle_name="chidi   emeka")
    nin = dojah.add("ANTHONY", "Ozioko", middle_name="Chidi Emeka")
    assert helpers.check_nin(client, tutor, nin).json()["verified"]


def test_name_mismatch_does_not_reveal_the_nin_records_name(client, dojah, tutor):
    nin = dojah.add("Chukwuemeka", "Nwachukwu")
    response = helpers.check_nin(client, tutor, nin)
    assert "CHUKWUEMEKA" not in response.text.upper() and "NWACHUKWU" not in response.text.upper()
    me = client.get("/v1/auth/me", headers=tutor["headers"]).text.upper()
    assert "CHUKWUEMEKA" not in me and "NWACHUKWU" not in me


def test_tutor_corrects_their_name_and_tries_again(client, dojah, tutor):
    nin = dojah.add("Anthony", "Ozioko", middle_name="Chidi")
    assert not helpers.check_nin(client, tutor, nin).json()["verified"]
    assert rename(client, tutor, "Anthony", "Ozioko", middle_name="Chidi").status_code == 200
    result = helpers.check_nin(client, tutor, nin).json()
    assert result["verified"] and result["attempts_left"] == 0


def test_unknown_nin_is_not_found(client, tutor):
    result = helpers.check_nin(client, tutor, "99999999999").json()
    assert not result["verified"] and not result["nin_found"] and result["name_matches"] is None
    assert "couldn't find this NIN" in result["message"]


def test_selfie_that_does_not_match_fails_with_no_override(client, admin_headers, dojah, tutor):
    dojah.selfie_matches = False
    result = helpers.check_nin(client, tutor, dojah.add("Anthony", "Ozioko")).json()
    assert not result["verified"] and result["name_matches"] and result["selfie_matches"] is False
    assert "selfie doesn't match" in result["message"]
    assert helpers.vet(client, admin_headers, tutor).status_code == 409


@pytest.mark.parametrize("nin", ["1234567890", "123456789012", "1234567890a", ""])
def test_nin_must_be_11_digits(client, dojah, tutor, nin):
    assert helpers.check_nin(client, tutor, nin).status_code == 422
    assert dojah.lookups == []


def test_selfie_must_be_an_image(client, dojah, tutor):
    response = helpers.check_nin(client, tutor, dojah.add("Anthony", "Ozioko"), selfie=b"not an image")
    assert response.status_code == 422
    assert dojah.lookups == []


def test_verified_nin_cannot_be_checked_again(client, dojah):
    tutor = helpers.verified_tutor(client)
    assert helpers.check_nin(client, tutor, tutor["nin"]).status_code == 409


# ---------- One NIN, one account (R3.6) ----------

def test_nin_verified_on_another_account_is_rejected(client, dojah):
    first = helpers.verified_tutor(client, full_name="Anthony Ozioko")
    second = helpers.register_tutor(client, full_name="Anthony Ozioko")
    helpers.upload_photo(client, second["headers"])
    response = helpers.check_nin(client, second, first["nin"])
    assert response.status_code == 409 and "another TutorLink account" in response.json()["detail"]
    assert dojah.lookups == [first["nin"]]  # refused before paying for a lookup


def test_a_failed_check_does_not_claim_the_nin(client, dojah, tutor):
    dojah.selfie_matches = False
    nin = dojah.add("Anthony", "Ozioko")
    helpers.check_nin(client, tutor, nin)
    dojah.selfie_matches = True
    other = helpers.register_tutor(client, full_name="Anthony Ozioko")
    helpers.upload_photo(client, other["headers"])
    assert helpers.check_nin(client, other, nin).json()["verified"]


# ---------- Attempts (R3.8) ----------

def test_fourth_attempt_within_24_hours_is_429_then_allowed_again(client, clock, dojah, tutor):
    for left in (2, 1, 0):
        assert helpers.check_nin(client, tutor, "99999999999").json()["attempts_left"] == left
        clock.travel(hours=1)
    response = helpers.check_nin(client, tutor, "99999999999")
    assert response.status_code == 429 and "Try again after" in response.json()["detail"]
    assert len(dojah.lookups) == 3
    checklist = client.get("/v1/onboarding", headers=tutor["headers"]).json()
    assert checklist["nin_attempts_left"] == 0 and checklist["nin_retry_at"]

    clock.travel(hours=21, minutes=1)  # the first attempt is now more than 24 hours old
    assert helpers.check_nin(client, tutor, dojah.add("Anthony", "Ozioko")).json()["verified"]


# ---------- What's stored (R3.7) and shown (R3.9) ----------

def test_full_nin_and_selfie_are_never_stored_or_returned(client, admin_headers, db, dojah):
    tutor = helpers.verified_tutor(client)
    nin = tutor["nin"]
    for row in db.execute(text("SELECT * FROM nin_verifications")).mappings():
        assert nin not in str(dict(row))
    for row in db.execute(text("SELECT * FROM tutor_profiles")).mappings():
        assert nin not in str(dict(row))
    assert nin not in client.get("/v1/auth/me", headers=tutor["headers"]).text
    assert nin not in client.get("/v1/admin/tutors/pending", headers=admin_headers).text
    columns = {r[0] for r in db.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'nin_verifications'"))}
    assert not {"nin", "selfie", "photo", "image", "first_name", "surname"} & columns


def test_admin_sees_each_check_and_the_verified_name(client, admin_headers, dojah, tutor):
    dojah.selfie_matches = False
    helpers.check_nin(client, tutor, dojah.add("Anthony", "Ozioko"))
    pending = next(p for p in client.get("/v1/admin/tutors/pending", headers=admin_headers).json()
                   if p["user_id"] == tutor["id"])
    assert pending["first_name"] == "Anthony" and pending["surname"] == "Ozioko"
    assert pending["photo_url"]
    check = pending["nin_check"]
    assert check["nin_found"] and check["name_matches"] and check["selfie_matches"] is False
    assert not check["verified"] and pending["nin_verified_at"] is None


def test_public_profile_has_no_nin_details(client, viewer, admin_headers):
    tutor = helpers.approved_tutor(client, admin_headers)
    public = client.get(f"/v1/tutors/{tutor['id']}", headers=viewer).json()
    assert "nin_check" not in public and "nin_verified_at" not in public


# ---------- Name lock (R3.1, R3.5) ----------

def test_tutor_registers_with_a_middle_name(client):
    response = helpers.google_register(client, helpers.unique_email("tutor"), middle_name="  Chidi ")
    assert response.status_code == 201
    assert response.json()["tutor_profile"]["middle_name"] == "Chidi"


def test_verified_tutor_cannot_change_their_name_but_an_admin_can(client, admin_headers):
    tutor = helpers.verified_tutor(client, full_name="Anthony Ozioko")
    response = rename(client, tutor, "Tony", "Ozioko")
    assert response.status_code == 409 and "can't be changed" in response.json()["detail"]
    # Other profile fields can still change.
    assert rename(client, tutor, "Anthony", "Ozioko").status_code == 200

    response = client.patch(f"/v1/admin/tutors/{tutor['id']}/name", headers=admin_headers,
                            json={"first_name": "Antony", "surname": "Ozioko"})
    assert response.status_code == 200
    profile = client.get("/v1/auth/me", headers=tutor["headers"]).json()["tutor_profile"]
    assert profile["first_name"] == "Antony" and profile["nin_verified_at"]
    assert client.patch(f"/v1/admin/tutors/{tutor['id']}/name", headers=tutor["headers"],
                        json={"first_name": "X", "surname": "Y"}).status_code == 403
