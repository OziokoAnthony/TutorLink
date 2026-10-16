"""Spec 14: public subject pages, real numbers, reviews and a price guide."""

import json
from uuid import UUID

from sqlmodel import select

from app.domains.auth.models import User
from app.domains.lessons.models import Lesson, LessonStatus
from app.domains.reviews.models import TutorReview
from tests import helpers


def public(client, path: str):
    response = client.get(f"/v1/public{path}")  # no login
    assert response.status_code == 200, response.text
    return response.json()


def review(db, tutor: dict, parent: dict, rating: int, comment: str | None) -> None:
    db.add(TutorReview(tutor_id=UUID(tutor["id"]), parent_id=UUID(parent["id"]), rating=rating, comment=comment))
    db.commit()


def maths(client) -> dict:
    return public(client, "/subjects/mathematics")


# ---------- R1: what stays private ----------

def test_nothing_public_identifies_a_tutor_and_only_bookable_tutors_count(client, db, admin_headers, claude):
    tutor = helpers.approved_tutor(client, admin_headers, full_name="Tunde Bello", area="Ikoyi")
    helpers.register_tutor(client, full_name="Pending Person")  # not approved: not counted
    parent = helpers.register_parent(client, full_name="Ada Okafor")
    review(db, tutor, parent, 5, "Very patient with my son.")

    pages = [public(client, p) for p in ("/stats", "/reviews", "/subjects", "/subjects/mathematics",
                                          "/levels/senior_secondary")]
    text = json.dumps(pages)
    for secret in ("Tunde", "Bello", "Ikoyi", tutor["id"], tutor["email"], "Pending", "Okafor", parent["id"]):
        assert secret not in text, secret
    assert pages[0]["verified_tutors"] == 1 and maths(client)["tutors"] == 1

    removed = db.get(User, UUID(tutor["id"]))
    removed.is_active = False  # a removed account (spec 10) stops counting
    db.add(removed)
    db.commit()
    assert public(client, "/stats")["verified_tutors"] == 0 and maths(client)["tutors"] == 0


# ---------- R2: real numbers ----------

def test_the_stats_match_the_database(client, db, admin_headers, claude):
    tutor = helpers.approved_tutor(client, admin_headers)
    parents = [helpers.register_parent(client) for _ in range(2)]
    review(db, tutor, parents[0], 5, "Great.")
    review(db, tutor, parents[1], 4, None)
    stats = public(client, "/stats")
    lessons = len(db.exec(select(Lesson).where(Lesson.status == LessonStatus.completed)).all())
    assert stats == {"verified_tutors": 1, "lessons_taught": lessons, "average_rating": 4.5, "rating_count": 2}


# ---------- R3: reviews ----------

def test_public_reviews_are_first_name_stars_and_comment_only(client, db, admin_headers, claude):
    tutor = helpers.approved_tutor(client, admin_headers)
    ada, bayo, chi, dayo = (helpers.register_parent(client, full_name=n)
                            for n in ("Ada Okafor", "Bayo Ade", "Chi Obi", "Dayo Bello"))
    review(db, tutor, ada, 5, "  Very patient with my son.  ")
    review(db, tutor, bayo, 3, "It was fine.")  # 1-3 stars: left out
    review(db, tutor, chi, 5, None)  # no comment: left out
    review(db, tutor, dayo, 4, "   ")  # blank comment: left out
    shown = public(client, "/reviews")
    assert [(r["first_name"], r["rating"], r["comment"]) for r in shown] == [("Ada", 5, "Very patient with my son.")]
    assert set(shown[0]) == {"first_name", "rating", "comment", "created_at"}
    assert [r["first_name"] for r in maths(client)["reviews"]] == ["Ada"]  # the subject's reviews too (R3.2)


# ---------- R4, R5: subject and level pages ----------

def test_subject_pages_give_tutor_counts_and_parent_price_ranges(client, admin_headers, claude):
    for price in ("4000.00", "5000.00", "6000.00"):
        helpers.approved_tutor(client, admin_headers, price=price)
    helpers.approved_tutor(client, admin_headers, level="primary", price="3000.00")

    listed = {s["slug"]: s for s in public(client, "/subjects")}
    assert listed["mathematics"]["tutors"] == 4 and listed["english-language"]["tutors"] == 0

    page = maths(client)
    assert page["name"] == "Mathematics" and page["tutors"] == 4
    levels = {lv["level"]: lv for lv in page["levels"]}
    # Parents pay the price plus TutorLink's 10% parent fee, as in a booking.
    assert levels["senior_secondary"] == {"level": "senior_secondary", "tutors": 3,
                                          "min_price": "4400.00", "max_price": "6600.00"}
    assert levels["primary"] == {"level": "primary", "tutors": 1, "min_price": None, "max_price": None}  # "Prices vary"

    senior = public(client, "/levels/senior_secondary")
    assert senior["tutors"] == 3
    assert [(s["name"], s["tutors"], s["min_price"]) for s in senior["subjects"]] == [("Mathematics", 3, "4400.00")]


def test_only_offered_subjects_have_pages(client, admin_headers):
    assert client.get("/v1/public/subjects/astrology").status_code == 404
    subject_id = next(s["id"] for s in client.get("/v1/admin/subjects", headers=admin_headers).json()
                      if s["name"] == "Mathematics")
    client.patch(f"/v1/admin/subjects/{subject_id}", headers=admin_headers, json={"is_offered": False})
    assert client.get("/v1/public/subjects/mathematics").status_code == 404
    assert "mathematics" not in [s["slug"] for s in public(client, "/subjects")]
    assert client.get("/v1/public/levels/nowhere").status_code == 422
