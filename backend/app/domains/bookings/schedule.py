"""Pure date maths for bookings: when lessons happen and how they group into billing periods."""

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Protocol

from app.core.clock import at_wat
from app.domains.bookings.models import BillingPeriod

PAY_BEFORE = timedelta(hours=24)  # a period must be paid 24 h before its first lesson (spec 1 R2.6)


class Weekly(Protocol):
    day_of_week: int
    start_time: time
    end_time: time


@dataclass(frozen=True)
class Occurrence:
    lesson_date: date
    start_time: time
    end_time: time

    @property
    def starts_at(self) -> datetime:
        return at_wat(self.lesson_date, self.start_time)

    @property
    def ends_at(self) -> datetime:
        return at_wat(self.lesson_date, self.end_time)


@dataclass(frozen=True)
class PeriodPlan:
    starts_on: date
    ends_on: date
    lessons: list[Occurrence]

    @property
    def first_lesson_at(self) -> datetime:
        return self.lessons[0].starts_at

    @property
    def last_lesson_end_at(self) -> datetime:
        return self.lessons[-1].ends_at

    @property
    def due_at(self) -> datetime:
        return self.first_lesson_at - PAY_BEFORE


def overlaps(a: Weekly, b: Weekly) -> bool:
    """Same weekday and the times overlap. Touching ends (14:00-15:00 and 15:00-16:00) don't."""
    return a.day_of_week == b.day_of_week and a.start_time < b.end_time and a.end_time > b.start_time


def within(slot: Weekly, window: Weekly) -> bool:
    return (slot.day_of_week == window.day_of_week
            and slot.start_time >= window.start_time and slot.end_time <= window.end_time)


def occurrences(slots: list[Weekly], first: date, last: date) -> list[Occurrence]:
    """Every lesson from `first` to `last` (inclusive), in time order."""
    found = []
    day = first
    while day <= last:
        for slot in slots:
            if slot.day_of_week == day.weekday():
                found.append(Occurrence(day, slot.start_time, slot.end_time))
        day += timedelta(days=1)
    return sorted(found, key=lambda o: o.starts_at)


def period_bounds(billing: BillingPeriod, day: date) -> tuple[date, date]:
    """The billing period containing `day`."""
    if billing == BillingPeriod.daily:
        return day, day
    if billing == BillingPeriod.weekly:
        monday = day - timedelta(days=day.weekday())
        return monday, monday + timedelta(days=6)
    last = calendar.monthrange(day.year, day.month)[1]
    return day.replace(day=1), day.replace(day=last)


def plan_period(slots: list[Weekly], billing: BillingPeriod, from_date: date, end_date: date | None,
                not_before: datetime | None = None) -> PeriodPlan | None:
    """The next billing period whose lessons start on or after `from_date` (and after `not_before`),
    or None when the booking's end date leaves no more lessons."""
    if not slots:
        return None
    # Every weekday with a slot comes round within 7 days; not_before can push us at most one more week.
    horizon = from_date + timedelta(days=14)
    if not_before is not None:
        horizon = max(horizon, not_before.date() + timedelta(days=14))
    if end_date is not None:
        horizon = min(horizon, end_date)
    upcoming = [o for o in occurrences(slots, from_date, horizon)
                if not_before is None or o.starts_at > not_before]
    if not upcoming:
        return None
    first = upcoming[0]
    _, period_end = period_bounds(billing, first.lesson_date)
    if end_date is not None:
        period_end = min(period_end, end_date)
    lessons = [o for o in occurrences(slots, first.lesson_date, period_end) if o.starts_at >= first.starts_at]
    return PeriodPlan(starts_on=first.lesson_date, ends_on=period_end, lessons=lessons)
