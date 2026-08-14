# Development

The project supports Python 3.10 through 3.13 and uses the locked
[`uv`](https://docs.astral.sh/uv/) environment in CI.

## Set up a checkout

Install the development dependencies:

```bash
git clone https://github.com/rockybranches/fancontrol-ui.git
cd fancontrol-ui
uv sync --extra test --extra docs
```

Run the application directly from the checkout:

```bash
uv run fancontrol-ui
```

The equivalent module entry point is `uv run python -m fancontrol_ui`.

## Tests and distributions

Run the full test suite headlessly:

```bash
QT_QPA_PLATFORM=offscreen uv run --frozen --extra test pytest
```

Run a single test by node ID:

```bash
QT_QPA_PLATFORM=offscreen uv run --frozen --extra test \
  pytest tests/test_hwmon.py::test_set_percent_enables_manual_mode
```

Build the wheel and source distribution:

```bash
uv build
```

## Documentation

Preview the documentation with live reload:

```bash
uv run --frozen --extra docs mkdocs serve
```

Build it with the same strict link and configuration checks used by CI:

```bash
uv run --frozen --extra docs mkdocs build --strict
```

Documentation source belongs in `docs/`. Add new pages to `nav` in
`mkdocs.yml` so they appear in the rendered site.

## Project structure

| Path | Responsibility |
| --- | --- |
| `src/fancontrol_ui/hwmon.py` | Hardware discovery, sysfs access, conversions, and writes |
| `src/fancontrol_ui/window.py` | PyQt6 controls, analysis views, and telemetry polling |
| `src/fancontrol_ui/main.py` | Application and window entry point |
| `tests/` | Hardware-domain and headless Qt tests |
| `packaging/` | Desktop integration and AUR packaging |

Keep sysfs access in `hwmon.py`; presentation code should use the domain
objects rather than reading or writing device files directly. Tests model
hardware with ordinary files under pytest's temporary directory and must not
require root or physical hwmon devices.

When adding UI behavior, preserve dependency injection for hardware discovery,
stable widget object names, and independent error handling for each telemetry
series.
