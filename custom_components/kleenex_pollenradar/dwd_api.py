"""DWD (Deutscher Wetterdienst) API client for pollen data.

This module handles the communication with the DWD pollen forecast API.
It provides functions to fetch and process pollen data for the Dresden region.

The DWD API provides pollen forecasts for three days:
- today
- tomorrow
- day after tomorrow

The pollen levels are provided as strings and converted to numeric values:
-1.0 = keine Angabe (no data)
0.0 = keine Belastung (no load)
0.5 = keine bis geringe Belastung (no to low load)
1.0 = geringe Belastung (low load)
1.5 = geringe bis mittlere Belastung (low to medium load)
2.0 = mittlere Belastung (medium load)
2.5 = mittlere bis hohe Belastung (medium to high load)
3.0 = hohe Belastung (high load)
"""
import logging
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import aiohttp
import async_timeout

from .const import (
    DWD_API_URL,
    DWD_REGION_ID,
    DWD_TREE_PLANTS,
    DWD_GRASS_PLANTS,
    DWD_WEED_PLANTS,
    DWD_FORECAST_DAYS,
    DWD_DAY_NAMES,
    DWD_TIMEZONE,
    DWD_LEVEL_MAPPING,
    DWD_LEVEL_LABELS,
    DWD_LEVEL_NONE,
    DWD_REQUEST_TIMEOUT,
    ERROR_MESSAGES,
)

_LOGGER = logging.getLogger(__name__)

