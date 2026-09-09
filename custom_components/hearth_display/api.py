"""Hearth Display API Client."""

from __future__ import annotations

import socket
from typing import Any

import aiohttp
import async_timeout

BASE_URL = "https://app.hearthdisplay.com"
LOGIN_URL = f"{BASE_URL}/api/web/session/login_with_email"


class HearthDisplayApiClientError(Exception):
    """Exception to indicate a general API error."""


class HearthDisplayApiClientCommunicationError(
    HearthDisplayApiClientError,
):
    """Exception to indicate a communication error."""


class HearthDisplayApiClientAuthenticationError(
    HearthDisplayApiClientError,
):
    """Exception to indicate an authentication error."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise HearthDisplayApiClientAuthenticationError(
            msg,
        )
    response.raise_for_status()


class HearthDisplayApiClient:
    """Hearth Display API Client."""

    def __init__(
        self,
        email: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client."""
        self._email = email
        self._password = password
        self._session = session
        self._cookies: dict[str, str] = {}

    async def async_login(self) -> dict[str, Any]:
        """Login to the Hearth Display API and store session cookies."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method="post",
                    url=LOGIN_URL,
                    json={"email": self._email, "password": self._password},
                )
                if response.status in (401, 403):
                    msg = "Invalid credentials"
                    raise HearthDisplayApiClientAuthenticationError(msg)
                response.raise_for_status()

                # Store cookies from Set-Cookie headers
                self._cookies = {k: v.value for k, v in response.cookies.items()}

                return await response.json()

        except HearthDisplayApiClientAuthenticationError:
            raise
        except TimeoutError as exception:
            msg = f"Timeout error during login - {exception}"
            raise HearthDisplayApiClientCommunicationError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error during login - {exception}"
            raise HearthDisplayApiClientCommunicationError(msg) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Unexpected error during login - {exception}"
            raise HearthDisplayApiClientError(msg) from exception

    async def async_get_data(self) -> Any:
        """Get data from the API."""
        if not self._cookies:
            await self.async_login()
        return await self._api_wrapper(
            method="get",
            url=f"{BASE_URL}/api/web/session",
        )

    async def async_get_routines(
        self,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> Any:
        """Get routines data from the API."""
        if not self._cookies:
            await self.async_login()

        params: dict[str, str] = {}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        return await self._api_wrapper(
            method="get",
            url=f"{BASE_URL}/api/web/routines",
            params=params,
        )

    async def async_get_tasks(self) -> Any:
        """Get tasks data from the API."""
        if not self._cookies:
            await self.async_login()

        return await self._api_wrapper(
            method="get",
            url=f"{BASE_URL}/api/web/task",
        )

    async def async_complete_task(self, task_id: int) -> Any:
        """Mark a task as complete."""
        if not self._cookies:
            await self.async_login()

        return await self._api_wrapper(
            method="post",
            url=f"{BASE_URL}/api/web/task/complete/{task_id}",
        )

    async def async_undo_task(self, task_id: int) -> Any:
        """Undo completion of a task."""
        if not self._cookies:
            await self.async_login()

        return await self._api_wrapper(
            method="post",
            url=f"{BASE_URL}/api/web/task/undo/{task_id}",
        )

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
        params: dict | None = None,
    ) -> Any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                    cookies=self._cookies,
                )
                if response.status in (401, 403):
                    # Session may have expired, try re-login once
                    await self.async_login()
                    response = await self._session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=data,
                        params=params,
                        cookies=self._cookies,
                    )
                _verify_response_or_raise(response)
                return await response.json()

        except HearthDisplayApiClientAuthenticationError:
            raise
        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise HearthDisplayApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise HearthDisplayApiClientCommunicationError(
                msg,
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise HearthDisplayApiClientError(
                msg,
            ) from exception
