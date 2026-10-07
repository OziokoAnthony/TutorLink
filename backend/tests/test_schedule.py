"""The date maths behind billing periods (no database)."""

from datetime import date, datetime, time, timedelta

from app.core.clock import WAT
from app.domains.bookings.models import BillingPeriod
from app.domains.bookings.schedule import overlaps, period_bounds, plan_period, within
from app.domains.tutors.models import WeeklyTime

MON_WED = [WeeklyTime(day_of_week=0, start_time=time(15), end_time=time(16)),
           WeeklyTime(day_of_week=2, start_time=time(15), end_time=time(16))]
MONDAY = date(2026, 10, 12)


def test_overlap_rules_match_the_clash_examples():
    new = WeeklyTime(day_of_week=0, start_time=time(15), end_time=time(16))
    for start, end, clash in [(time(14, 30), time(15, 30), True), (time(15), time(16), True),
                              (time(15, 30), time(16, 30), True), (time(14), time(16, 30), True),
                              (time(14), time(15), False), (time(16), time(17), False)]:
        assert overlaps(new, WeeklyTime(day_of_week=0, start_time=start, end_time=end)) is clash
    assert not overlaps(new, WeeklyTime(day_of_week=1, start_time=time(15), end_time=time(16)))


def test_within_window():
    window = WeeklyTime(day_of_week=0, start_time=time(14), end_time=time(18))
    assert within(MON_WED[0], window)
    assert not within(WeeklyTime(day_of_week=0, start_time=time(17), end_time=time(19)), window)


def test_period_bounds():
    wed = date(2026, 10, 14)
    assert period_bounds(BillingPeriod.daily, wed) == (wed, wed)
    assert period_bounds(BillingPeriod.weekly, wed) == (MONDAY, MONDAY + timedelta(days=6))
    assert period_bounds(BillingPeriod.monthly, wed) == (date(2026, 10, 1), date(2026, 10, 31))


def test_weekly_period_covers_the_rest_of_that_week():
    plan = plan_period(MON_WED, BillingPeriod.weekly, MONDAY, None)
    assert [o.lesson_date for o in plan.lessons] == [MONDAY, MONDAY + timedelta(days=2)]
    assert plan.due_at == datetime(2026, 10, 11, 15, tzinfo=WAT)  # 24 h before Monday 15:00


def test_first_lesson_too_soon_moves_to_the_next_one():
    now = datetime(2026, 10, 11, 16, tzinfo=WAT)  # Sunday 16:00: Monday 15:00 is only 23 h away
    not_before = now + timedelta(hours=24)
    plan = plan_period(MON_WED, BillingPeriod.weekly, MONDAY, None, not_before=not_before)
    assert plan.starts_on == MONDAY + timedelta(days=2) and len(plan.lessons) == 1


def test_end_date_cuts_the_period_and_then_stops():
    plan = plan_period(MON_WED, BillingPeriod.monthly, MONDAY, end_date=MONDAY + timedelta(days=7))
    assert plan.ends_on == MONDAY + timedelta(days=7) and len(plan.lessons) == 3
    assert plan_period(MON_WED, BillingPeriod.monthly, MONDAY + timedelta(days=8), MONDAY + timedelta(days=8)) is None
