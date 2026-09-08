"""Constants for UniFi Protect Sensors."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "unifi_protect_sensors"

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

MANUFACTURER = "Ubiquiti"

# Protect model identifiers, as reported in a device's bootstrap ``type`` field.
MODEL_UFP_SENSE = "UFP-SENSE"
MODEL_USL_ENVIRONMENTAL = "USL-Environmental-US"
MODEL_USL_ENTRY = "USL-Entry-US"
MODEL_UP_AIRQUALITY = "UP-AirQuality"

# Devices that report environmental readings under ``stats.*``.
ENVIRONMENTAL_MODELS = (MODEL_UFP_SENSE, MODEL_USL_ENVIRONMENTAL)
# Every battery-powered model. Wired devices report a null percentage and are
# excluded by the payload-field check instead.
BATTERY_MODELS = (MODEL_UFP_SENSE, MODEL_USL_ENVIRONMENTAL, MODEL_USL_ENTRY)

# A device reporting this state is offline; its entities go unavailable.
STATE_DISCONNECTED = "DISCONNECTED"

# Config entry keys — not duplicating homeassistant.const; these are our own
# storage keys so they are explicit here regardless of HA's constant values.
CONF_API_KEY = "api_key"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_PORT = 443
# UniFi devices use self-signed certs; users may enable verification via options flow
DEFAULT_VERIFY_SSL = False

# Protect console API paths (shared by the coordinator and the config flow so
# validation hits the same endpoints the integration uses at runtime).
LOGIN_PATH = "/api/auth/login"
BOOTSTRAP_PATH = "/proxy/protect/api/bootstrap"
WS_PATH = "/proxy/protect/ws/updates"
