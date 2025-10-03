"""Constants for the Kleenex pollen radar integration."""

from enum import Enum

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
        "url": "https://www.kleenex.fr/api/sitecore/Pollen/",
        "method": "get",
    },
    "it": {
        "name": "Italy",
        "url": "https://www.it.scottex.com/api/sitecore/Pollen/",
        "method": "post",
    },
    "nl": {
        "name": "Netherlands",
        "url": "https://www.kleenex.nl/api/sitecore/Pollen/",
        "method": "get",
    },
    "uk": {
        "name": "United Kingdom",
        "url": "https://www.kleenex.co.uk/api/sitecore/Pollen/",
        "method": "get",
    },
    "us": {
        "name": "United States of America",
        "url": "https://www.kleenex.com/api/sitecore/Pollen/",
        "method": "get",
    },
}
CONF_REGION = "region"
CONF_GET_CONTENT_BY = "get_content_by"
CONF_NAME = "name"
CONF_CITY = "city"
RETRY_ATTEMPTS = 5


class GetContentBy(Enum):
    """Get content by."""

    CITY = "city"
    LAT_LNG = "lat_lng"


METHODS = {
    GetContentBy.CITY: "GetPollenContentCity",
    GetContentBy.LAT_LNG: "GetPollenContent",
}
