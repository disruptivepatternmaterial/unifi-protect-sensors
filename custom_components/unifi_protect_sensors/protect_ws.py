"""Decoder for the UniFi Protect WebSocket event stream.

Protect streams device changes over ``/proxy/protect/ws/updates`` as binary
frames. Every WebSocket message is composed of two consecutive frames:

* an **action** frame describing what changed (model, id, action), and
* a **data** frame carrying the changed fields (a partial delta).

Each frame is prefixed with an 8-byte header::

    byte 0   packet type      1 = action frame, 2 = data frame
    byte 1   payload format   1 = JSON, 2 = UTF-8 string, 3 = raw buffer
    byte 2   deflated         1 = zlib-compressed payload, 0 = plain
    byte 3   position         frame position marker (unused here)
    byte 4-7 payload size     big-endian uint32 byte length of the payload

This module has no Home Assistant dependencies so it can be unit-tested in
isolation.
"""

from __future__ import annotations

import json
import struct
import zlib
from typing import Any, NamedTuple

_HEADER_LEN = 8

# Safety cap on decompressed frame size (10 MB). Prevents memory amplification
# attacks if a compromised LAN host sends a crafted zlib bomb.
_MAX_DECOMPRESSED_BYTES = 10 * 1024 * 1024

# Packet type markers (header byte 0)
PACKET_TYPE_ACTION = 1
PACKET_TYPE_PAYLOAD = 2

# Payload format markers (header byte 1)
PAYLOAD_FORMAT_JSON = 1
PAYLOAD_FORMAT_UTF8 = 2
PAYLOAD_FORMAT_BUFFER = 3


class ProtectFrame(NamedTuple):
    """A single decoded WebSocket frame."""

    packet_type: int
    payload_format: int
    deflated: bool
    payload: bytes


class ProtectWSMessage(NamedTuple):
    """A decoded WebSocket message (action + data)."""

    action: dict[str, Any]
    data: dict[str, Any]


def _decode_frame(buffer: bytes, offset: int) -> tuple[ProtectFrame, int]:
    """Decode a single frame starting at ``offset``; return it and the next offset."""
    if len(buffer) < offset + _HEADER_LEN:
        raise ValueError("Buffer too small for frame header")

    packet_type = buffer[offset]
    payload_format = buffer[offset + 1]
    deflated = bool(buffer[offset + 2])
    size = struct.unpack(">I", buffer[offset + 4 : offset + 8])[0]

    start = offset + _HEADER_LEN
    end = start + size
    if len(buffer) < end:
        raise ValueError("Buffer too small for frame payload")

    payload = buffer[start:end]
    if deflated:
        dec = zlib.decompressobj()
        try:
            payload = dec.decompress(payload, _MAX_DECOMPRESSED_BYTES)
        except zlib.error as err:
            raise ValueError(f"Malformed deflate payload: {err}") from err
        if dec.unconsumed_tail:
            raise ValueError(
                f"Decompressed frame exceeds {_MAX_DECOMPRESSED_BYTES // (1024 * 1024)} MB limit"
            )
        if not dec.eof:
            # Stream ended before the deflate end-of-stream marker — a truncated
            # or malformed compressed payload.
            raise ValueError("Incomplete deflate stream in frame payload")

    return ProtectFrame(packet_type, payload_format, deflated, payload), end


def _payload_to_obj(frame: ProtectFrame) -> Any:
    """Convert a frame payload to a Python object based on its format byte."""
    if frame.payload_format == PAYLOAD_FORMAT_JSON:
        return json.loads(frame.payload)
    if frame.payload_format == PAYLOAD_FORMAT_UTF8:
        return frame.payload.decode("utf-8")
    return frame.payload


def decode_ws_message(buffer: bytes) -> ProtectWSMessage:
    """Decode a full Protect WebSocket binary message into action + data dicts.

    Raises ``ValueError`` if the buffer does not contain a well-formed
    action frame followed by a data frame.
    """
    action_frame, offset = _decode_frame(buffer, 0)
    data_frame, _ = _decode_frame(buffer, offset)

    if action_frame.packet_type != PACKET_TYPE_ACTION:
        raise ValueError(
            f"Expected action frame (type {PACKET_TYPE_ACTION}), got type {action_frame.packet_type}"
        )
    if data_frame.packet_type != PACKET_TYPE_PAYLOAD:
        raise ValueError(
            f"Expected data frame (type {PACKET_TYPE_PAYLOAD}), got type {data_frame.packet_type}"
        )

    action = _payload_to_obj(action_frame)
    data = _payload_to_obj(data_frame)

    if not isinstance(action, dict):
        raise ValueError("Action frame did not decode to an object")
    if not isinstance(data, dict):
        # Some frames (e.g. UTF-8 strings) legitimately are not dicts; callers
        # only care about dict deltas, so normalise to an empty mapping.
        data = {}

    return ProtectWSMessage(action=action, data=data)
