"""Spec 3: online and offline lessons, meeting links, the parent's address, and lesson recordings."""

import time
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest

from app.core import storage
from tests import helpers

VIDEO = b"\x00\x00\x00\x18ftypmp42" + b"0" * 2048  # stands in for an MP4 file
LINK = "https://meet.google.com/abc-defg-hij"


@pytest.fixture
def parent(client):
    return helpers.register_parent(client, address="12 Admiralty Way, Lekki")


@pytest.fixture
def tutor(client, admin_headers):
    return helpers.approved_tutor(client, admin_headers)


@pytest.fixture
def online_lesson(client, clock, paystack, parent, tutor):
    """A paid online lesson that has just ended."""
    booking = helpers.paid_booking(client, paystack, parent, tutor, mode="online")
    lesson = helpers.lessons(client, parent)[0]
    clock.set(datetime.fromisoformat(lesson["ends_at"]) + timedelta(minutes=5))
    return {**lesson, "booking": booking}


def request_upload(client, tutor, lesson, *, filename="lesson.mp4", content_type="video/mp4", size=len(VIDEO)):
    return client.post(f"/v1/lessons/{lesson['id']}/recording/upload", headers=tutor["headers"],
                       json={"filename": filename, "content_type": content_type, "size": size})


def put_file(client, upload: dict, data: bytes = VIDEO):
    """What the browser does with the upload link (here, the local stand-in for R2)."""
    parts = urlsplit(upload["upload_url"])
    return client.put(f"{parts.path}?{parts.query}", content=data, headers={"Content-Type": upload["content_type"]})


def upload_recording(client, tutor, lesson) -> dict:
    upload = request_upload(client, tutor, lesson)
    assert upload.status_code == 200, upload.text
    assert put_file(client, upload.json()).status_code == 204
    done = client.post(f"/v1/lessons/{lesson['id']}/recording/complete", headers=tutor["headers"])
    assert done.status_code == 200, done.text
    return done.json()


# ---------- R1: mode, consent, meeting link, address ----------

def test_online_booking_without_recording_consent_is_rejected(client, parent, tutor):
    assert helpers.book(client, parent, tutor, mode="online", recording_consent=False).status_code == 422
    booking = helpers.book(client, parent, tutor, mode="online")
    assert booking.status_code == 201 and booking.json()["recording_consent_at"]


def test_offline_booking_needs_no_consent(client, parent, tutor):
    booking = helpers.book(client, parent, tutor, mode="offline", recording_consent=False)
    assert booking.status_code == 201 and booking.json()["recording_consent_at"] is None


def test_online_job_without_recording_consent_is_rejected(client, parent):
    body = helpers.job_body(mode="online", area=None, recording_consent=False)
    assert client.post("/v1/jobs", headers=parent["headers"], json=body).status_code == 422


def test_booking_from_an_online_job_keeps_the_consent(client, parent, tutor):
    job = helpers.post_job(client, parent, mode="online", area=None)
    helpers.apply_to_job(client, tutor, job)
    assert helpers.choose_applicant(client, parent, job, tutor).json()["recording_consent_at"]


def test_parent_sees_the_meeting_link_only_after_paying(client, paystack, parent, tutor):
    booking = helpers.accepted_booking(client, parent, tutor, mode="online")
    url = f"/v1/bookings/{booking['id']}"
    response = client.put(f"{url}/meeting-link", headers=tutor["headers"], json={"meeting_link": LINK})
    assert response.status_code == 200 and response.json()["meeting_link"] == LINK
    assert client.get(url, headers=parent["headers"]).json()["meeting_link"] is None
    helpers.deposit(client, paystack, parent, booking["periods"][0]["amount"])
    assert client.get(url, headers=parent["headers"]).json()["meeting_link"] == LINK


