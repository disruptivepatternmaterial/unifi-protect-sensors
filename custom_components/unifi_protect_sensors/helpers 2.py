"""Shared helpers for UniFi Protect Sensors."""

from __future__ import annotations

from typing import Any


def get_nested(data: dict, path: str) -> Any | None:
    """Walk a dot-separated path into a nested dict, returning None on any missing key."""
    cur: Any = data
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur
