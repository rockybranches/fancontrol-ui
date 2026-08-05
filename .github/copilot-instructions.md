# Fan Control UI repository instructions

## Build and test

- Use Python 3.10 or newer. The repository is locked with `uv.lock`; match CI with `uv` when possible.
- Install development dependencies with `uv sync --extra test` (the README's pip alternative is `python -m pip install -e '.[test]'`).
- Run the full suite headlessly:
  ```bash
  QT_QPA_PLATFORM=offscreen uv run --frozen --extra test pytest
  ```
- Run one test by pytest node ID:
  ```bash
  QT_QPA_PLATFORM=offscreen uv run --frozen --extra test pytest tests/test_hwmon.py::test_set_percent_enables_manual_mode
  ```
  Keep `QT_QPA_PLATFORM=offscreen` for UI tests and for commands that may collect `tests/test_window.py`.
- Build both the wheel and source distribution with `uv build`.
- Run the application from the checkout with `uv run fancontrol-ui` or `uv run python -m fancontrol_ui`.
- No lint or static type-check command is configured in this repository.

## Architecture

This is a small, synchronous PyQt6 desktop application with a deliberate split between hardware access and presentation:

- `fancontrol_ui.hwmon` is the hardware/domain layer. `discover_hwmon()` returns immutable `HwmonController` values containing `TemperatureSensor` and `FanChannel` children; `discover_fans()` remains the compatibility API that flattens controller fan channels. Fan discovery uses the union of relevant `fanN_*` and `pwmN*` files, so `FanChannel.pwm_path` is optional. Domain objects own all sysfs reads, conversions, capabilities, and fan writes.
- `fancontrol_ui.window` is the Qt presentation layer. `FanControlWindow` keeps the existing Controls UI and adds an Analysis tab backed by `QGraphicsScene`. A one-second `QTimer` samples discovered telemetry into per-series `deque(maxlen=600)` histories.
- `fancontrol_ui.main` creates the single `QApplication` and window. Both the `fancontrol-ui` console script and `python -m fancontrol_ui` lead to this entry point.

The application has no daemon or persistence layer. Refresh is an explicit rescan that rebuilds fan rows and topology nodes, clears telemetry history, and replaces all discovered object references. Slider value changes update only the displayed percentage; releasing the slider performs the hardware write.

## Hardware access conventions

- Keep filesystem reads and writes in `hwmon.py`; the Qt layer should consume `FanChannel` methods rather than manipulate sysfs paths.
- Wrap `OSError` and invalid device-file contents in `FanControlError` with the affected path. The window catches this domain error and exposes it to the user.
- Linux hwmon mode values are significant: write `1` to `pwmN_enable` before setting a manual PWM value and write `2` to restore driver automatic control.
- Preserve `FanChannel.set_percent()`'s failure safety: if the PWM write fails after changing mode, restore the previous non-manual mode; if restoration also fails, report both failures.
- Convert percentages with `round(percent * maximum / 100)` and clamp device values when reading. Controllers may expose `pwmN_max`; otherwise the maximum is 255. Only read or poll percentages when `pwmN` exists.
- Treat PWM, `pwmN_enable`, RPM input, labels, `fanN_min`, `fanN_max`, `fanN_target`, `fanN_pulses`, `fanN_enable`, and `fanN_div` as independent optional capabilities. Prefer `pwmN_label`, then `fanN_label`, then the generated chip/index display name. Existence determines capability; do not infer writability or hide an existing setting because of permissions.
- Use the hwmon device directory plus numeric fan index as channel identity. Never derive topology keys, controller grouping, widget IDs, or telemetry series from an optional PWM path.
- Discovery accepts a `Path` root so tests can model sysfs with `tmp_path`; do not hard-code `/sys/class/hwmon` below the default argument.
- Discover `tempN_input` as a `TemperatureSensor`; `tempN_label`, `tempN_max`, and `tempN_crit` are optional. Temperatures use Linux hwmon millidegrees Celsius and must be converted in `hwmon.py`.

## UI and testing conventions

- Preserve constructor injection of the discovery callable in `FanControlWindow`; window tests use it to avoid real hardware.
- A custom legacy `discover=lambda: [...]` must never trigger real-hardware analysis discovery. Tests that need sensors inject `discover_hardware` explicitly.
- Qt tests share a module-scoped `QApplication`, construct windows directly, and close each window. Hardware tests create plain files under `tmp_path`; they must not require root or a Linux hwmon device.
- Interactive controls use stable object names in the form `fan-{hwmon-directory}-{index}-{control}` so tests can locate them with `findChild`. Numeric settings use a `QSpinBox` and a separate `{control}-apply` button; monitoring-only rows state that no configurable controls are exposed.
- Analysis widgets use stable `analysis-*` object names. Topology rectangle items store their stable domain key in graphics item data role 0. The history-series selector must expose each sampled series for a node; do not silently graph only the first series.
- When connecting signals inside the fan-row loop, capture the current widget/channel in lambda default arguments; otherwise callbacks will reference a later loop value.
- A channel read failure disables its slider and marks its readings unavailable. Operation errors update the common status label rather than escaping the Qt callback.
- Poll telemetry every 1000 ms and retain no more than 600 values per series. Catch each `FanControlError` independently so one missing or unreadable sysfs file does not stop other series or the timer.

## Packaging and releases

- The package uses a `src/` layout configured in `pyproject.toml`; pytest adds `src` to `pythonpath` and collects from `tests/`.
- Keep the version in `pyproject.toml` and `fancontrol_ui.__version__` synchronized. Release tags use `v<version>` and the release workflow rejects a tag that does not match `pyproject.toml`.
- CI supports Python 3.10 through 3.13, runs the headless suite from the frozen lockfile, and builds distributions. Avoid syntax or APIs unavailable on Python 3.10.
