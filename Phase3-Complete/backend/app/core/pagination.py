"""
Pagination helpers for consistent limit/offset API responses.
"""


def build_paginated_response(items, total: int, limit: int, offset: int) -> dict:
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
