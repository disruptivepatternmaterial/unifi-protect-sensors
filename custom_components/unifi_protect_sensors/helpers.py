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


def field_exists(data: dict, path: str) -> bool:
    """Return True if the dot-separated key path exists in data (value may be None)."""
    keys = path.split(".")
    cur: Any = data
    for key in keys[:-1]:
        if not isinstance(cur, dict) or key not in cur:
            return False
        cur = cur[key]
    return isinstance(cur, dict) and keys[-1] in cur


def deep_merge(base: dict, delta: dict) -> dict:
    """Recursively merge ``delta`` into ``base`` in place and return ``base``.

    Nested dicts are merged key-by-key; any non-dict value in ``delta`` (including
    None and lists) overwrites the corresponding value in ``base``. This mirrors
    how UniFi Protect WebSocket deltas patch a device snapshot.
    """
    for key, value in delta.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base