def test_meeting_link_must_be_https_and_online_only(client, parent, tutor):
    online = helpers.accepted_booking(client, parent, tutor, mode="online")
    bad = client.put(f"/v1/bookings/{online['id']}/meeting-link", headers=tutor["headers"],
                     json={"meeting_link": "http://meet.example.com/x"})
    assert bad.status_code == 422
    offline = helpers.accepted_booking(client, helpers.register_parent(client), tutor,
                                       start_date=helpers.days_ahead(4))
    response = client.put(f"/v1/bookings/{offline['id']}/meeting-link", headers=tutor["headers"],
                          json={"meeting_link": LINK})
    assert response.status_code == 422


def test_tutor_sees_the_address_only_after_the_first_payment(client, paystack, parent, tutor):
    booking = helpers.accepted_booking(client, parent, tutor)
    url = f"/v1/bookings/{booking['id']}"
    assert client.get(url, headers=tutor["headers"]).json()["parent_address"] is None
    helpers.deposit(client, paystack, parent, booking["periods"][0]["amount"])
    assert client.get(url, headers=tutor["headers"]).json()["parent_address"] == "12 Admiralty Way, Lekki"
    assert client.get("/v1/bookings/tutor/me", headers=tutor["headers"]).json()[0]["parent_address"]


# ---------- R2: recordings ----------

def test_online_report_needs_a_completed_recording(client, tutor, online_lesson):
    assert online_lesson["recording_required"] and not online_lesson["has_recording"]
    assert helpers.report(client, tutor, online_lesson["id"]).status_code == 422
    upload = request_upload(client, tutor, online_lesson).json()
    put_file(client, upload)
    # Uploaded but not completed: still refused.
    assert helpers.report(client, tutor, online_lesson["id"]).status_code == 422
    assert client.post(f"/v1/lessons/{online_lesson['id']}/recording/complete",
                       headers=tutor["headers"]).status_code == 200
    response = helpers.report(client, tutor, online_lesson["id"])
    assert response.status_code == 200 and response.json()["has_recording"]


def test_offline_report_needs_no_recording(client, db, clock, paystack, parent, tutor):
    helpers.completed_lesson(client, db, clock, paystack, parent, tutor)
    assert helpers.lessons(client, parent)[0]["recording_required"] is False


@pytest.mark.parametrize("filename,content_type,size", [
    ("lesson.mp4", "video/mp4", 3 * 1024 ** 3),  # 3 GB
    ("setup.exe", "application/x-msdownload", 1024),
    ("setup.exe", "video/mp4", 1024),  # a video type doesn't make an .exe acceptable
    ("lesson.mp4", "application/octet-stream", 1024),
])
def test_upload_link_refuses_big_or_non_video_files(client, tutor, online_lesson, filename, content_type, size):
    response = request_upload(client, tutor, online_lesson, filename=filename, content_type=content_type, size=size)
    assert response.status_code == 422


def test_mov_and_webm_are_accepted(client, tutor, online_lesson):
    for filename, content_type in (("lesson.mov", "video/quicktime"), ("lesson.webm", "video/webm")):
        assert request_upload(client, tutor, online_lesson, filename=filename,
                              content_type=content_type).status_code == 200


def test_upload_of_a_different_size_is_refused_and_not_completed(client, tutor, online_lesson):
    upload = request_upload(client, tutor, online_lesson).json()
    assert put_file(client, upload, VIDEO[:100]).status_code == 403
    response = client.post(f"/v1/lessons/{online_lesson['id']}/recording/complete", headers=tutor["headers"])
    assert response.status_code == 422


def test_stored_file_is_checked_again_before_the_report(client, tutor, online_lesson):
    upload_recording(client, tutor, online_lesson)
    key = storage._local_path  # the stored file vanishes (e.g. deleted from the bucket)
    lesson_key = next(p for p in key("recordings").rglob("*") if p.is_file())
    lesson_key.unlink()
    assert helpers.report(client, tutor, online_lesson["id"]).status_code == 422


