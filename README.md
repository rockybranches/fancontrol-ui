# Fan Control UI

A small PyQt6 application for controlling fan speeds exposed through Linux's
`hwmon` PWM interface.

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
it to apply a speed from 0% to 100%. **Refresh** rescans connected hardware.

Hardware monitoring files are commonly writable only by root. Prefer a
device-specific udev rule or system service that grants narrowly scoped access.
Running the entire graphical application as root is not recommended.

> Setting a slider puts that channel into manual PWM mode. Firmware-based fan
> curves will no longer control it until automatic mode is restored by the
> driver, firmware, or another fan-control service.

## Development

```bash
python -m pip install -e '.[test]'
pytest
```

