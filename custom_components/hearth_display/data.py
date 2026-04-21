"""Custom types for hearth_display."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import HearthDisplayApiClient
    from .coordinator import BlueprintDataUpdateCoordinator


type HearthDisplayConfigEntry = ConfigEntry[HearthDisplayData]


@dataclass
class HearthDisplayData:
    """Data for the Blueprint integration."""

    client: HearthDisplayApiClient
    coordinator: BlueprintDataUpdateCoordinator
    integration: Integration
