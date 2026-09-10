"""Custom types for hearth_display."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import HearthDisplayApiClient
    from .coordinator import HearthDisplayDataUpdateCoordinator


type HearthDisplayConfigEntry = ConfigEntry[HearthDisplayData]


@dataclass
class HearthDisplayData:
    """Runtime data for the Hearth Display integration."""

    client: HearthDisplayApiClient
    coordinator: HearthDisplayDataUpdateCoordinator
    integration: Integration
