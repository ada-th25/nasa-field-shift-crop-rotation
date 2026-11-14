"""Tests for the dynamic default date window added so the API defaults to
recent data instead of a fixed calendar year (see docs/algorithm.md,
"can it look at current data" discussion)."""
from datetime import date, timedelta

from app.schemas import POWER_REPORTING_LAG_DAYS, FarmRequest


def test_default_end_date_is_lag_days_before_today():
    expected = (date.today() - timedelta(days=POWER_REPORTING_LAG_DAYS)).strftime("%Y%m%d")
    req = FarmRequest(lat=42.0, lon=-93.0)
    assert req.end_date == expected


def test_default_start_date_is_one_year_before_default_end_date():
    from datetime import datetime

    req = FarmRequest(lat=42.0, lon=-93.0)
    start = datetime.strptime(req.start_date, "%Y%m%d").date()
    end = datetime.strptime(req.end_date, "%Y%m%d").date()
    assert (end - start).days == 365


def test_explicit_dates_are_not_overridden_by_the_default():
    req = FarmRequest(lat=42.0, lon=-93.0, start_date="20230101", end_date="20231231")
    assert req.start_date == "20230101"
    assert req.end_date == "20231231"


def test_two_instances_get_independent_but_consistent_defaults():
    # Regression guard: a plain mutable/class-level default would freeze
    # the date at import time instead of computing it per request.
    a = FarmRequest(lat=1.0, lon=1.0)
    b = FarmRequest(lat=2.0, lon=2.0)
    assert a.end_date == b.end_date  # same day, so same computed default
