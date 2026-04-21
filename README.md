# Hearth Display for Home Assistant

A custom [Home Assistant](https://www.home-assistant.io/) integration for [Hearth Display](https://hearthdisplay.com/) that brings your family's routine data into Home Assistant.

## Features

- **Routine tracking sensors** — creates a sensor for each family member's routine, showing completed steps, total steps, and progress percentage.
- **Per-member devices** — each family member appears as a separate device in Home Assistant, with their routines grouped underneath.
- **Automatic polling** — data is refreshed from the Hearth Display cloud API every hour.

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

The integration will create a device for each family member and a sensor for each of their routines.

## Sensors

Each routine sensor exposes:

| Attribute | Description |
| --- | --- |
| `state` | Number of completed steps |
| `total_steps` | Total number of steps in the routine |
| `completed_steps` | Number of completed steps |
| `progress` | Completion percentage (0–100%) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

See [LICENSE](LICENSE) for details.
