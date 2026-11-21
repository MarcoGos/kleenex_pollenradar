"""Tests for pollen API requests."""

import ssl
import unittest
from unittest.mock import AsyncMock, Mock

from custom_components.kleenex_pollenradar.api import DNSError, PollenApi
from custom_components.kleenex_pollenradar.const import GetContentBy


class TestPollenApiRequests(unittest.IsolatedAsyncioTestCase):
    """Test request configuration for regional endpoints."""

    async def test_requests_use_session_tls_defaults(self):
        """GET and POST requests must not disable certificate verification."""
        for region, content_by, method, parameter, result in (
            ("fr", GetContentBy.CITY, "get", "params", "<html></html>"),
            ("it", GetContentBy.CITY_ITALY, "post", "data", {"html": ""}),
        ):
            with self.subTest(region=region):
                response = Mock(status=200, ok=True)
                response.text = AsyncMock(return_value=result)
                response.json = AsyncMock(return_value=result)
                session = Mock()
                request = AsyncMock(return_value=response)
                setattr(session, method, request)
                api = PollenApi(session, region, content_by)
                params = {"city": "Example"}
                url = "https://example.com/pollen"

                actual = await api._PollenApi__perform_request(url, params)

                self.assertEqual(actual, result)
                request.assert_awaited_once_with(
                    url=url, headers=api._headers, **{parameter: params}
                )

    async def test_certificate_failure_is_not_ignored(self):
        """TLS failures must propagate through the API error path."""
        error = ssl.SSLError("certificate verify failed")
        session = Mock()
        session.get = AsyncMock(side_effect=error)
        api = PollenApi(session, "fr", GetContentBy.CITY)

        with self.assertRaises(DNSError) as raised:
            await api._PollenApi__perform_request("https://example.com", {})

        self.assertIs(raised.exception.__cause__, error)
