# Fan Control UI

A small PyQt6 application for controlling fan speeds exposed through Linux's
`hwmon` PWM interface.

## Features

- Automatically discovers available Linux PWM fan controls
- Shows fan labels, current speed percentages, and RPM readings when available
- Applies manual fan speeds from 0% to 100%
- Returns supported channels to the driver's automatic control mode
- Reports device, data, and permission errors in the interface

## Requirements

- Linux with one or more `pwmN` controls under `/sys/class/hwmon`
- Python 3.10 or newer
- Permission to write the relevant `pwmN` and `pwmN_enable` files

## Install and run

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install .
fancontrol-ui
```

The app discovers available PWM channels at startup. Move a slider and release
it to apply a speed from 0% to 100%. **Automatic** returns a channel to the
driver's automatic mode, and **Refresh** rescans connected hardware.

Hardware monitoring files are commonly writable only by root. Prefer a
device-specific udev rule or system service that grants narrowly scoped access.
Running the entire graphical application as root is not recommended.

> Setting a slider puts that channel into manual PWM mode. Firmware-based fan
> curves will no longer control it until automatic mode is restored. Very low
> speeds can stop some fans; monitor temperatures while choosing safe values.

## Development

```bash
python -m pip install -e '.[test]'
QT_QPA_PLATFORM=offscreen pytest
```

## License

MIT
