DOMAIN = "solark"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PLANT_ID = "plant_id"
CONF_BASE_URL = "base_url"
CONF_API_URL = "api_url"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ALLOW_WRITE = "allow_write_access"

DEFAULT_BASE_URL = "https://www.mysolark.com"
DEFAULT_API_URL = "https://p2.api.solarkcloud.com"
# Older API host. Still serves reads, but writes to /common/setting/{sn}/set
# now fail (HTTP 500 / code=1) once an account is migrated to the p2 cluster.
# Existing config entries pointing here are migrated to DEFAULT_API_URL (v4).
LEGACY_API_URLS = ("https://ecsprod-api-new.solarkcloud.com",)
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_ALLOW_WRITE = False

PLATFORMS = ["sensor"]
