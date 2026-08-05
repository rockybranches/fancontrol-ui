# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added

- Arch Linux desktop integration and automated AUR publication
- Hardware topology analysis with live temperature, PWM, and RPM history
- Controls for optional hwmon fan configuration capabilities

### Changed

- Fan discovery now supports monitoring-only channels and controllers without
  PWM endpoints
- Release metadata and installation documentation are ready for Linux package
  repositories

## [0.1.0] - 2026-08-04

### Added

- Linux `hwmon` PWM fan discovery
- PyQt6 sliders for manual fan-speed control
- Fan labels, RPM readings, and status feedback
- Automatic-mode restoration for supported controllers
- Unit and headless UI tests
- GitHub Actions continuous integration and release automation

[0.1.0]: https://github.com/rockybranches/fancontrol-ui/releases/tag/v0.1.0
[Unreleased]: https://github.com/rockybranches/fancontrol-ui/compare/v0.1.0...HEAD
