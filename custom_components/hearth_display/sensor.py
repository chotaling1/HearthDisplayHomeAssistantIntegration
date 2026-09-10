"""Sensor platform for hearth_display."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .task_util import (
    ANYONE_KEY,
    completed_today,
    due_date,
    group_tasks,
    is_complete,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import HearthDisplayDataUpdateCoordinator
    from .data import HearthDisplayConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: HearthDisplayConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hearth Display routine sensors from a config entry."""
    coordinator = entry.runtime_data.coordinator

    entities: list[SensorEntity] = []
    for member in (coordinator.data or {}).get("routines") or []:
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

    # Task summaries are keyed by assignee rather than by task, so the entity
    # set stays stable even though recurring chores mint a new task id daily.
    for group in group_tasks((coordinator.data or {}).get("tasks")).values():
        entities.extend(
            description_cls(
                coordinator=coordinator,
                entry_id=entry.entry_id,
                group_key=group["key"],
                user_id=group["user_id"],
                name=group["name"],
            )
            for description_cls in (
                HearthDisplayOpenTasksSensor,
                HearthDisplayPointsTodaySensor,
                HearthDisplayBestStreakSensor,
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
        coordinator: HearthDisplayDataUpdateCoordinator,
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
        for member in (self.coordinator.data or {}).get("routines") or []:
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


class HearthDisplayTaskSensor(CoordinatorEntity, SensorEntity):
    """Base class for per-assignee task summary sensors."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    _key_suffix: str
    _sensor_name: str

    def __init__(
        self,
        coordinator: HearthDisplayDataUpdateCoordinator,
        entry_id: str,
        group_key: str,
        user_id: int | None,
        name: str,
    ) -> None:
        """Initialize the task summary sensor."""
        super().__init__(coordinator)
        self._group_key = group_key
        self._attr_unique_id = f"{entry_id}_tasks_{group_key}_{self._key_suffix}"
        self._attr_name = self._sensor_name
        # Reuse the routine sensors' device identifier so a member's routines
        # and tasks land on the same device. Unassigned tasks get their own.
        device_id = ANYONE_KEY if user_id is None else str(user_id)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=name,
            manufacturer="Hearth Display",
        )

    @property
    def _tasks(self) -> list[dict[str, Any]]:
        """Return this assignee's tasks from the latest poll."""
        group = group_tasks((self.coordinator.data or {}).get("tasks")).get(
            self._group_key
        )
        return group["tasks"] if group else []


class HearthDisplayOpenTasksSensor(HearthDisplayTaskSensor):
    """Number of tasks still outstanding for an assignee."""

    _key_suffix = "open_tasks"
    _sensor_name = "Open tasks"
    _attr_icon = "mdi:checkbox-marked-circle-outline"

    @property
    def native_value(self) -> int:
        """Return the count of incomplete tasks."""
        return sum(1 for task in self._tasks if not is_complete(task))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return a breakdown of the outstanding work."""
        open_tasks = [task for task in self._tasks if not is_complete(task)]
        return {
            "overdue": sum(1 for task in open_tasks if task.get("is_overdue")),
            "priority": sum(1 for task in open_tasks if task.get("is_priority")),
            "completed_today": sum(
                1 for task in self._tasks if completed_today(task)
            ),
            "tasks": [
                {
                    "subject": (task.get("subject") or "").strip(),
                    "due": due.isoformat() if (due := due_date(task)) else None,
                    "is_overdue": task.get("is_overdue"),
                    "points": task.get("point_value"),
                }
                for task in open_tasks
            ],
        }


class HearthDisplayPointsTodaySensor(HearthDisplayTaskSensor):
    """Points earned by an assignee on the current local day."""

    _key_suffix = "points_today"
    _sensor_name = "Points today"
    _attr_icon = "mdi:star-circle-outline"
    _attr_native_unit_of_measurement = "points"

    @property
    def native_value(self) -> int:
        """Return the summed point value of today's completions."""
        return sum(
            task.get("point_value") or 0
            for task in self._tasks
            if completed_today(task)
        )


class HearthDisplayBestStreakSensor(HearthDisplayTaskSensor):
    """
    Longest current streak across an assignee's recurring chores.

    ``streak_length`` is denormalized onto every occurrence of a recurring
    task, so it reads as the streak's current value rather than a per-day one.
    """

    _key_suffix = "best_streak"
    _sensor_name = "Best streak"
    _attr_icon = "mdi:fire"
    _attr_native_unit_of_measurement = "days"

    @property
    def native_value(self) -> int:
        """Return the highest current streak among this assignee's chores."""
        return max(
            (task.get("streak_length") or 0 for task in self._tasks),
            default=0,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the current streak for each distinct recurring chore."""
        streaks: dict[str, int] = {}
        for task in self._tasks:
            if not task.get("streak_id"):
                continue
            subject = (task.get("subject") or "").strip()
            streaks[subject] = max(
                streaks.get(subject, 0), task.get("streak_length") or 0
            )
        return {"streaks": streaks}
