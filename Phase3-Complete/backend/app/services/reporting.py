"""
Shared reporting helpers for clipped daily summaries and timelines.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, List, Sequence, Tuple

from sqlalchemy.orm import Session

from app.core.dates import app_day_bounds_utc, as_utc, to_app_timezone
from app.models.activity import AppUsage, IdleInterval
from app.models.browser_usage import BrowserUsage
from app.models.daily_summary import DailySummary
from app.models.presence import PresenceInterval
from app.services.ml_classifier import classify_app_by_patterns

Interval = Tuple[datetime, datetime]


def get_day_bounds(target_date: date) -> Tuple[datetime, datetime]:
    return app_day_bounds_utc(target_date)


def _db_query_ts(db: Session, value: datetime) -> datetime:
    utc_value = as_utc(value)
    if db.bind and db.bind.dialect.name == "sqlite":
        return utc_value.replace(tzinfo=None)
    return utc_value


def _clip_interval(
    start_ts: datetime,
    end_ts: datetime,
    range_start: datetime,
    range_end: datetime,
) -> Interval | None:
    start = max(as_utc(start_ts), as_utc(range_start))
    end = min(as_utc(end_ts), as_utc(range_end))
    if end <= start:
        return None
    return start, end


def _duration_seconds(interval: Interval) -> int:
    return int((interval[1] - interval[0]).total_seconds())


def _merge_intervals(intervals: Sequence[Interval]) -> List[Interval]:
    if not intervals:
        return []

    ordered = sorted(intervals, key=lambda item: item[0])
    merged: List[Interval] = [ordered[0]]

    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


def _subtract_intervals(base_intervals: Sequence[Interval], subtract_intervals: Sequence[Interval]) -> List[Interval]:
    if not base_intervals:
        return []
    if not subtract_intervals:
        return list(base_intervals)

    subtracts = _merge_intervals(subtract_intervals)
    result: List[Interval] = []

    for base_start, base_end in base_intervals:
        cursor = base_start
        for subtract_start, subtract_end in subtracts:
            if subtract_end <= cursor:
                continue
            if subtract_start >= base_end:
                break
            if subtract_start > cursor:
                result.append((cursor, min(subtract_start, base_end)))
            cursor = max(cursor, subtract_end)
            if cursor >= base_end:
                break
        if cursor < base_end:
            result.append((cursor, base_end))

    return result


def _sum_intervals(intervals: Iterable[Interval]) -> int:
    return sum(_duration_seconds(interval) for interval in intervals)


def _get_overlapping_records(db: Session, model, user_id: int, range_start: datetime, range_end: datetime):
    return db.query(model).filter(
        model.user_id == user_id,
        model.start_ts < _db_query_ts(db, range_end),
        model.end_ts > _db_query_ts(db, range_start),
    ).order_by(model.start_ts).all()


def build_daily_summary_payload(db: Session, user_id: int, target_date: date) -> dict:
    range_start, range_end = get_day_bounds(target_date)

    app_records = _get_overlapping_records(db, AppUsage, user_id, range_start, range_end)
    idle_records = _get_overlapping_records(db, IdleInterval, user_id, range_start, range_end)
    presence_records = _get_overlapping_records(db, PresenceInterval, user_id, range_start, range_end)
    browser_records = _get_overlapping_records(db, BrowserUsage, user_id, range_start, range_end)

    app_intervals: List[Interval] = []
    app_productivity_candidates: list[tuple[str, Interval]] = []
    idle_intervals: List[Interval] = []
    presence_by_state = defaultdict(list)
    productivity_by_label = defaultdict(list)
    top_apps = defaultdict(int)
    top_domains = defaultdict(int)
    activity_starts: List[datetime] = []
    activity_ends: List[datetime] = []

    for record in app_records:
        interval = _clip_interval(record.start_ts, record.end_ts, range_start, range_end)
        if not interval:
            continue
        duration_sec = _duration_seconds(interval)
        if duration_sec <= 0:
            continue
        app_intervals.append(interval)
        app_productivity_candidates.append((record.app_name, interval))
        top_apps[record.app_name] += duration_sec
        activity_starts.append(interval[0])
        activity_ends.append(interval[1])

    for record in idle_records:
        interval = _clip_interval(record.start_ts, record.end_ts, range_start, range_end)
        if not interval:
            continue
        idle_intervals.append(interval)
        activity_starts.append(interval[0])
        activity_ends.append(interval[1])

    for record in presence_records:
        interval = _clip_interval(record.start_ts, record.end_ts, range_start, range_end)
        if not interval:
            continue
        presence_by_state[record.state].append(interval)
        activity_starts.append(interval[0])
        activity_ends.append(interval[1])

    for record in browser_records:
        interval = _clip_interval(record.start_ts, record.end_ts, range_start, range_end)
        if not interval:
            continue
        duration_sec = _duration_seconds(interval)
        if duration_sec <= 0:
            continue
        label = record.label or "neutral"
        productivity_by_label[label].append(interval)
        top_domains[(record.domain, record.category, label)] += duration_sec
        activity_starts.append(interval[0])
        activity_ends.append(interval[1])

    merged_app_intervals = _merge_intervals(app_intervals)
    merged_idle_intervals = _merge_intervals(idle_intervals)

    focus_sec = _sum_intervals(
        _subtract_intervals(merged_app_intervals, merged_idle_intervals)
    )

    for app_name, interval in app_productivity_candidates:
        _category, label, _confidence = classify_app_by_patterns(app_name or "")
        active_intervals = _subtract_intervals([interval], merged_idle_intervals)
        if active_intervals:
            productivity_by_label[label].extend(active_intervals)

    idle_sec = _sum_intervals(merged_idle_intervals)
    present_sec = _sum_intervals(_merge_intervals(presence_by_state.get("present", [])))
    absent_sec = _sum_intervals(_merge_intervals(presence_by_state.get("absent", [])))
    camera_off_sec = _sum_intervals(_merge_intervals(presence_by_state.get("camera_off", [])))
    productive_sec = _sum_intervals(_merge_intervals(productivity_by_label.get("productive", [])))
    unproductive_sec = _sum_intervals(_merge_intervals(productivity_by_label.get("unproductive", [])))
    neutral_sec = _sum_intervals(_merge_intervals(productivity_by_label.get("neutral", [])))

    top_apps_payload = [
        {"app_name": app_name, "duration_sec": duration_sec}
        for app_name, duration_sec in sorted(
            top_apps.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:10]
    ]
    top_domains_payload = [
        {
            "domain": domain,
            "category": category,
            "label": label,
            "duration_sec": duration_sec,
        }
        for (domain, category, label), duration_sec in sorted(
            top_domains.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:10]
    ]

    return {
        "user_id": user_id,
        "date": target_date,
        "focus_sec": focus_sec,
        "idle_sec": idle_sec,
        "present_sec": present_sec,
        "absent_sec": absent_sec,
        "camera_off_sec": camera_off_sec,
        "productive_sec": productive_sec,
        "unproductive_sec": unproductive_sec,
        "neutral_sec": neutral_sec,
        "top_apps": top_apps_payload,
        "top_domains": top_domains_payload,
        "first_activity": min(activity_starts) if activity_starts else None,
        "last_activity": max(activity_ends) if activity_ends else None,
    }


def build_daily_summary_response(db: Session, user_id: int, target_date: date) -> dict:
    payload = build_daily_summary_payload(db, user_id, target_date)
    return {
        "user_id": user_id,
        "date": target_date.isoformat(),
        "focus_sec": payload["focus_sec"],
        "idle_sec": payload["idle_sec"],
        "present_sec": payload["present_sec"],
        "absent_sec": payload["absent_sec"],
        "camera_off_sec": payload["camera_off_sec"],
        "productive_sec": payload["productive_sec"],
        "unproductive_sec": payload["unproductive_sec"],
        "neutral_sec": payload["neutral_sec"],
        "top_apps": payload["top_apps"],
        "top_domains": payload["top_domains"],
    }


def build_timeline_blocks(db: Session, user_id: int, target_date: date) -> list[dict]:
    range_start, range_end = get_day_bounds(target_date)
    blocks = []

    for record in _get_overlapping_records(db, PresenceInterval, user_id, range_start, range_end):
        interval = _clip_interval(record.start_ts, record.end_ts, range_start, range_end)
        if not interval:
            continue
        blocks.append({
            "type": record.state,
            "start_ts": to_app_timezone(interval[0]),
            "end_ts": to_app_timezone(interval[1]),
            "duration_sec": _duration_seconds(interval),
            "details": None,
        })

    for record in _get_overlapping_records(db, IdleInterval, user_id, range_start, range_end):
        interval = _clip_interval(record.start_ts, record.end_ts, range_start, range_end)
        if not interval:
            continue
        blocks.append({
            "type": "idle",
            "start_ts": to_app_timezone(interval[0]),
            "end_ts": to_app_timezone(interval[1]),
            "duration_sec": _duration_seconds(interval),
            "details": None,
        })

    for record in _get_overlapping_records(db, AppUsage, user_id, range_start, range_end):
        interval = _clip_interval(record.start_ts, record.end_ts, range_start, range_end)
        if not interval:
            continue
        blocks.append({
            "type": "app_usage",
            "start_ts": to_app_timezone(interval[0]),
            "end_ts": to_app_timezone(interval[1]),
            "duration_sec": _duration_seconds(interval),
            "details": {"app_name": record.app_name},
        })

    for record in _get_overlapping_records(db, BrowserUsage, user_id, range_start, range_end):
        interval = _clip_interval(record.start_ts, record.end_ts, range_start, range_end)
        if not interval:
            continue
        blocks.append({
            "type": "browser_usage",
            "start_ts": to_app_timezone(interval[0]),
            "end_ts": to_app_timezone(interval[1]),
            "duration_sec": _duration_seconds(interval),
            "details": {
                "domain": record.domain,
                "category": record.category,
                "label": record.label,
            },
        })

    blocks = _coalesce_timeline_blocks(_dedupe_timeline_blocks(blocks))
    blocks.sort(key=lambda item: item["start_ts"], reverse=True)
    return blocks


def _dedupe_timeline_blocks(blocks: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for block in blocks:
        details = block.get("details") or {}
        details_key = tuple(sorted(details.items()))
        key = (
            block["type"],
            as_utc(block["start_ts"]),
            as_utc(block["end_ts"]),
            block["duration_sec"],
            details_key,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(block)
    return deduped


def _timeline_details_key(block: dict) -> tuple:
    details = block.get("details") or {}
    return tuple(sorted(details.items()))


def _coalesce_timeline_blocks(blocks: list[dict], max_gap_seconds: int = 3) -> list[dict]:
    if not blocks:
        return []

    ordered = sorted(blocks, key=lambda item: as_utc(item["start_ts"]))
    buckets: dict[tuple, list[dict]] = {}

    for block in ordered:
        bucket_key = (block["type"], _timeline_details_key(block))
        bucket = buckets.setdefault(bucket_key, [])

        if not bucket:
            bucket.append(dict(block))
            continue

        last = bucket[-1]
        gap_seconds = (as_utc(block["start_ts"]) - as_utc(last["end_ts"])).total_seconds()

        if gap_seconds <= max_gap_seconds:
            if as_utc(block["end_ts"]) > as_utc(last["end_ts"]):
                last["end_ts"] = block["end_ts"]
            last["duration_sec"] = _duration_seconds((
                as_utc(last["start_ts"]),
                as_utc(last["end_ts"]),
            ))
        else:
            bucket.append(dict(block))

    return [block for bucket in buckets.values() for block in bucket]


def upsert_daily_summary(db: Session, user_id: int, target_date: date) -> DailySummary:
    payload = build_daily_summary_payload(db, user_id, target_date)

    summary = db.query(DailySummary).filter(
        DailySummary.user_id == user_id,
        DailySummary.date == target_date,
    ).first()

    if not summary:
        summary = DailySummary(user_id=user_id, date=target_date)
        db.add(summary)

    summary.focus_sec = payload["focus_sec"]
    summary.idle_sec = payload["idle_sec"]
    summary.present_sec = payload["present_sec"]
    summary.absent_sec = payload["absent_sec"]
    summary.camera_off_sec = payload["camera_off_sec"]
    summary.productive_sec = payload["productive_sec"]
    summary.unproductive_sec = payload["unproductive_sec"]
    summary.neutral_sec = payload["neutral_sec"]
    summary.top_apps_json = payload["top_apps"]
    summary.top_domains_json = payload["top_domains"]
    summary.first_activity = payload["first_activity"]
    summary.last_activity = payload["last_activity"]
    return summary


def refresh_daily_summaries(db: Session, user_id: int, target_dates: Iterable[date]) -> None:
    for target_date in sorted(set(target_dates)):
        upsert_daily_summary(db, user_id, target_date)
