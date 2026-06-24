"""Test configuration and shared fixtures for UniFi Protect Sensors."""
from __future__ import annotations
import json
from pathlib import Path
import pytest


def load_fixture(filename: str) -> dict:
    """Load a sanitized JSON fixture from tests/fixtures/."""
    fixture_path = Path(__file__).parent / "fixtures" / filename
    with fixture_path.open() as f:
        return json.load(f)
