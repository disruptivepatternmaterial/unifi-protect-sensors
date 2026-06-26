"""Unit tests for the Protect WebSocket decoder and deep_merge helper."""
from __future__ import annotations

import json
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest


def _build_frame(obj, *, packet_type: int, payload_format: int = 1, deflate: bool = False) -> bytes:
    """Construct a single Protect WS frame for a Python object."""
    if payload_format == 1:
        payload = json.dumps(obj).encode("utf-8")
    elif payload_format == 2:
        payload = obj.encode("utf-8")
    else:
        payload = obj  # raw bytes
    if deflate:
        payload = zlib.compress(payload)
    header = struct.pack(
        ">BBBBI",
        packet_type,
        payload_format,
        1 if deflate else 0,
        0,
        len(payload),
    )
    return header + payload


def _build_message(action: dict, data: dict, *, deflate_data: bool = False) -> bytes:
    return (
        _build_frame(action, packet_type=1)
        + _build_frame(data, packet_type=2, deflate=deflate_data)
    )


class TestDecodeWSMessage:
    def _import(self):
        from custom_components.unifi_protect_sensors.protect_ws import decode_ws_message
        return decode_ws_message

    def test_decode_basic_update(self):
        decode = self._import()
        action = {"action": "update", "modelKey": "sensor", "id": "abc", "newUpdateId": "u1"}
        data = {"airQuality": {"co2": {"value": 725, "status": "neutral"}}}
        msg = decode(_build_message(action, data))
        assert msg.action == action
        assert msg.data == data

    def test_decode_deflated_data_frame(self):
        decode = self._import()
        action = {"action": "update", "modelKey": "sensor", "id": "xyz"}
        data = {"stats": {"temperature": {"value": 22.5}}, "padding": "x" * 500}
        msg = decode(_build_message(action, data, deflate_data=True))
        assert msg.action["id"] == "xyz"
        assert msg.data["stats"]["temperature"]["value"] == 22.5

    def test_decode_real_captured_headers(self):
        """Mirror the real header shape observed on the controller: (1,1,0,size)/(2,1,0,size)."""
        decode = self._import()
        action = {
            "action": "update",
            "newUpdateId": "259cf52e-bcf3-4fe1-afb5-18189cdd0d37",
            "modelKey": "sensor",
            "id": "6a344e7c004ffe03e413db41",
            "mac": "74F92CA88F38",
            "nvrMac": "74ACB9EEE3FC",
        }
        data = {
            "airQuality": {
                "aqi": {"value": 0, "status": "neutral"},
                "co2": {"value": 725, "status": "neutral"},
                "temperature": {"value": 22.5, "status": "neutral"},
            }
        }
        msg = decode(_build_message(action, data))
        assert msg.action["modelKey"] == "sensor"
        assert msg.data["airQuality"]["co2"]["value"] == 725

    def test_non_dict_data_normalised_to_empty(self):
        decode = self._import()
        action = {"action": "update", "modelKey": "sensor", "id": "abc"}
        msg = decode(
            _build_frame(action, packet_type=1)
            + _build_frame("just a string", packet_type=2, payload_format=2)
        )
        assert msg.data == {}

    def test_truncated_buffer_raises(self):
        decode = self._import()
        with pytest.raises(ValueError):
            decode(b"\x01\x01\x00\x00\x00\x00")  # too short for header

    def test_truncated_payload_raises(self):
        decode = self._import()
        # header claims 100 bytes but none follow
        bad = struct.pack(">BBBBI", 1, 1, 0, 0, 100)
        with pytest.raises(ValueError):
            decode(bad)

    def test_wrong_action_frame_type_raises(self):
        """Frame 1 with packet_type=2 (data) should be rejected."""
        decode = self._import()
        action = {"action": "update", "modelKey": "sensor", "id": "abc"}
        data = {"stats": {"temperature": {"value": 22.5}}}
        # Build message with packet_type=2 for the first frame (wrong)
        bad_action = _build_frame(action, packet_type=2)
        good_data = _build_frame(data, packet_type=2)
        with pytest.raises(ValueError, match="action frame"):
            decode(bad_action + good_data)

    def test_wrong_data_frame_type_raises(self):
        """Frame 2 with packet_type=1 (action) should be rejected."""
        decode = self._import()
        action = {"action": "update", "modelKey": "sensor", "id": "abc"}
        data = {"stats": {"temperature": {"value": 22.5}}}
        good_action = _build_frame(action, packet_type=1)
        bad_data = _build_frame(data, packet_type=1)  # wrong — should be 2
        with pytest.raises(ValueError, match="data frame"):
            decode(good_action + bad_data)

    def test_zlib_size_cap_raises(self):
        """A payload that decompresses beyond the limit should raise ValueError."""
        from custom_components.unifi_protect_sensors.protect_ws import _MAX_DECOMPRESSED_BYTES
        # Build a compressible payload just over the limit
        big = b"A" * (_MAX_DECOMPRESSED_BYTES + 1)
        compressed = zlib.compress(big)
        # Manually build a deflated frame
        header = struct.pack(">BBBBI", 1, 1, 1, 0, len(compressed))
        frame1 = header + compressed
        # Build a minimal valid second frame so decode_ws_message can parse it
        dummy_data = json.dumps({}).encode()
        header2 = struct.pack(">BBBBI", 2, 1, 0, 0, len(dummy_data))
        frame2 = header2 + dummy_data
        from custom_components.unifi_protect_sensors.protect_ws import decode_ws_message
        with pytest.raises(ValueError, match="exceeds"):
            decode_ws_message(frame1 + frame2)


class TestDeepMerge:
    def _import(self):
        from custom_components.unifi_protect_sensors.helpers import deep_merge
        return deep_merge

    def test_top_level_overwrite(self):
        merge = self._import()
        base = {"a": 1, "b": 2}
        assert merge(base, {"b": 3}) == {"a": 1, "b": 3}

    def test_nested_merge_preserves_siblings(self):
        merge = self._import()
        base = {"stats": {"temperature": {"value": 20}, "humidity": {"value": 40}}}
        delta = {"stats": {"temperature": {"value": 22.5}}}
        result = merge(base, delta)
        assert result["stats"]["temperature"]["value"] == 22.5
        assert result["stats"]["humidity"]["value"] == 40

    def test_none_overwrites(self):
        merge = self._import()
        base = {"leakDetectedAt": "2026-01-01T00:00:00Z"}
        assert merge(base, {"leakDetectedAt": None}) == {"leakDetectedAt": None}

    def test_list_overwrites_not_merged(self):
        merge = self._import()
        base = {"ids": [1, 2, 3]}
        assert merge(base, {"ids": [9]}) == {"ids": [9]}

    def test_new_nested_key_added(self):
        merge = self._import()
        base = {"airQuality": {"co2": {"value": 400}}}
        delta = {"airQuality": {"voc": {"value": 100}}}
        result = merge(base, delta)
        assert result["airQuality"]["co2"]["value"] == 400
        assert result["airQuality"]["voc"]["value"] == 100

    def test_returns_same_base_object(self):
        merge = self._import()
        base = {"a": 1}
        assert merge(base, {"b": 2}) is base
