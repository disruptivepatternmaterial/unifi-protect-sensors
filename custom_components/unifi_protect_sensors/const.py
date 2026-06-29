"""Constants for UniFi Protect Sensors."""

from __future__ import annotations

DOMAIN = "unifi_protect_sensors"

PLATFORMS = ["sensor", "binary_sensor"]

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
