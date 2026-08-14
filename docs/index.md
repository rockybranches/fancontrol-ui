# Fan Control UI

Fan Control UI is a PyQt6 desktop application for monitoring and configuring
fan endpoints exposed through Linux's [`hwmon` interface][hwmon].

## Features

- Discover fan endpoints from RPM, PWM, mode, and fan configuration files.
- Apply manual fan speeds and restore supported channels to automatic mode.
- Configure exposed RPM limits, targets, pulses per revolution, fan enablement,
  and tachometer divisors.
- Monitor RPM-only channels without presenting unsupported controls.
- Inspect controllers, temperature sensors, and fans in an interactive topology
  diagram.
- Graph up to 10 minutes of temperature, PWM, and RPM history.
- Report device, data, and permission errors in the interface.

## Using the application

The application scans `/sys/class/hwmon` at startup. Move a fan slider and
release it to apply a manual speed. **Automatic** returns a supported channel to
the driver's conventional automatic mode. Other settings use their adjacent
**Apply** button, and **Refresh** performs a complete hardware rescan.

The **Analysis** tab provides topology, capability details, current telemetry,
and history. When a fan exposes both PWM and RPM readings, use the history
selector to choose the series to graph.

!!! warning

    Applying a slider value puts that fan into manual PWM mode. Firmware fan
    curves no longer control it until automatic mode is restored. Very low
    speeds can stop some fans, so monitor temperatures while choosing safe
    values.

See [Installation](installation.md) to install Fan Control UI or
[Development](development.md) to work from a source checkout.

[hwmon]: https://docs.kernel.org/hwmon/hwmon-kernel-api.html
