"""
Helpers for parsing Hearth Display task payloads.

The ``/api/web/task`` endpoint returns a flat list of task objects rather than
the per-member grouping used by ``/api/web/routines``, so callers have to do
the grouping themselves. A few of its quirks are worth stating explicitly,
since they are easy to get wrong:

* ``assignee_profile.user_id`` is always ``None``. The real assignee is the
  top-level ``user_id`` field; ``assignee_profile`` only carries display data.
* A top-level ``user_id`` of ``None`` means the task is unassigned ("Anyone").
* Recurring chores mint a brand new task ``id`` for every occurrence, all
  sharing a ``recurrence_rule_id`` and ``streak_id``.
* Completion is expressed by ``completed_at``/``completed_by``. There is no
  ``status`` or ``is_complete`` field.
* ``due_at`` is a *local* day boundary encoded in UTC (23:59:59 local), so it
  must be converted to local time before taking a date from it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from datetime import date

ANYONE_KEY = "anyone"
ANYONE_NAME = "Anyone"


def task_group_key(task: dict[str, Any]) -> str:
    """Return the stable grouping key for a task's assignee."""
    user_id = task.get("user_id")
    return ANYONE_KEY if user_id is None else str(user_id)


def assignee_name(task: dict[str, Any]) -> str:
    """Return the assignee's display name, tolerating padded strings."""
    profile = task.get("assignee_profile") or {}
    name = (profile.get("first_name") or "").strip()
    return name or ANYONE_NAME


def is_complete(task: dict[str, Any]) -> bool:
    """Return True if the task has been completed."""
    return task.get("completed_at") is not None


def due_date(task: dict[str, Any]) -> date | None:
    """
    Return the task's due date in local time.

    ``due_at`` marks the end of the due day in local terms (for example
    ``2026-09-10T04:59:59Z`` is 23:59:59 on September 9th in US Central), so
    the UTC date is a day ahead of the date the app displays.
    """
    parsed = dt_util.parse_datetime(task.get("due_at") or "")
    if parsed is None:
        return None
    return dt_util.as_local(parsed).date()


def completed_date(task: dict[str, Any]) -> date | None:
    """Return the local date the task was completed, if it was."""
    parsed = dt_util.parse_datetime(task.get("completed_at") or "")
    if parsed is None:
        return None
    return dt_util.as_local(parsed).date()


def completed_today(task: dict[str, Any]) -> bool:
    """Return True if the task was completed on the current local day."""
    return completed_date(task) == dt_util.now().date()


def group_tasks(tasks: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    """
    Group tasks by assignee, preserving API order within each group.

    Returns a mapping of group key to ``{"key", "user_id", "name", "tasks"}``.
    Grouping by assignee rather than by task keeps the set of entities stable
    even though recurring chores produce a new task id every day.
    """
    groups: dict[str, dict[str, Any]] = {}
    for task in tasks or []:
        key = task_group_key(task)
        group = groups.get(key)
        if group is None:
            group = {
                "key": key,
                "user_id": task.get("user_id"),
                "name": assignee_name(task),
                "tasks": [],
            }
            groups[key] = group
        group["tasks"].append(task)
    return groups
