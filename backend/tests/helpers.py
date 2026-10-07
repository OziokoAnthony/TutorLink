"""Small factories that drive the API the same way the frontend would, plus fakes for Paystack and the clock."""

import hashlib
import hmac
import io
import json
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from PIL import Image

from app.core.clock import WAT
from app.core.config import settings
from app.scripts.create_admin import create_admin as create_admin_user

PASSWORD = "password123"
ALL_WEEK = [{"day_of_week": d, "start_time": "08:00", "end_time": "20:00"} for d in range(7)]
STRENGTHS = "Quick with mental arithmetic and enjoys puzzles."
WEAKNESSES = "Struggles with word problems and fractions."


# ---------- Fakes ----------

class FakeClock:
    def __init__(self):
        self.current = datetime.now(timezone.utc)

    def now(self) -> datetime:
        return self.current

    def travel(self, **delta) -> datetime:
        self.current += timedelta(**delta)
        return self.current

    def set(self, moment: datetime) -> datetime:
        self.current = moment
        return self.current


class FakePaystack:
    def __init__(self):
        self.transactions: dict[str, dict] = {}  # reference -> what Verify Transaction returns
        self.customers: dict[str, str] = {}  # email -> customer_code
        self.account_names: dict[str, str] = {}  # account number -> name the bank reports
        self.transfers: list[dict] = []
        self.transfer_status = "pending"
        self.unreachable = False
        self.banks = [{"name": "Access Bank", "code": "044", "active": True},
                      {"name": "Test Bank", "code": "001", "active": True}]

    def verify_transaction(self, reference):
        if self.unreachable:
            raise HTTPException(502, "Payment provider unavailable")
        return self.transactions.get(reference, {})

    def create_customer(self, *, email, first_name, last_name, phone):
        code = f"CUS_{len(self.customers) + 1}"
        self.customers[email] = code
        return {"customer_code": code}

    def create_dedicated_account(self, customer_code):
        number = f"90{len(self.customers):08d}"
        return {"account_number": number, "account_name": "TUTORLINK/PARENT", "bank": {"name": "Test Bank"}}

    def list_banks(self):
        return self.banks

    def resolve_account(self, account_number, bank_code):
        return {"account_number": account_number,
                "account_name": self.account_names.get(account_number, "UNKNOWN ACCOUNT NAME")}

    def create_transfer_recipient(self, *, name, account_number, bank_code):
        return {"recipient_code": f"RCP_{account_number}"}

    def initiate_transfer(self, *, amount_kobo, recipient_code, reference, reason):
        self.transfers.append({"amount_kobo": amount_kobo, "recipient_code": recipient_code, "reference": reference})
        return {"transfer_code": f"TRF_{len(self.transfers)}", "status": self.transfer_status}


# ---------- Webhooks ----------

def sign(body: bytes) -> str:
    return hmac.new(settings.PAYSTACK_WEBHOOK_SECRET.encode(), body, hashlib.sha512).hexdigest()


def post_webhook(client, payload: dict, signature: str | None = None):
    body = json.dumps(payload).encode()
    return client.post("/v1/webhooks/payment", content=body, headers={
        "Content-Type": "application/json",
        "X-Paystack-Signature": signature if signature is not None else sign(body),
    })


def deposit(client, paystack: FakePaystack, parent: dict, naira, reference: str | None = None,
            confirmed: bool = True):
    """A bank transfer into the parent's account number, as Paystack reports it."""
    reference = reference or f"DEP-{uuid4().hex[:10]}"
    code = paystack.customers[parent["email"]]
    data = {"id": abs(hash(reference)) % 10**9, "reference": reference, "amount": int(float(naira) * 100),
            "currency": "NGN", "channel": "dedicated_nuban", "customer": {"customer_code": code}}
    if confirmed:
        paystack.transactions[reference] = {**data, "status": "success"}
    return post_webhook(client, {"event": "charge.success", "data": data})


def transfer_event(client, reference: str, event: str = "transfer.success"):
    return post_webhook(client, {"event": event, "data": {"id": abs(hash(reference + event)) % 10**9,
                                                          "reference": reference}})


# ---------- Accounts ----------

def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}@example.com"


def image_bytes(size=(600, 400), fmt: str = "PNG") -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, (200, 120, 40)).save(out, fmt)
    return out.getvalue()


def upload_photo(client, headers: dict, data: bytes | None = None, filename: str = "me.png"):
    return client.put("/v1/auth/me/photo", headers=headers,
                      files={"file": (filename, data if data is not None else image_bytes(), "image/png")})


def login(client, email: str, password: str = PASSWORD) -> dict:
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register_parent(client, email: str | None = None, full_name: str = "Ada Parent", photo: bool = True) -> dict:
    email = email or unique_email("parent")
    response = client.post("/v1/auth/register", json={
        "email": email, "password": PASSWORD, "role": "parent", "full_name": full_name,
    })
    assert response.status_code == 201, response.text
    parent = {"id": response.json()["user"]["id"], "email": email, "headers": login(client, email)}
    if photo:
        assert upload_photo(client, parent["headers"]).status_code == 200
    return parent


