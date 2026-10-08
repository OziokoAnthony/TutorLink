"""Time-based rules (spec 1): expiries, payment deadlines, next periods, reports and payable earnings;
deleting lesson recordings after 90 days (spec 3); closing timed-out exam attempts and topping up the
exam's question bank (spec 4 R5).

`run_all` is called every SCHEDULER_INTERVAL_SECONDS by the API process. A PostgreSQL advisory lock
makes sure only one process runs it at a time, even with several API containers.
Run once by hand with: uv run python -m app.jobs
"""

import logging
import threading
from datetime import datetime

from sqlalchemy import text
from sqlmodel import Session

from app.core import clock
from app.core.config import settings
from app.db.session import engine
from app.domains.bookings import service as bookings
from app.domains.exam import service as exam
from app.domains.lessons import service as lessons

logger = logging.getLogger(__name__)

ADVISORY_LOCK_ID = 7_201_001  # any constant unique to this job


def run_all(session: Session, now: datetime | None = None) -> dict[str, int]:
    now = now or clock.now()
    # Order matters: deadlines are applied before new periods are created and paid.
    return {
        "expired_requests": bookings.expire_requests(session, now),
        "missed_deadlines": bookings.handle_missed_deadlines(session, now),
        "next_periods": bookings.create_next_periods(session, now),
        "paid_periods": bookings.pay_all_due(session, now),
        "reminders": bookings.remind_due_periods(session, now),
        "flagged_lessons": lessons.flag_unreported(session, now),
        "completed_lessons": lessons.complete_reported(session, now),
        "ended_bookings": bookings.end_finished_bookings(session, now),
        "deleted_recordings": lessons.delete_old_recordings(session, now),
        "closed_exam_attempts": exam.close_expired(session, now),
    }


def run_once() -> dict[str, int] | None:
    """Runs every job unless another process is already doing it. Returns None when skipped."""
    with engine.connect() as lock_conn:
        if not lock_conn.execute(text("SELECT pg_try_advisory_lock(:id)"), {"id": ADVISORY_LOCK_ID}).scalar():
            return None
        try:
            with Session(engine) as session:
                counts = run_all(session)
                # Starts Claude requests in the background; kept out of run_all so tests don't generate.
                counts["exam_batches_started"] = exam.top_up_bank(session)
                return counts
        finally:
            lock_conn.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": ADVISORY_LOCK_ID})
            lock_conn.commit()


def start_scheduler() -> threading.Event:
    """Starts the background loop; set the returned event to stop it."""
    stop = threading.Event()

    def loop():
        while not stop.wait(settings.SCHEDULER_INTERVAL_SECONDS):
            try:
                counts = run_once()
                if counts and any(counts.values()):
                    logger.info("Scheduled jobs: %s", {k: v for k, v in counts.items() if v})
            except Exception:
                logger.exception("Scheduled jobs failed")

    threading.Thread(target=loop, name="tutorlink-jobs", daemon=True).start()
    return stop


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_once())
