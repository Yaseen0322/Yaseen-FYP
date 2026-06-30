from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings


def app_timezone():
    try:
        return ZoneInfo(settings.DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError:
        return timezone.utc


def utc_today():
    return datetime.now(app_timezone()).date()


def as_utc(value: datetime) -> datetime:
    """
    Normalize datetimes to UTC. SQLite drops tzinfo for aware values, while
    the desktop agent sends ISO UTC timestamps, so naive DB values are treated
    as UTC rather than local server time.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def to_app_timezone(value: datetime) -> datetime:
    return as_utc(value).astimezone(app_timezone())


def app_day_bounds_utc(target_date: date) -> tuple[datetime, datetime]:
    start_local = datetime.combine(target_date, time.min, tzinfo=app_timezone())
    end_local = start_local.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
