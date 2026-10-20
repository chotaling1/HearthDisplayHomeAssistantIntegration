"""Hearth Display API Client."""

from __future__ import annotations

import asyncio
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


def _first(*values: Any) -> Any:
    """Return the first value that is not None."""
    return next((value for value in values if value is not None), None)


def _normalize_member(
    member: dict[str, Any],
    details_by_id: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Convert a ``/routines/summary`` member into the original routines shape."""
    profile = member.get("p_profile") or {}
    return {
        "user_id": profile.get("user_id"),
        "first_name": profile.get("first_name") or "",
        "color": profile.get("color"),
        "routines": [
            _normalize_routine(routine, details_by_id.get(routine["id"]) or {})
            for routine in member.get("routines") or []
        ],
    }


def _normalize_routine(
    routine: dict[str, Any],
    details: dict[str, Any],
) -> dict[str, Any]:
    """Merge a summary routine with its details into the original shape."""
    steps = details.get("steps") or routine.get("steps") or []
    return {
        "id": routine["id"],
        "name": routine.get("name") or details.get("name"),
        "completed_steps": _first(
            details.get("p_completed_steps"), routine.get("p_completed_steps"), 0
        ),
        "total_steps": _first(
            details.get("p_available_steps"), routine.get("p_available_steps"), 0
        ),
        "active_today": routine.get("p_is_scheduled_today"),
        "is_active": not (routine.get("analytics_properties") or {}).get(
            "is_paused", False
        ),
        "streak_length": routine.get("streak_length"),
        "formatted_recurrence_details": _first(
            routine.get("p_formatted_recurrence_details"),
            details.get("p_formatted_recurrence_details"),
        ),
        "week_progress": routine.get("p_week_progress") or [],
        "steps": [
            {
                "name": step.get("name"),
                "order": step.get("order", 0),
                "is_complete": bool(step.get("p_is_complete")),
                "can_complete_step_today": bool(step.get("p_can_complete")),
            }
            for step in steps
        ],
    }


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
                _verify_response_or_raise(response)

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

    async def async_get_routines(self) -> list[dict[str, Any]]:
        """
        Get routines for every family member, with today's steps.

        ``GET /api/web/routines`` now only accepts POST (create). The web app
        reads ``/api/web/routines/summary`` for the per-member routine list and
        ``/api/web/routines/{id}/details`` for each routine's steps. Both use
        ``p_``-prefixed fields; they are normalised back to the original shape
        so entity unique ids and attributes stay the same.
        """
        if not self._cookies:
            await self.async_login()

        summary = await self._api_wrapper(
            method="get",
            url=f"{BASE_URL}/api/web/routines/summary",
        )
        members = summary or []
        routine_ids = [
            routine["id"]
            for member in members
            for routine in member.get("routines") or []
        ]
        details = await asyncio.gather(
            *(self.async_get_routine_details(rid) for rid in routine_ids)
        )
        details_by_id = dict(zip(routine_ids, details, strict=True))

        return [
            _normalize_member(member, details_by_id)
            for member in members
            if (member.get("p_profile") or {}).get("user_id") is not None
        ]

    async def async_get_routine_details(self, routine_id: int) -> dict[str, Any]:
        """Get today's progress and steps for one routine."""
        return await self._api_wrapper(
            method="get",
            url=f"{BASE_URL}/api/web/routines/{routine_id}/details",
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