def test_only_the_lessons_tutor_can_upload(client, admin_headers, online_lesson):
    other = helpers.approved_tutor(client, admin_headers, full_name="Bola Ade")
    assert request_upload(client, other, online_lesson).status_code == 403


def test_offline_lessons_have_no_recording_upload(client, clock, paystack, parent, tutor):
    helpers.paid_booking(client, paystack, parent, tutor)
    lesson = helpers.lessons(client, parent)[0]
    clock.set(datetime.fromisoformat(lesson["ends_at"]) + timedelta(minutes=5))
    assert request_upload(client, tutor, lesson).status_code == 422


def test_viewing_link_for_parent_tutor_and_admin_only(client, admin_headers, parent, tutor, online_lesson):
    upload_recording(client, tutor, online_lesson)
    url = f"/v1/lessons/{online_lesson['id']}/recording"
    for headers in (parent["headers"], tutor["headers"], admin_headers):
        response = client.get(url, headers=headers)
        assert response.status_code == 200, response.text
    other_parent = helpers.register_parent(client)
    other_tutor = helpers.approved_tutor(client, admin_headers, full_name="Bola Ade")
    assert client.get(url, headers=other_parent["headers"]).status_code == 403
    assert client.get(url, headers=other_tutor["headers"]).status_code == 403


def test_viewing_link_expires_after_15_minutes_and_plays_the_file(client, clock, parent, tutor, online_lesson):
    upload_recording(client, tutor, online_lesson)
    link = client.get(f"/v1/lessons/{online_lesson['id']}/recording", headers=parent["headers"]).json()
    assert datetime.fromisoformat(link["expires_at"]) == clock.now() + timedelta(minutes=15)
    parts = urlsplit(link["url"])
    expires = int(parse_qs(parts.query)["expires"][0])
    assert 15 * 60 - 5 <= expires - time.time() <= 15 * 60
    played = client.get(f"{parts.path}?{parts.query}")
    assert played.status_code == 200 and played.content == VIDEO


def test_parent_lesson_shows_the_recording_next_to_the_report(client, parent, tutor, online_lesson):
    upload_recording(client, tutor, online_lesson)
    helpers.report(client, tutor, online_lesson["id"])
    seen = helpers.lessons(client, parent)[0]
    assert seen["has_recording"] and seen["topic_covered"] == "Fractions"


def test_recordings_are_deleted_after_90_days_unless_a_problem_is_open(client, db, clock, paystack, admin_headers,
                                                                        parent, tutor, online_lesson):
    upload_recording(client, tutor, online_lesson)
    helpers.report(client, tutor, online_lesson["id"])

    # A second online lesson with an open problem keeps its recording.
    other_parent = helpers.register_parent(client)
    helpers.paid_booking(client, paystack, other_parent, tutor, mode="online", start_date=helpers.days_ahead(4))
    disputed = helpers.lessons(client, other_parent)[0]
    clock.set(datetime.fromisoformat(disputed["ends_at"]) + timedelta(minutes=5))
    upload_recording(client, tutor, disputed)
    helpers.report(client, tutor, disputed["id"])
    client.post(f"/v1/lessons/{disputed['id']}/problem", headers=other_parent["headers"],
                json={"kind": "agreement_broken", "description": "The lesson was about a different subject."})

    clock.set(datetime.fromisoformat(online_lesson["ends_at"]) + timedelta(days=89))
    helpers.run_jobs(db, clock)
    assert helpers.lessons(client, parent)[0]["has_recording"]

    clock.set(datetime.fromisoformat(disputed["ends_at"]) + timedelta(days=91))
    helpers.run_jobs(db, clock)
    assert not helpers.lessons(client, parent)[0]["has_recording"]
    assert client.get(f"/v1/lessons/{online_lesson['id']}/recording", headers=parent["headers"]).status_code == 404
    assert helpers.lessons(client, other_parent)[0]["has_recording"]
    files = [p for p in storage._local_path("recordings").rglob("*") if p.is_file()]
    assert len(files) == 1  # only the disputed lesson's recording is left
