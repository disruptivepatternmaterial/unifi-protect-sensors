"""Constants for UniFi Protect Sensors."""

from __future__ import annotations

DOMAIN = "unifi_protect_sensors"

PLATFORMS = ["sensor", "binary_sensor"]

CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_API_KEY = "api_key"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_PORT = 443
DEFAULT_VERIFY_SSL = False

ATTR_PAYLOAD_FIELD = "payload_field"

