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


def device_type_matches(device_type: str, expected_source: str) -> bool:
    """Return True if ``device_type`` is one of the comma-separated expected sources.

    An empty ``expected_source`` matches every device (used for metrics that exist
    on all device types). Matching is case-insensitive and exact against Protect's
    model identifier (the device ``type`` field, e.g. ``"USL-Environmental-US"``).

    Exact matching is deliberate: a blank or unknown ``device_type`` matches nothing
    (so unrecognised devices get no entities rather than all of them), and partial
    overlaps between model names cannot cross-match.
    """
    sources = [s.strip().lower() for s in expected_source.split(",") if s.strip()]
    if not sources:
        return True
    return device_type.strip().lower() in sources


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
