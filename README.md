# Hearth Display for Home Assistant

A custom [Home Assistant](https://www.home-assistant.io/) integration for [Hearth Display](https://hearthdisplay.com/) that brings your family's routines and tasks into Home Assistant.

## Features

- **To-do lists** — each family member gets a to-do list entity holding their Hearth tasks. Ticking an item off in Home Assistant completes it in Hearth, and unticking it reopens it.
- **Routine tracking sensors** — a sensor for each family member's routine, showing completed steps, total steps, and progress percentage.
- **Task summary sensors** — outstanding task count, points earned today, and current best streak, per family member.
- **Per-member devices** — each family member appears as a separate device, with their routines, tasks and summaries grouped underneath. Unassigned tasks live on an "Anyone" device.
- **Automatic polling** — data is refreshed from the Hearth Display cloud API every 5 minutes.

## Requirements

- Home Assistant **2026.3.2** or newer
- A [Hearth Display](https://hearthdisplay.com/) account (email & password)

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant.
2. Go to **Integrations** and click the three-dot menu → **Custom repositories**.
3. Add `https://github.com/chotaling1/HearthDisplayHomeAssistantIntegration` with category **Integration**.
4. Search for "Hearth Display" and install it.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/hearth_display` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Hearth Display**.
3. Enter your Hearth Display account email and password.

The integration creates a device per family member, holding that member's to-do list, routine sensors and task summary sensors.

## Entities

### To-do lists

One `todo` entity per family member, plus an "Anyone" list for unassigned tasks. The state is the number of outstanding items.

The list shows everything still outstanding (including overdue tasks) plus anything completed today. Older completions are left out — Hearth creates a fresh task for every occurrence of a recurring chore, so including the full history would bury today's work under repeats of the same name. Keeping today's completions visible means an accidental tick can still be undone.

Completing an item calls Hearth's complete endpoint; reopening one calls undo.

### Routine sensors

One sensor per routine per member. The state is the number of completed steps.

| Attribute | Description |
| --- | --- |
| `total_steps` | Total number of steps in the routine |
| `completed_steps` | Number of completed steps |
| `completion_percentage` | Completion percentage (0–100) |
| `active_today` | Whether the routine is scheduled for today |
| `is_active` | Whether the routine is enabled |
| `recurrence` | Human-readable recurrence, e.g. `Daily` |
| `steps` | Each step's name, completion, and whether it can be completed today |

### Task summary sensors

Three per family member:

| Sensor | State |
| --- | --- |
| **Open tasks** | Count of outstanding tasks. Attributes break out `overdue`, `priority`, `completed_today`, and a `tasks` list. |
| **Points today** | Points earned from tasks completed on the current local day. |
| **Best streak** | Longest current streak across that member's recurring chores, with a per-chore breakdown in `streaks`. |

## Completing a task from an automation

Use [`todo.update_item`](https://www.home-assistant.io/actions/todo.update_item/) with `status: completed`.

Recurring chores get a new task ID for each occurrence, so an ID can't be hard-coded in an automation — target the item by name instead. Outstanding items are listed ahead of completed ones, so a name resolves to the occurrence that still needs action:

```yaml
actions:
  - action: todo.update_item
    target:
      entity_id: todo.hailey_tasks
    data:
      item: "Good table manners at breakfast"
      status: completed
```

To be explicit about which occurrence you're completing, look the ID up first with `todo.get_items` and pass that instead of the name.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

See [LICENSE](LICENSE) for details.
