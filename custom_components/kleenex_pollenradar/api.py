from typing import Any

# import requests
from datetime import datetime, date
import logging
import aiohttp
import async_timeout

from bs4 import BeautifulSoup

from .const import DOMAIN, REGIONS

TIMEOUT = 10

_LOGGER: logging.Logger = logging.getLogger(__package__)


class PollenApi:
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
        if self.latitude != 0 and self.longitude != 0:
            success = await self.__request_by_latitude_longitude()
            if success:
                _LOGGER.debug("Trying to __decode_raw_data")
                self.__decode_raw_data()

    async def __request_by_latitude_longitude(self) -> bool:
        data = {"lat": self.latitude, "lng": self.longitude}
        _LOGGER.debug("__request_by_latitude_longitude, data=%s", data)
        success = await self.__perform_request(self.__get_url_by_region(), data)
        return success

    def __get_url_by_region(self) -> str:
        return REGIONS[self.region]["url"]

    async def __perform_request(self, url: str, data: Any) -> bool:
        _LOGGER.debug("Send %s to %s with headers %s", data, url, self._headers)
        async with async_timeout.timeout(TIMEOUT):
            response = await self._session.post(
                url=url, data=data, headers=self._headers
            )
        if response.ok:
            self._raw_data = await response.text()
            _LOGGER.debug("%s - __perform_request succeeded", DOMAIN)
        else:
            _LOGGER.error("Error: %s - __perform_request %s", DOMAIN, response.status)
        return response.ok

    def __decode_raw_data(self):
        self._pollen = []
        soup = BeautifulSoup(self._raw_data, "html.parser")
        _LOGGER.debug("Just loaded into BeautifulSoup")
        results = soup.find_all("button", class_="day-link")
        for day in results:
            day_no = int(day.select("span.day-number")[0].contents[0])
            pollen_date = self.__determine_pollen_date(day_no)
            _LOGGER.debug("Found day %d %s", day_no, pollen_date)
            pollen: dict[str, Any] = {
                "day": day_no,
                "date": pollen_date,
            }
            for pollen_type in self._pollen_types:
                pollen_count, unit_of_measure = day.get(
                    f"data-{pollen_type}-count"
                ).split(" ")
                pollen_level = day.get(f"data-{pollen_type}").replace(" ", "_")
                try:
                    pollen[pollen_type] = int(pollen_count)
                except ValueError:
                    pollen[pollen_type] = 0
                pollen[f"{pollen_type}_level"] = pollen_level
                pollen[f"{pollen_type}_unit_of_measure"] = unit_of_measure.lower()
                pollen[f"{pollen_type}_details"] = []

                pollen_detail_type = self._pollen_detail_types[pollen_type]
                pollen_details = day.get(f"data-{pollen_detail_type}-detail").split("|")
                for item in pollen_details:
                    sub_items = item.split(",")
                    pollen_detail = {
                        "name": sub_items[0],
                        "value": int(sub_items[1]),
                        "level": sub_items[2],
                    }
                    pollen[f"{pollen_type}_details"].append(pollen_detail)
            self._pollen.append(pollen)
            _LOGGER.debug("Day %d with info %s", day_no, pollen)
        _LOGGER.debug("Pollen info %s", self._pollen)

    def get_pollen_info(self) -> list[dict[str, Any]]:
        return self._pollen

    def __determine_pollen_date(self, day_no: int) -> date:
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
        return f"{self.latitude}x{self.longitude}"