def offer(subjects=("Mathematics",), level: str = "senior_secondary", price: str = "5000.00",
          windows: list | None = None) -> dict:
    return {"subjects": list(subjects), "level": level, "price": price, "windows": windows or ALL_WEEK}


def register_tutor(client, email: str | None = None, full_name: str = "Tunde Tutor", area: str = "Lekki",
                   offers: list | None = None, **offer_kwargs) -> dict:
    """`full_name` is split into first name (first word) and surname (the rest)."""
    email = email or unique_email("tutor")
    first_name, _, surname = full_name.partition(" ")
    response = client.post("/v1/auth/register", json={
        "email": email, "password": PASSWORD, "role": "tutor", "first_name": first_name, "surname": surname,
        "area": area, "offers": offers or [offer(**offer_kwargs)],
    })
    assert response.status_code == 201, response.text
    user = response.json()["user"]
    tutor = {"id": user["id"], "email": email, "work_email": user["work_email"],
             "headers": login(client, user["work_email"])}
    tutor["offer_id"] = client.get("/v1/tutors/profile/offers", headers=tutor["headers"]).json()[0]["id"]
    return tutor


def create_admin(client, db) -> dict:
    email = unique_email("admin")
    create_admin_user(db, email, PASSWORD)
    return login(client, email)


def vet(client, admin_headers: dict, tutor: dict, status: str = "approved", note: str | None = None):
    return client.patch(f"/v1/tutors/{tutor['id']}/vet", headers=admin_headers,
                        json={"status": status, "note": note})


def approved_tutor(client, admin_headers: dict, **kwargs) -> dict:
    """An approved tutor with one offer: senior-secondary Mathematics, any day 08:00-20:00, ₦5,000."""
    tutor = register_tutor(client, **kwargs)
    assert vet(client, admin_headers, tutor).status_code == 200
    return tutor


# ---------- Bookings ----------

def wat_today(now: datetime | None = None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(WAT).date()


def days_ahead(n: int, now: datetime | None = None) -> date:
    return wat_today(now) + timedelta(days=n)


def book(client, parent: dict, tutor: dict, *, subjects=("Mathematics",), slots: list | None = None,
         start_date: date | None = None, end_date: date | None = None, billing_period: str = "weekly",
         mode: str = "offline", offer_id: str | None = None, strengths: str = STRENGTHS,
         weaknesses: str = WEAKNESSES):
    """Requests a booking. By default: one 15:00-16:00 lesson a week, starting in 3 days."""
    start_date = start_date or days_ahead(3)
    slots = slots if slots is not None else [
        {"day_of_week": start_date.weekday(), "start_time": "15:00", "end_time": "16:00"}]
    return client.post("/v1/bookings", headers=parent["headers"], json={
        "tutor_id": tutor["id"], "offer_id": offer_id or tutor["offer_id"], "subjects": list(subjects),
        "slots": slots, "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat() if end_date else None, "billing_period": billing_period,
        "mode": mode, "child_strengths": strengths, "child_weaknesses": weaknesses,
    })


def requested_booking(client, parent: dict, tutor: dict, **kwargs) -> dict:
    response = book(client, parent, tutor, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()


def accepted_booking(client, parent: dict, tutor: dict, **kwargs) -> dict:
    """A booking the tutor accepted. Returns the parent's view (with its first period)."""
    booking = requested_booking(client, parent, tutor, **kwargs)
    response = client.post(f"/v1/bookings/{booking['id']}/accept", headers=tutor["headers"])
    assert response.status_code == 200, response.text
    return client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()


def paid_booking(client, paystack: FakePaystack, parent: dict, tutor: dict, **kwargs) -> dict:
    """An accepted booking whose first period the parent paid by bank transfer."""
    booking = accepted_booking(client, parent, tutor, **kwargs)
    due = booking["periods"][0]["amount"]
    assert deposit(client, paystack, parent, due).status_code == 200
    booking = client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()
    assert booking["status"] == "active", booking
    return booking


def lessons(client, user: dict, role: str = "parent") -> list[dict]:
    path = "/v1/lessons/me" if role == "parent" else "/v1/lessons/tutor/me"
    response = client.get(path, headers=user["headers"])
    assert response.status_code == 200, response.text
    return response.json()


def run_jobs(db, clock: FakeClock):
    from app import jobs

    return jobs.run_all(db, clock.now())


def report(client, tutor: dict, lesson_id: str, topic: str = "Fractions"):
    return client.post(f"/v1/lessons/{lesson_id}/report", headers=tutor["headers"],
                       json={"topic_covered": topic, "homework": "Exercise 3"})


def completed_lesson(client, db, clock: FakeClock, paystack: FakePaystack, parent: dict, tutor: dict) -> dict:
    """A paid lesson that was taught, reported, and whose problem window closed: earning payable."""
    booking = paid_booking(client, paystack, parent, tutor)
    lesson = [l for l in lessons(client, parent) if l["booking_id"] == booking["id"]][0]
    clock.set(datetime.fromisoformat(lesson["ends_at"]) + timedelta(minutes=5))
    assert report(client, tutor, lesson["id"]).status_code == 200
    clock.travel(hours=24, minutes=1)
    run_jobs(db, clock)
    return lesson
