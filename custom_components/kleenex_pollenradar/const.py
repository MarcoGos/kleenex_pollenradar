"""Constants for the Kleenex pollen radar integration."""

NAME = "Kleenex Pollen Radar"
DOMAIN = "kleenex_pollenradar"
MANUFACTURER = "Kleenex / Scottex"
MODEL = "Pollen radar"

# Platforms
SENSOR = "sensor"
PLATFORMS = [SENSOR]

DEFAULT_SYNC_INTERVAL = 3600  # seconds

REGIONS = {
    "fr": {
        "name": "France",
        "url": "https://www.kleenex.fr/api/sitecore/Pollen/GetPollenContent",
    },
    "it": {
        "name": "Italy",
        "url": "https://www.it.scottex.com/api/sitecore/Pollen/GetPollenContent",
    },
    "nl": {
        "name": "Netherlands",
        "url": "https://www.kleenex.nl/api/sitecore/Pollen/GetPollenContent",
    },
    "uk": {
        "name": "United Kingdom",
        "url": "https://www.kleenex.co.uk/api/sitecore/Pollen/GetPollenContent",
    },
    "us": {
        "name": "United States of America",
        "url": "https://www.kleenex.com/api/sitecore/Pollen/GetPollenContent",
    }
}
CONF_REGION = "region"
