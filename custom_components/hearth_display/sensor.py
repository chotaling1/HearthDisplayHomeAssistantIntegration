"""Sensor platform for hearth_display."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import BlueprintDataUpdateCoordinator
    from .data import HearthDisplayConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: HearthDisplayConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hearth Display routine sensors from a config entry."""
    coordinator = entry.runtime_data.coordinator

    entities: list[HearthDisplayRoutineSensor] = []
    for member in coordinator.data or []:
        for routine in member.get("routines", []):
            entities.append(
                HearthDisplayRoutineSensor(
                    coordinator=coordinator,
                    entry_id=entry.entry_id,
                    user_id=member["user_id"],
                    first_name=member["first_name"].strip(),
                    routine_id=routine["id"],
                    routine_name=routine["name"],
                )
            )

    async_add_entities(entities)


class HearthDisplayRoutineSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a Hearth Display routine for a family member."""

    _attr_attribution = ATTRIBUTION
    _attr_icon = "mdi:clipboard-check-outline"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BlueprintDataUpdateCoordinator,
        entry_id: str,
        user_id: int,
        first_name: str,
        routine_id: int,
        routine_name: str,
    ) -> None:
        """Initialize the routine sensor."""
        super().__init__(coordinator)
        self._user_id = user_id
        self._routine_id = routine_id
        self._attr_unique_id = f"{entry_id}_{user_id}_{routine_id}"
        self._attr_name = routine_name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(user_id))},
            name=first_name,
            manufacturer="Hearth Display",
        )

    def _find_routine(self) -> dict[str, Any] | None:
        """Find this routine in the coordinator data."""
        for member in self.coordinator.data or []:
            if member.get("user_id") == self._user_id:
                for routine in member.get("routines", []):
                    if routine.get("id") == self._routine_id:
                        return routine
        return None

    @property
    def native_value(self) -> int | None:
        """Return the number of completed steps."""
        routine = self._find_routine()
        if routine is not None:
            return routine.get("completed_steps")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional routine attributes."""
        routine = self._find_routine()
        if routine is None:
            return {}

        total = routine.get("total_steps", 0)
        completed = routine.get("completed_steps", 0)

        attrs: dict[str, Any] = {
            "total_steps": total,
            "completed_steps": completed,
            "completion_percentage": round((completed / total) * 100, 1) if total > 0 else 0,
            "active_today": routine.get("active_today"),
            "is_active": routine.get("is_active"),
            "routine_id": routine.get("id"),
            "recurrence": routine.get("formatted_recurrence_details"),
        }

        steps = routine.get("steps", [])
        step_summary = []
        for step in sorted(steps, key=lambda s: s.get("order", 0)):
            step_summary.append({
                "name": step.get("name"),
                "is_complete": step.get("is_complete", False),
                "can_complete_today": step.get("can_complete_step_today", False),
            })
        attrs["steps"] = step_summary

        return attrs
