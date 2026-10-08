"""Lesson times are Nigerian local time. Nigeria is UTC+1 all year (no daylight saving)."""

from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

WAT = timezone(timedelta(hours=1), "WAT")
CENT = Decimal("0.01")


def now() -> datetime:
    """The current time. Every time-based rule reads it through here, so tests can move the clock."""
    return datetime.now(timezone.utc)


def at_wat(day: date, clock: time) -> datetime:
    """A local date and time as an aware datetime."""
    return datetime.combine(day, clock, tzinfo=WAT)


def today_wat(now: datetime) -> date:
    return now.astimezone(WAT).date()


def money(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def to_kobo(amount: Decimal) -> int:
    return int(money(amount) * 100)
