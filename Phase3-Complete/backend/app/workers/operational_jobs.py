"""
Run alert processing jobs outside the API server.

Usage:
    python -m app.workers.operational_jobs --once
    python -m app.workers.operational_jobs --interval 300
"""
from __future__ import annotations

import argparse
import asyncio

from app.core.database import SessionLocal, verify_schema_up_to_date
from app.services.runtime_jobs import process_all_alert_orgs


async def run_once() -> list[dict]:
    verify_schema_up_to_date()
    db = SessionLocal()
    try:
        return await process_all_alert_orgs(db)
    finally:
        db.close()


async def run_forever(interval: int) -> None:
    while True:
        results = await run_once()
        total_created = sum(item["created_count"] for item in results)
        print(f"Processed alert jobs for {len(results)} orgs; created {total_created} alerts")
        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run background alert processing jobs")
    parser.add_argument("--once", action="store_true", help="Process one cycle and exit")
    parser.add_argument("--interval", type=int, default=300, help="Polling interval in seconds")
    args = parser.parse_args()

    if args.once:
        results = asyncio.run(run_once())
        total_created = sum(item["created_count"] for item in results)
        print(f"Processed alert jobs for {len(results)} orgs; created {total_created} alerts")
        return

    asyncio.run(run_forever(args.interval))


if __name__ == "__main__":
    main()
