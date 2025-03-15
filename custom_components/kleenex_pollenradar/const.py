"""Constants for the Kleenex pollen radar integration.

This module contains all constants used by the integration, including:
- Basic integration information
- API endpoints and configuration
- Region definitions and settings
- Update intervals and timeouts
- Plant type classifications
- Translations and error messages
"""

#######################
# Integration Basics  #
#######################

# Core integration information
NAME = "Kleenex Pollen Radar"
DEFAULT_NAME = "Pollen"  # Default name for the integration
DOMAIN = "kleenex_pollenradar"
VERSION = "1.0.0"

# Manufacturer information
MANUFACTURER = "Kleenex / Scottex / DWD"
MODEL = "Pollen radar"

# Platform configuration
SENSOR = "sensor"
PLATFORMS = [SENSOR]

######################
# Update Intervals   #
######################

# Default update interval for Kleenex API (1 hour)
DEFAULT_SYNC_INTERVAL = 3600  # seconds
MIN_UPDATE_INTERVAL = 60  # minimum 1 minute

######################
# DWD API Settings  #
######################

# API endpoint and region configuration
DWD_API_URL = "https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json"
DWD_REGION_ID = 81  # Tiefland Sachsen (Dresden)
DWD_REQUEST_TIMEOUT = 10  # seconds

# DWD specific information
DWD_MANUFACTURER = "Deutscher Wetterdienst (DWD)"
DWD_MODEL = "Pollenflug-Gefahrenindex"
DWD_UPDATE_INTERVAL = 3600  # DWD updates data every hour
DWD_TIMEZONE = "Europe/Berlin"

# Plant classifications for DWD data
DWD_TREE_PLANTS = {
    "Erle",   # Alder
    "Hasel",  # Hazel
    "Birke",  # Birch
    "Esche"   # Ash
}

DWD_GRASS_PLANTS = {
    "Gräser",  # Grasses
    "Roggen"   # Rye
}

DWD_WEED_PLANTS = {
    "Ambrosia",  # Ragweed
    "Beifuß"     # Mugwort
}

# DWD forecast day keys and translations
DWD_FORECAST_DAYS = ["today", "tomorrow", "dayafter_to"]
DWD_DAY_NAMES = {
    "today": "heute",
    "tomorrow": "morgen",
    "dayafter_to": "übermorgen"
}

# DWD pollen level values
DWD_LEVEL_NO_DATA = -1.0
DWD_LEVEL_NONE = 0.0
DWD_LEVEL_NONE_TO_LOW = 0.5
DWD_LEVEL_LOW = 1.0
DWD_LEVEL_LOW_TO_MEDIUM = 1.5
DWD_LEVEL_MEDIUM = 2.0
DWD_LEVEL_MEDIUM_TO_HIGH = 2.5
DWD_LEVEL_HIGH = 3.0

# DWD pollen level mapping
DWD_LEVEL_MAPPING = {
    "-1": DWD_LEVEL_NO_DATA,     # keine Angabe
    "0": DWD_LEVEL_NONE,         # keine Belastung
    "0-1": DWD_LEVEL_NONE_TO_LOW,  # keine bis geringe Belastung
    "1": DWD_LEVEL_LOW,          # geringe Belastung
    "1-2": DWD_LEVEL_LOW_TO_MEDIUM,  # geringe bis mittlere Belastung
    "2": DWD_LEVEL_MEDIUM,       # mittlere Belastung
    "2-3": DWD_LEVEL_MEDIUM_TO_HIGH,  # mittlere bis hohe Belastung
    "3": DWD_LEVEL_HIGH          # hohe Belastung
}

# DWD pollen level labels
DWD_LEVEL_LABELS = {
    DWD_LEVEL_NO_DATA: "Keine Angabe",
    DWD_LEVEL_NONE: "Keine Belastung",
    DWD_LEVEL_NONE_TO_LOW: "Keine bis geringe Belastung",
    DWD_LEVEL_LOW: "Geringe Belastung",
    DWD_LEVEL_LOW_TO_MEDIUM: "Geringe bis mittlere Belastung",
    DWD_LEVEL_MEDIUM: "Mittlere Belastung",
    DWD_LEVEL_MEDIUM_TO_HIGH: "Mittlere bis hohe Belastung",
    DWD_LEVEL_HIGH: "Hohe Belastung"
}

######################
# Region Settings   #
######################

# Available regions with their configurations
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
    },
    "de": {
        "name": "Germany (Dresden)",
        "url": DWD_API_URL,
        "region_id": DWD_REGION_ID,
        "manufacturer": DWD_MANUFACTURER,
        "model": DWD_MODEL,
        "update_interval": DWD_UPDATE_INTERVAL,
        "timezone": DWD_TIMEZONE,
    }
}

######################
# Configuration     #
######################

# Configuration keys
CONF_REGION = "region"

# Error messages
ERROR_MESSAGES = {
    "cannot_connect": "Verbindung zum API-Server nicht möglich",
    "invalid_auth": "Authentifizierung fehlgeschlagen",
    "unknown": "Unbekannter Fehler aufgetreten",
    "no_data": "Keine Daten verfügbar",
    "invalid_region": "Ungültige Region",
    "timeout": "Zeitüberschreitung bei der Anfrage",
    "parse_error": "Fehler beim Verarbeiten der Daten"
}
