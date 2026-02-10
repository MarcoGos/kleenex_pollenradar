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


class Regions(Enum):
    """Supported regions."""

    FRANCE = "fr"
    ITALY = "it"
    NETHERLANDS = "nl"
    UNITED_KINGDOM = "uk"
    UNITED_STATES = "us"


REGIONS = {
    Regions.FRANCE.value: {
        "name": "France",
        "url": "https://www.kleenex.fr/api/sitecore/Pollen/",
        "method": "get",
    },
    Regions.ITALY.value: {
        "name": "Italy",
        "url": "https://www.it.scottex.com/api/sitecore/Pollen/",
        "method": "post",
    },
    Regions.NETHERLANDS.value: {
        "name": "Netherlands",
        "url": "https://www.kleenex.nl/api/sitecore/Pollen/",
        "method": "get",
    },
    Regions.UNITED_KINGDOM.value: {
        "name": "United Kingdom",
        "url": "https://www.kleenex.co.uk/api/sitecore/Pollen/",
        "method": "get",
    },
    Regions.UNITED_STATES.value: {
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
    CITY_ITALY = "city_italy"


METHODS = {
    GetContentBy.CITY: "GetPollenContentCity",
    GetContentBy.CITY_ITALY: "GetPollenData",
}
