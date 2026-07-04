"""
Rebuild persisted daily summaries from raw activity, idle, presence, and browser records.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.core.dates import to_app_timezone
from app.models.activity import AppUsage, IdleInterval
from app.models.browser_usage import BrowserUsage
from app.models.presence import PresenceInterval
from app.services.reporting import refresh_daily_summaries


TRACKED_MODELS = (AppUsage, IdleInterval, PresenceInterval, BrowserUsage)


def record_dates(record):
    start_date = to_app_timezone(record.start_ts).date()
    end_date = to_app_timezone(record.end_ts).date()
    current = start_date
    while current <= end_date:
        yield current
        current = current.fromordinal(current.toordinal() + 1)


def main():
    db = SessionLocal()
    try:
        dates_by_user = {}
        for model in TRACKED_MODELS:
            for record in db.query(model).all():
                user_dates = dates_by_user.setdefault(record.user_id, set())
                user_dates.update(record_dates(record))

        rebuilt = 0
        for user_id, dates in sorted(dates_by_user.items()):
            refresh_daily_summaries(db, user_id, dates)
            rebuilt += len(dates)

        db.commit()
        print(f"Rebuilt daily summaries for {len(dates_by_user)} users across {rebuilt} user-days.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
