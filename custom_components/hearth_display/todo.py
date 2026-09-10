"""Todo platform for hearth_display."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import HearthDisplayApiClientError
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
    """Set up a to-do list per assignee from a config entry."""
    coordinator = entry.runtime_data.coordinator

    async_add_entities(
        HearthDisplayTodoList(
            coordinator=coordinator,
            entry_id=entry.entry_id,
            group_key=group["key"],
            user_id=group["user_id"],
            name=group["name"],
        )
        for group in group_tasks((coordinator.data or {}).get("tasks")).values()
    )


class HearthDisplayTodoList(CoordinatorEntity, TodoListEntity):
    """A Hearth Display task list for a single assignee."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_name = "Tasks"
    _attr_icon = "mdi:clipboard-list-outline"
    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM

    def __init__(
        self,
        coordinator: HearthDisplayDataUpdateCoordinator,
        entry_id: str,
        group_key: str,
        user_id: int | None,
        name: str,
    ) -> None:
        """Initialize the to-do list."""
        super().__init__(coordinator)
        self._group_key = group_key
        self._attr_unique_id = f"{entry_id}_tasks_{group_key}"
        # Share the routine sensors' device so a member's routines and tasks
        # group together. Unassigned ("Anyone") tasks get their own device.
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

    @property
    def todo_items(self) -> list[TodoItem]:
        """
        Return the to-do items to display.

        The API hands back roughly two weeks of history, and recurring chores
        appear once per day, so showing everything would bury today's work
        under repeats of the same chore. This shows everything outstanding
        (including overdue) plus whatever was completed today, which keeps a
        mis-tap undoable without the backlog.

        Outstanding items are listed first, oldest due date first. Recurring
        chores reuse the same subject every day, and ``todo.update_item``
        resolves a name to the *first* matching item, so ordering decides
        which occurrence an automation acts on. A recurring task's uid changes
        with each occurrence and cannot be hard-coded in an automation, which
        makes name targeting the only practical option -- putting outstanding
        work first means a name resolves to the occurrence still needing
        action rather than one already completed today.
        """
        items: list[TodoItem] = []
        for task in self._tasks:
            complete = is_complete(task)
            if complete and not completed_today(task):
                continue
            items.append(
                TodoItem(
                    uid=str(task["id"]),
                    summary=(task.get("subject") or "").strip(),
                    status=(
                        TodoItemStatus.COMPLETED
                        if complete
                        else TodoItemStatus.NEEDS_ACTION
                    ),
                    due=due_date(task),
                    description=(task.get("description") or "").strip() or None,
                )
            )

        return sorted(
            items,
            key=lambda item: (
                item.status == TodoItemStatus.COMPLETED,
                item.due or date.max,
            ),
        )

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """
        Complete or reopen a task.

        Only the completion status is writable; Hearth exposes dedicated
        complete/undo endpoints rather than a general task update.
        """
        client = self.coordinator.config_entry.runtime_data.client
        task_id = int(item.uid)

        try:
            if item.status == TodoItemStatus.COMPLETED:
                await client.async_complete_task(task_id)
            else:
                await client.async_undo_task(task_id)
        except HearthDisplayApiClientError as exception:
            msg = f"Failed to update task {task_id}: {exception}"
            raise HomeAssistantError(msg) from exception

        await self.coordinator.async_request_refresh()
