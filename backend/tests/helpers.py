"""Small factories that drive the API the same way the frontend would."""

from uuid import uuid4

from app.scripts.create_admin import create_admin as create_admin_user

PASSWORD = "password123"


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}@example.com"


def login(client, email: str, password: str = PASSWORD) -> dict:
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register_parent(client, email: str | None = None, full_name: str = "Ada Parent") -> dict:
    email = email or unique_email("parent")
    response = client.post("/v1/auth/register", json={
        "email": email, "password": PASSWORD, "role": "parent", "full_name": full_name,
    })
    assert response.status_code == 201, response.text
    return {"id": response.json()["user"]["id"], "email": email, "headers": login(client, email)}


def register_tutor(client, email: str | None = None, full_name: str = "Tunde Tutor",
                   area: str = "Lekki", rate: str = "5000.00") -> dict:
    email = email or unique_email("tutor")
    response = client.post("/v1/auth/register", json={
        "email": email, "password": PASSWORD, "role": "tutor", "full_name": full_name,
        "area": area, "rate_per_session": rate,
    })
    assert response.status_code == 201, response.text
    return {"id": response.json()["user"]["id"], "email": email, "headers": login(client, email)}


def create_admin(client, db) -> dict:
    email = unique_email("admin")
    create_admin_user(db, email, PASSWORD)
    return login(client, email)


def add_subject(client, tutor: dict, subject: str = "Mathematics", level: str = "senior_secondary") -> dict:
    response = client.post("/v1/tutors/profile/subjects", headers=tutor["headers"],
                           json={"subject": subject, "level": level})
    assert response.status_code == 201, response.text
    return response.json()


def vet(client, admin_headers: dict, tutor: dict, status: str = "approved", note: str | None = None):
    return client.patch(f"/v1/tutors/{tutor['id']}/vet", headers=admin_headers,
                        json={"status": status, "note": note})


def approved_tutor(client, admin_headers: dict, **kwargs) -> dict:
    """A tutor who is approved and teaches senior-secondary Mathematics."""
    tutor = register_tutor(client, **kwargs)
    add_subject(client, tutor)
    assert vet(client, admin_headers, tutor).status_code == 200
    return tutor


def book(client, parent: dict, tutor: dict, day: int = 0, start: str = "15:00", end: str = "16:00",
         subject: str = "Mathematics", level: str = "senior_secondary"):
    return client.post("/v1/schedules", headers=parent["headers"], json={
        "tutor_id": tutor["id"], "day_of_week": day, "start_time": start, "end_time": end,
        "subject": subject, "level": level,
    })


def booked_schedule(client, parent: dict, tutor: dict, **kwargs) -> dict:
    response = book(client, parent, tutor, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()


def log_session(client, tutor: dict, schedule_id: str, session_date: str, topic: str = "Algebra"):
    return client.post("/v1/sessions", headers=tutor["headers"], json={
        "schedule_id": schedule_id, "session_date": session_date, "topic_covered": topic,
        "homework": "Exercise 3",
    })


def logged_session(client, tutor: dict, schedule_id: str, session_date: str) -> dict:
    response = log_session(client, tutor, schedule_id, session_date)
    assert response.status_code == 201, response.text
    return response.json()


def confirmed_session(client, parent: dict, tutor: dict, schedule_id: str, session_date: str) -> dict:
    session = logged_session(client, tutor, schedule_id, session_date)
    response = client.patch(f"/v1/sessions/{session['id']}/confirm", headers=parent["headers"])
    assert response.status_code == 200, response.text
    return response.json()
