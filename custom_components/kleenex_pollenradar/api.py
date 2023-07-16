from typing import Any

# import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
import logging
import aiohttp

from .const import DOMAIN, REGIONS

import async_timeout

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
        self._region = region
        self._latitude = latitude
        self._longitude = longitude

    async def async_get_data(self) -> list[dict[str, Any]]:
        """Get data from the API."""
        await self.refresh_data()
        return self._pollen

    async def refresh_data(self):
        if self._latitude != 0 and self._longitude != 0:
            success = await self.__request_by_latitude_longitude()
        if success:
            _LOGGER.debug("Trying to __decode_raw_data")
            self.__decode_raw_data()

    async def __request_by_latitude_longitude(self) -> bool:
        data = {"lat": self._latitude, "lng": self._longitude}
        _LOGGER.debug(f"__request_by_latitude_longitude, data={data}")
        success = await self.__perform_request(self.__get_url_by_region(), data)
        return success

    def __get_url_by_region(self) -> str:
        return REGIONS[self._region]["url"]

    async def __perform_request(self, url: str, data: Any) -> bool:
        _LOGGER.debug(f"Send {data} to {url} with headers {self._headers}")
        with async_timeout.timeout(TIMEOUT):
            response = await self._session.post(
                url=url, data=data, headers=self._headers
            )
        if response.ok:
            self._raw_data = await response.text()  # .content.decode("utf-8")
            _LOGGER.debug(f"{DOMAIN} - __perform_request succeeded")
        else:
            _LOGGER.error(f"Error: {DOMAIN} - __perform_request {response.status}")
        return response.ok

    def __decode_raw_data(self):
        self._pollen = []
        soup = BeautifulSoup(self._raw_data, "html.parser")
        _LOGGER.debug(f"Just loaded into BeautifulSoup")
        results = soup.find_all("button", class_="day-link")
        for day in results:
            day_no = int(day.select("span.day-number")[0].contents[0])
            pollen_date = self.__determine_pollen_date(day_no)
            _LOGGER.debug(f"Found day {day_no} {pollen_date}")
            pollen: dict[str, Any] = {
                "day": day_no,
                "date": pollen_date,
            }
            for pollen_type in self._pollen_types:
                pollen_count, unit_of_measure = day.get(
                    f"data-{pollen_type}-count"
                ).split(" ")
                pollen_level = day.get(f"data-{pollen_type}")
                pollen[pollen_type] = {
                    "pollen": pollen_count,
                    "level": pollen_level,
                    "unit_of_measure": unit_of_measure.lower(),
                    "details": [],
                }
                pollen_detail_type = self._pollen_detail_types[pollen_type]
                pollen_details = day.get(f"data-{pollen_detail_type}-detail").split("|")
                for item in pollen_details:
                    sub_items = item.split(",")
                    pollen_detail = {
                        "name": sub_items[0],
                        "value": int(sub_items[1]),
                        "level": sub_items[2],
                    }
                    pollen[pollen_type]["details"].append(pollen_detail)
            self._pollen.append(pollen)
            _LOGGER.debug(f"Day {day_no} with info {pollen}")
        _LOGGER.debug(f"Pollen info {self._pollen}")

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
        return f"{self._latitude}x{self._longitude}"
