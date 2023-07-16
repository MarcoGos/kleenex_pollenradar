"""Constants for the Kleenex pollenradar integration."""

NAME = "Kleenex pollenradar"
DOMAIN = "kleenex_pollenradar"
MANUFACTURER = "Kleenex"
MODEL = "Pollenradar"

# Platforms
SENSOR = "sensor"
PLATFORMS = [SENSOR]

DEFAULT_SYNC_INTERVAL = 3600  # seconds

REGIONS = {
    "nl": {
        "name": "Netherlands",
        "url": "https://www.kleenex.nl/api/sitecore/Pollen/GetPollenContent",
    },
    "uk": {
        "name": "United Kingdom",
        "url": "https://www.kleenex.co.uk/api/sitecore/Pollen/GetPollenContent",
    },
    "fr": {
        "name": "France",
        "url": "https://www.kleenex.fr/api/sitecore/Pollen/GetPollenContent",
    }
}
CONF_REGION = "region"
