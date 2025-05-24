"""Kleenex API"""

from typing import Any

from datetime import datetime, date
import aiohttp
import async_timeout

from homeassistant.exceptions import HomeAssistantError

from bs4 import BeautifulSoup
from .const import DOMAIN, REGIONS

TIMEOUT = 10


class PollenApi:
    """Pollenradar API."""

    _headers: dict[str, str] = {
        "User-Agent": "Home Assistant (kleenex_pollenradar)",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    _raw_data: str = ""
    _pollen: list[dict[str, Any]] = []
    _pollen_types = ("trees", "weeds", "grass")
    _pollen_detail_types: dict[str, str] = {
        "trees": "tree",
        "weeds": "weed",
        "grass": "grass",
    }

    def __init__(
        self,
        session: aiohttp.ClientSession,
        region: str = "",
        latitude: float = 0,
        longitude: float = 0,
    ) -> None:
        self._session = session
        self.region = region
        self.latitude = latitude
        self.longitude = longitude

    async def async_get_data(self) -> list[dict[str, Any]]:
        """Get data from the API."""
        await self.refresh_data()
        return self._pollen

    async def refresh_data(self):
        """Refresh data from the API."""
        if self.latitude != 0 and self.longitude != 0:
            success = await self.__request_by_latitude_longitude()
            if success:
                self.__decode_raw_data()

    async def __request_by_latitude_longitude(self) -> bool:
        """Request data from the API using latitude and longitude."""
        data = {"lat": self.latitude, "lng": self.longitude}
        success = await self.__perform_request(self.__get_url_by_region(), data)
        return success

    def __get_url_by_region(self) -> str:
        """Get the URL for the API based on the region."""
        return REGIONS[self.region]["url"]

    async def __perform_request(self, url: str, data: Any) -> bool:
        """Perform the request to the API."""
        try:
            async with async_timeout.timeout(TIMEOUT):
                response = await self._session.post(
                    url=url, data=data, headers=self._headers, ssl=False
                )
                if response.ok:
                    self._raw_data = await response.text()
                return response.ok
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
        soup = BeautifulSoup(self._raw_data, "html.parser")
        results = soup.find_all("button", class_="day-link")
        if results:
            self._pollen = []
        for day in results:
            day_no = int(day.select("span.day-number")[0].contents[0])  # type: ignore
            pollen_date = self.__determine_pollen_date(day_no)
            pollen: dict[str, Any] = {
                "day": day_no,
                "date": pollen_date,
            }
            pollen["pollen_type"] = {}
            for pollen_type in self._pollen_types:
                pollen_count, unit_of_measure = day.get(  # type: ignore
                    f"data-{pollen_type}-count", "0 PPM"
                ).split(" ")  # type: ignore
                try:
                    pollen[pollen_type] = int(pollen_count)
                except ValueError:
                    pollen[pollen_type] = 0
                pollen_level = day.get(f"data-{pollen_type}", "")  # type: ignore
                if pollen_level == "":
                    pollen_level = self.determine_level_by_count(
                        pollen_type, pollen[pollen_type]
                    )
                pollen[f"{pollen_type}_level"] = pollen_level
                pollen[f"{pollen_type}_unit_of_measure"] = unit_of_measure.lower()
                pollen[f"{pollen_type}_details"] = []

                pollen_detail_type = self._pollen_detail_types[pollen_type]
                pollen_details = day.get(f"data-{pollen_detail_type}-detail", "").split(  # type: ignore
                    "|"
                )
                for item in pollen_details:
                    sub_items = item.split(",")
                    pollen_detail = {
                        "name": sub_items[0],
                        "value": int(sub_items[1]),
                        "level": sub_items[2],
                    }
                    pollen[f"{pollen_type}_details"].append(pollen_detail)
            self._pollen.append(pollen)

    def get_raw_data(self) -> str:
        """Get the raw data from the API."""
        return self._raw_data

    def get_pollen_info(self) -> list[dict[str, Any]]:
        """Get the pollen information."""
        return self._pollen

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

    @property
    def position(self) -> str:
        """Get the position of the pollen data."""
        return f"{self.latitude}x{self.longitude}"

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