class DWDApiError(Exception):
    """DWD API specific errors."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """Initialize the error with a message and optional original error."""
        super().__init__(message)
        self.original_error = original_error

def level_to_numeric(level: str) -> float:
    """Convert DWD level string to numeric value.
    
    Args:
        level: The level string from the DWD API
        
    Returns:
        float: The numeric value representing the pollen level
        
    Note:
        Invalid or unknown level strings will return 0.0 (keine Belastung)
    """
    try:
        level_str = str(level).strip()
        if level_str not in DWD_LEVEL_MAPPING:
            _LOGGER.warning("Unknown pollen level value: %s", level_str)
            return DWD_LEVEL_NONE
        return DWD_LEVEL_MAPPING[level_str]
    except (ValueError, AttributeError) as err:
        _LOGGER.error("Error converting pollen level '%s' to numeric value: %s", level, err)
        return DWD_LEVEL_NONE

def numeric_to_label(val: float) -> str:
    """Convert numeric value to human readable label.
    
    Args:
        val: The numeric pollen level value
        
    Returns:
        str: Human readable label in German
    """
    try:
        # Round to nearest valid level to handle floating point imprecision
        valid_levels = sorted(DWD_LEVEL_LABELS.keys())
        closest_level = min(valid_levels, key=lambda x: abs(x - val))
        return DWD_LEVEL_LABELS[closest_level]
    except Exception as err:
        _LOGGER.error("Error converting numeric value %s to label: %s", val, err)
        return DWD_LEVEL_LABELS[DWD_LEVEL_NONE]

def process_pollen_data(pollen_data: dict, day_key: str) -> tuple[float, float, float]:
    """Process pollen data for a specific day.
    
    This function processes the raw pollen data from the DWD API and calculates
    the maximum pollen levels for three categories: trees, grasses, and weeds.
    
    Args:
        pollen_data: Dictionary containing the raw pollen data from DWD API
        day_key: The key for the day to process ('today', 'tomorrow', 'dayafter_to')
        
    Returns:
        Tuple containing three float values:
        - tree_level: Maximum pollen level for trees (0.0 to 3.0)
        - grass_level: Maximum pollen level for grasses (0.0 to 3.0)
        - weed_level: Maximum pollen level for weeds (0.0 to 3.0)
        
    Note:
        If no data is available for a category, its level will be 0.0
    """
    if not isinstance(pollen_data, dict):
        _LOGGER.warning("Invalid pollen data format: expected dict, got %s", type(pollen_data))
        return 0.0, 0.0, 0.0
    
    tree_pollen_levels = []
    grass_pollen_levels = []
    weed_pollen_levels = []
    
    for plant, values in pollen_data.items():
        if not isinstance(values, dict):
            _LOGGER.warning("Invalid values format for plant %s: expected dict, got %s", plant, type(values))
            continue
            
        level = values.get(day_key)
        if level is None:
            _LOGGER.debug("No data for plant %s on %s", plant, day_key)
            continue
        
        level_val = level_to_numeric(str(level))
        
        if plant in DWD_TREE_PLANTS:
            tree_pollen_levels.append(level_val)
        elif plant in DWD_GRASS_PLANTS:
            grass_pollen_levels.append(level_val)
        elif plant in DWD_WEED_PLANTS:
            weed_pollen_levels.append(level_val)
        else:
            _LOGGER.debug("Unknown plant type: %s", plant)
    
    # Calculate maximum levels with better error handling
    try:
        tree_level = max(tree_pollen_levels) if tree_pollen_levels else 0.0
    except Exception as err:
        _LOGGER.error("Error calculating tree pollen level: %s", err)
        tree_level = 0.0
        
    try:
        grass_level = max(grass_pollen_levels) if grass_pollen_levels else 0.0
    except Exception as err:
        _LOGGER.error("Error calculating grass pollen level: %s", err)
        grass_level = 0.0
        
    try:
        weed_level = max(weed_pollen_levels) if weed_pollen_levels else 0.0
    except Exception as err:
        _LOGGER.error("Error calculating weed pollen level: %s", err)
        weed_level = 0.0
    
    return tree_level, grass_level, weed_level

async def get_dwd_data() -> List[Dict[str, Any]]:
    """Fetch and process pollen data from DWD API.
    
    Returns:
        List of dictionaries containing pollen data for each forecast day.
        Each dictionary contains:
        - date: The forecast date (YYYY-MM-DD)
        - trees: Dict with pollen level for trees
        - grass: Dict with pollen level for grasses
        - weeds: Dict with pollen level for weeds
        
    Raises:
        DWDApiError: If there is any error fetching or processing the data
    """
    try:
        async with async_timeout.timeout(DWD_REQUEST_TIMEOUT):
            async with aiohttp.ClientSession() as session:
                async with session.get(DWD_API_URL) as resp:
                    if resp.status != 200:
                        raise DWDApiError(
                            ERROR_MESSAGES["cannot_connect"],
                            original_error=None
                        )
                    try:
                        dwd_data = await resp.json(content_type=None)
                    except ValueError as err:
                        raise DWDApiError(
                            ERROR_MESSAGES["parse_error"],
                            original_error=err
                        ) from err
    except asyncio.TimeoutError as err:
        raise DWDApiError(
            ERROR_MESSAGES["timeout"],
            original_error=err
        ) from err
    except aiohttp.ClientError as err:
        raise DWDApiError(
            ERROR_MESSAGES["cannot_connect"],
            original_error=err
        ) from err
    
    # Find Dresden region data
    region_info = None
    for entry in dwd_data.get("content", []):
        if entry.get("partregion_id") == DWD_REGION_ID or entry.get("region_id") == DWD_REGION_ID:
            region_info = entry
            break
    
    if region_info is None:
        raise DWDApiError(ERROR_MESSAGES["invalid_region"])
    
    # Process pollen data
    pollen = region_info.get("Pollen", {})
    if not pollen:
        raise DWDApiError(ERROR_MESSAGES["no_data"])

    result = []
    
    # Get the current date in German timezone
    current_date = datetime.now(ZoneInfo(DWD_TIMEZONE))
    last_update = dwd_data.get("last_update", "")
    
    for i, day in enumerate(DWD_FORECAST_DAYS):
        forecast_date = current_date + timedelta(days=i)
        tree_level, grass_level, weed_level = process_pollen_data(pollen, day)
        
        # Convert levels to labels
        tree_label = numeric_to_label(tree_level)
        grass_label = numeric_to_label(grass_level)
        weed_label = numeric_to_label(weed_level)
        
        day_name = DWD_DAY_NAMES.get(day, day)
        
        data = {
            "date": forecast_date.strftime("%Y-%m-%d"),
            "trees": {
                "pollen": int(tree_level * 100),
                "level": tree_label,
                "details": f"DWD Daten für Dresden ({day_name})"
            },
            "grass": {
                "pollen": int(grass_level * 100),
                "level": grass_label,
                "details": f"DWD Daten für Dresden ({day_name})"
            },
            "weeds": {
                "pollen": int(weed_level * 100),
                "level": weed_label,
                "details": f"DWD Daten für Dresden ({day_name})"
            }
        }
        result.append(data)
    
    # Fill remaining days with the last forecast (DWD only provides 3 days)
    while len(result) < 5:
        last_data = result[-1].copy()
        forecast_date = datetime.strptime(last_data["date"], "%Y-%m-%d") + timedelta(days=1)
        last_data["date"] = forecast_date.strftime("%Y-%m-%d")
        for category in ["trees", "grass", "weeds"]:
            last_data[category]["details"] = f"DWD Daten für Dresden (Prognose)"
        result.append(last_data)
    
    return result 