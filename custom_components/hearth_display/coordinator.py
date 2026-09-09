"""DataUpdateCoordinator for hearth_display."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    HearthDisplayApiClientAuthenticationError,
    HearthDisplayApiClientError,
)

if TYPE_CHECKING:
    from .data import HearthDisplayConfigEntry


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class BlueprintDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: HearthDisplayConfigEntry

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        try:
            now = datetime.now(timezone.utc)
            start_time = (now - timedelta(days=1)).isoformat()
            end_time = (now + timedelta(days=1)).isoformat()
            client = self.config_entry.runtime_data.client
            routines, tasks = await asyncio.gather(
                client.async_get_routines(
                    start_time=start_time,
                    end_time=end_time,
                ),
                client.async_get_tasks(),
            )
        except HearthDisplayApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except HearthDisplayApiClientError as exception:
            raise UpdateFailed(exception) from exception
        else:
            return {"routines": routines or [], "tasks": tasks or []}
