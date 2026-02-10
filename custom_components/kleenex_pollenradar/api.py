"""Kleenex API"""

from typing import Any
import logging

from datetime import datetime, date
import aiohttp
import async_timeout

from homeassistant.exceptions import HomeAssistantError

from bs4 import BeautifulSoup, Tag
from .const import DOMAIN, REGIONS, GetContentBy, METHODS

TIMEOUT = 10

_LOGGER: logging.Logger = logging.getLogger(__package__)


class PollenApi:
    """Pollenradar API."""

    _headers: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.3",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    _raw_data: Any = ""
    _pollen: list[dict[str, Any]] = []
    _pollen_types = ("trees", "weeds", "grass")
    _pollen_detail_types: dict[str, str] = {
        "trees": "tree",
        "weeds": "weed",
        "grass": "grass",
    }
    _found_city: str = ""
    _found_latitude: float = 0.0
    _found_longitude: float = 0.0

    def __init__(
        self,
        session: aiohttp.ClientSession,
        region: str,
        get_content_by: GetContentBy,
        city: str = "",
    ) -> None:
        self._session = session
        self.region = region
        self.get_content_by = get_content_by
        self.city = city

    async def async_get_data(self) -> dict[str, Any]:
        """Get data from the API."""
        await self.refresh_data()
        return {
            "pollen": self._pollen,
            "location": {
                "latitude": self._found_latitude,
                "longitude": self._found_longitude,
                "city": self._found_city,
            },
            "raw": self._raw_data,
        }

    async def refresh_data(self):
        """Refresh data from the API."""
        if self.city:
            success = await self.__request_data()
            if success:
                if self.get_content_by == GetContentBy.CITY_ITALY:
                    self.__decode_raw_data_italy()
                else:
                    self.__decode_raw_data()

    async def __request_data(self) -> bool:
        """Request data from the API using city."""
        params = {
            "city"
            if self.get_content_by == GetContentBy.CITY
            else "location": self.city
        }
        url = self.__get_url_by_region()
        _LOGGER.debug("Requesting data from URL: %s with params: %s", url, params)
        data = await self.__perform_request(url, params)
        self._raw_data = data
        return data is not None

    def __get_url_by_region(self) -> str:
        """Get the URL for the API based on the region."""
        return f"{REGIONS[self.region]['url']}{self.__get_url_page()}"

    def __get_url_page(self) -> str:
        """Get the URL for the page based on the region."""
        return METHODS[self.get_content_by]

    async def __perform_request(self, url: str, params: Any) -> Any | None:
        """Perform the request to the API."""
        try:
            async with async_timeout.timeout(TIMEOUT):
                if REGIONS[self.region]["method"] == "get":
                    response = await self._session.get(
                        url=url, params=params, headers=self._headers, ssl=False
                    )
                else:
                    response = await self._session.post(
                        url=url, data=params, headers=self._headers, ssl=False
                    )
                if response.status == 403:
                    _LOGGER.error("Access forbidden: 403 error from server")
                    return None
                if response.ok:
                    if self.get_content_by == GetContentBy.CITY_ITALY:
                        return await response.json()
                    else:
                        return await response.text()
                return None
        except aiohttp.ClientConnectorDNSError as e:
            raise DNSError(
                "dns_error",
                translation_domain=DOMAIN,
                translation_key="dns_error",
            ) from e
        except Exception as e:
            raise DNSError(
                "unknown_error",
                translation_domain=DOMAIN,
                translation_key="unknown_error",
            ) from e

    def __decode_raw_data(self):
        """Decode the raw data from the API."""
        # <button class="day-link active" data-grass="low" data-trees="moderate" data-weeds="low"
        # data-grass-count="0 PPM"
        # data-weeds-count="0 PPM"
        # data-trees-count="133 PPM"
        # data-grass-detail="Poaceae,0,low"
        # data-tree-detail="Hazelaar,9,low|Iep,2,low|Pijnboom,0,low|Els,29,low|Populier,10,low|Eik,0,low|Plataan,0,low|Berk,0,low|Cipres,83,high"
        # data-weed-detail="Bijvoet,0,low|Ganzevoet,0,low|Ambrosia,0,low|Brandnetel,0,low">
        #     <span class="day-name">Vandaag</span>
        #     <span class="day-number">10</span>
        # </button>

        soup = BeautifulSoup(self._raw_data, "html.parser")

        self.__extract_location_data(soup)

        results = soup.find_all("button", class_="day-link")
        if results:
            self._pollen = []
        tag_results = [el for el in results if isinstance(el, Tag)]
        for day in tag_results:
            day_no = int(day.select_one("span.day-number").contents[0])  # type: ignore
            pollen_date = self.__determine_pollen_date(day_no)
            pollen: dict[str, Any] = {
                "day": day_no,
                "date": pollen_date,
            }
            for pollen_type in self._pollen_types:
                count_unit = day.get(f"data-{pollen_type}-count", "0 PPM")
                try:
                    pollen_count, unit_of_measure = count_unit.split(" ")  # type: ignore
                    pollen[pollen_type] = int(pollen_count)
                except (ValueError, AttributeError):
                    pollen[pollen_type] = 0
                    unit_of_measure = "ppm"
                pollen_level = day.get(
                    f"data-{pollen_type}", ""
                ) or self.determine_level_by_count(pollen_type, pollen[pollen_type])
                pollen[f"{pollen_type}_level"] = pollen_level
                pollen[f"{pollen_type}_unit_of_measure"] = unit_of_measure.lower()
                pollen[f"{pollen_type}_details"] = []

                pollen_detail_type = self._pollen_detail_types[pollen_type]
                pollen_details_str = day.get(f"data-{pollen_detail_type}-detail", "")
                if pollen_details_str:
                    for item in pollen_details_str.split("|"):  # type: ignore
                        sub_items = item.split(",")
                        if len(sub_items) == 3:
                            try:
                                pollen_detail = {
                                    "name": sub_items[0],
                                    "value": int(sub_items[1]),
                                    "level": sub_items[2],
                                }
                            except ValueError:
                                pollen_detail = {
                                    "name": sub_items[0],
                                    "value": 0,
                                    "level": sub_items[2],
                                }
                            pollen[f"{pollen_type}_details"].append(pollen_detail)
            self._pollen.append(pollen)

    def __decode_raw_data_italy(self):
        """Decode the raw data from the API for Italy."""
        self.__extract_location_data_italy(self._raw_data.get("city", ""))
        data = self._raw_data.get("html", "")
        soup = BeautifulSoup(data, "html.parser")
        day_infos = soup.find_all("button", class_="day-wrapper")
        if day_infos:
            self._pollen = []
        for day_info in day_infos:
            day_class = day_info.get("data-day-value", "day")
            day_no = int(day_info.find("span", "forecast-date").contents[0])  # type: ignore
            pollen_date = self.__determine_pollen_date(day_no)
            pollen: dict[str, Any] = {
                "day": day_no,
                "date": pollen_date,
            }
            pollen_infos = soup.find_all("button", class_=day_class)
            for pollen_info in pollen_infos:
                pollen_type = str(pollen_info.get("data-show", ""))
                if "-" in pollen_type:
                    original_pollen_type = pollen_type.split("-")[0]
                    pollen_type = original_pollen_type
                    if pollen_type != "grass":
                        pollen_type += "s"
                    ppm_span = pollen_info.find("span", class_="number-text")
                    if ppm_span:
                        count_unit = ppm_span.text.strip()  # type: ignore
                    else:
                        count_unit = "0 PPM"
                    try:
                        pollen_count, unit_of_measure = count_unit.split(" ")  # type: ignore
                        pollen[pollen_type] = int(pollen_count)
                    except (ValueError, AttributeError):
                        pollen[pollen_type] = 0
                        unit_of_measure = "ppm"
                    pollen_level = self.determine_level_by_count(
                        pollen_type, pollen[pollen_type]
                    )
                    pollen[f"{pollen_type}_level"] = pollen_level
                    pollen[f"{pollen_type}_unit_of_measure"] = unit_of_measure.lower()
                    pollen[f"{pollen_type}_details"] = []
                    pollen_analysis = soup.find(
                        "div",
                        class_=f"{original_pollen_type}-pollen-analysis-{day_class.replace('day', 'day-')}",
                    )
                    if pollen_analysis:
                        detail_infos = pollen_analysis.find_all(
                            "div", class_="table-details"
                        )
                        if detail_infos:
                            for detail_info in detail_infos:
                                name = (
                                    detail_info.find("span", class_="name-text")
                                    .contents[0]
                                    .text
                                )
                                value = (
                                    detail_info.find("span", class_="quality-text")
                                    .contents[0]
                                    .text.split(" ")
                                )
                                pollen_detail = {
                                    "name": name,
                                    "value": int(value[1]),
                                    "level": value[0],
                                }
                                pollen[f"{pollen_type}_details"].append(pollen_detail)

            self._pollen.append(pollen)

    def __extract_location_data(self, soup: BeautifulSoup) -> None:
        """Extract latitude and longitude from the soup."""
        self._found_city = self.__get_location_str("cityName", soup)
        self._found_latitude = self.__get_location_float("pollenlat", soup)
        self._found_longitude = self.__get_location_float("pollenlng", soup)

    def __extract_location_data_italy(self, city_data: str) -> None:
        """Extract latitude and longitude from the city data."""
        city_info = city_data.split("|")
        self._found_city = city_info[0] if len(city_info) > 0 else ""
        self._found_latitude = float(city_info[1]) if len(city_info) > 1 else 0.0
        self._found_longitude = float(city_info[2]) if len(city_info) > 2 else 0.0

    def __get_location_str(self, key: str, soup: BeautifulSoup) -> str:
        """Get a location value from the raw data."""
        result = soup.find("input", id=key)
        return result.get("value", "") if result else ""  # type: ignore

    def __get_location_float(self, key: str, soup: BeautifulSoup) -> float:
        """Get a location value from the raw data."""
        result = soup.find("input", id=key)
        value = result.get("value", None) if result else None  # type: ignore
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def __determine_pollen_date(self, day_no: int) -> date:
        """Determine the date of the pollen data."""
        year = datetime.today().year
        month = datetime.today().month
        try:
            dt = datetime(year=year, month=month, day=day_no)
            invalid_date = False
        except ValueError:
            dt = datetime.today()
            invalid_date = True
        if dt.date() < datetime.today().date() or invalid_date:
            month += 1
            if month > 12:
                year += 1
                month = 1
            dt = datetime(year=year, month=month, day=day_no)
        return dt.date()

    def determine_level_by_count(self, pollen_type: str, pollen_count: int) -> str:
        """Determine the pollen level based on the count."""
        thresholds = {
            "trees": [95, 207, 703],
            "weeds": [20, 77, 266],
            "grass": [29, 60, 341],
        }

        categories = ["low", "moderate", "high", "very-high"]

        for i, threshold in enumerate(thresholds.get(pollen_type, [])):
            if pollen_count <= threshold:
                return categories[i]

        return "very-high"


class DNSError(HomeAssistantError):
    """Base class for Pollen API errors."""
