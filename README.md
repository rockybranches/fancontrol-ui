# Fan Control UI

A small PyQt6 application for monitoring and configuring fan endpoints exposed
through Linux's `hwmon` interface.

## Features

- Discovers fan endpoints from RPM, PWM, mode, and fan configuration files
- Shows fan labels, current speed percentages, and RPM readings when available
- Applies manual fan speeds from 0% to 100%
- Returns supported channels to the driver's automatic control mode
- Configures exposed minimum, maximum, and target RPM values, pulses per
  revolution, fan enablement, and tachometer divisors, including on channels
  without PWM control
- Shows RPM-only channels as clearly identified monitoring-only rows
- Maps hwmon controllers to their temperature sensors and fan channels in an
  interactive topology diagram
- Samples temperatures, PWM percentages, and available RPM readings every
  second, with an in-memory 10-minute history graph
- Shows controller, sensor, and fan capability details when a topology node is
  selected
- Reports device, data, and permission errors in the interface

## Requirements

- Linux with one or more fan-related `fanN_*` or `pwmN*` files under
  `/sys/class/hwmon`
- Python 3.10 or newer
- Permission to write any exposed settings you want to change

## Install and run

On Arch Linux, install the AUR package with an AUR helper:

```bash
paru -S fancontrol-ui
```

For a distribution-independent installation from source:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install .
fancontrol-ui
```

The app discovers available fan endpoints at startup. When PWM is available,
move a slider and release it to apply a speed from 0% to 100%. **Automatic**
returns channels with `pwmN_enable` to the driver's conventional automatic mode.
Other exposed fan settings use an explicit **Apply** button. **Refresh** rescans
connected hardware. Open the **Analysis** tab to select hardware nodes, inspect
live values and capabilities, and view up to 600 recent samples per telemetry
series. Select PWM or RPM history when both are available. RPM-only fan history
is supported, and read failures are shown on the selected node without stopping
other telemetry.

Hardware monitoring files are commonly writable only by root. Prefer a
device-specific udev rule or system service that grants narrowly scoped access.
Running the entire graphical application as root is not recommended.

> Setting a slider puts that channel into manual PWM mode. Firmware-based fan
> curves will no longer control it until automatic mode is restored. Very low
> speeds can stop some fans; monitor temperatures while choosing safe values.

## Development

```bash
uv sync --extra test
QT_QPA_PLATFORM=offscreen uv run --frozen --extra test pytest
uv build
```

Python 3.10 through 3.13 are tested in CI. See
[`packaging/aur/README.md`](packaging/aur/README.md) for AUR release setup and
manual package validation.

## License

MIT
