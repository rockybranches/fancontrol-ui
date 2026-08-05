from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


PWM_FILE = re.compile(r"pwm(\d+)(?:_(?:enable|max|label))?$")
FAN_FILE = re.compile(r"fan(\d+)_(?:input|min|max|target|pulses|enable|div|label)$")
TEMP_INPUT_FILE = re.compile(r"temp(\d+)_input$")


class FanControlError(RuntimeError):
    """Raised when a fan control cannot be read or changed."""


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise FanControlError(f"Could not read {path}: {exc.strerror}") from exc


def _read_int(path: Path) -> int:
    value = _read_text(path)
    try:
        return int(value)
    except ValueError as exc:
        raise FanControlError(f"Invalid numeric value in {path}: {value!r}") from exc


@dataclass(frozen=True)
class FanCapabilities:
    pwm_maximum: int
    mode_control: bool
    rpm_available: bool
    label_available: bool
    pwm_available: bool = True
    minimum_control: bool = False
    maximum_control: bool = False
    target_control: bool = False
    pulses_control: bool = False
    enable_control: bool = False
    divisor_control: bool = False

    @property
    def configurable(self) -> bool:
        return any(
            (
                self.pwm_available,
                self.mode_control,
                self.minimum_control,
                self.maximum_control,
                self.target_control,
                self.pulses_control,
                self.enable_control,
                self.divisor_control,
            )
        )


@dataclass(frozen=True)
class FanChannel:
    chip: str
    index: int
    pwm_path: Path | None
    enable_path: Path | None
    maximum: int = 255
    label: str | None = None
    rpm_path: Path | None = None
    minimum_path: Path | None = None
    fan_maximum_path: Path | None = None
    target_path: Path | None = None
    pulses_path: Path | None = None
    fan_enable_path: Path | None = None
    divisor_path: Path | None = None
    device_path: Path | None = None

    @property
    def display_name(self) -> str:
        return self.label or f"{self.chip} fan {self.index}"

    @property
    def device_directory(self) -> Path:
        if self.device_path is not None:
            return self.device_path
        for path in (
            self.pwm_path,
            self.enable_path,
            self.rpm_path,
            self.minimum_path,
            self.fan_maximum_path,
            self.target_path,
            self.pulses_path,
            self.fan_enable_path,
            self.divisor_path,
        ):
            if path is not None:
                return path.parent
        return Path(self.chip)

    @property
    def identity(self) -> tuple[Path, int]:
        return (self.device_directory, self.index)

    @property
    def capabilities(self) -> FanCapabilities:
        return FanCapabilities(
            pwm_available=self.pwm_path is not None and self.pwm_path.exists(),
            pwm_maximum=self.maximum,
            mode_control=self._existing_path(self.enable_path, f"pwm{self.index}_enable")
            is not None,
            rpm_available=self._existing_path(self.rpm_path, f"fan{self.index}_input")
            is not None,
            label_available=self.label is not None,
            minimum_control=self._existing_path(self.minimum_path, f"fan{self.index}_min")
            is not None,
            maximum_control=self._existing_path(
                self.fan_maximum_path, f"fan{self.index}_max"
            )
            is not None,
            target_control=self._existing_path(self.target_path, f"fan{self.index}_target")
            is not None,
            pulses_control=self._existing_path(self.pulses_path, f"fan{self.index}_pulses")
            is not None,
            enable_control=self._existing_path(
                self.fan_enable_path, f"fan{self.index}_enable"
            )
            is not None,
            divisor_control=self._existing_path(self.divisor_path, f"fan{self.index}_div")
            is not None,
        )

    def read_percent(self) -> int:
        if self.pwm_path is None:
            raise FanControlError(f"{self.display_name} does not expose a PWM control")
        raw_value = _read_int(self.pwm_path)
        return round(max(0, min(raw_value, self.maximum)) * 100 / self.maximum)

    def read_rpm(self) -> int | None:
        rpm_path = self._existing_path(self.rpm_path, f"fan{self.index}_input")
        if rpm_path is None:
            return None
        return _read_int(rpm_path)

    def read_mode(self) -> int | None:
        enable_path = self._existing_path(self.enable_path, f"pwm{self.index}_enable")
        if enable_path is None:
            return None
        return _read_int(enable_path)

    def read_minimum_rpm(self) -> int | None:
        return self._read_optional(self.minimum_path, f"fan{self.index}_min")

    def set_minimum_rpm(self, value: int) -> None:
        self._write_optional(self.minimum_path, f"fan{self.index}_min", value, "minimum RPM")

    def read_maximum_rpm(self) -> int | None:
        return self._read_optional(self.fan_maximum_path, f"fan{self.index}_max")

    def set_maximum_rpm(self, value: int) -> None:
        self._write_optional(
            self.fan_maximum_path, f"fan{self.index}_max", value, "maximum RPM"
        )

    def read_target_rpm(self) -> int | None:
        return self._read_optional(self.target_path, f"fan{self.index}_target")

    def set_target_rpm(self, value: int) -> None:
        self._write_optional(self.target_path, f"fan{self.index}_target", value, "target RPM")

    def read_pulses(self) -> int | None:
        return self._read_optional(self.pulses_path, f"fan{self.index}_pulses")

    def set_pulses(self, value: int) -> None:
        self._write_optional(
            self.pulses_path, f"fan{self.index}_pulses", value, "pulses per revolution"
        )

    def read_enabled(self) -> int | None:
        return self._read_optional(self.fan_enable_path, f"fan{self.index}_enable")

    def set_enabled(self, value: int) -> None:
        if value not in (0, 1):
            raise ValueError("Fan enabled value must be 0 or 1")
        self._write_optional(self.fan_enable_path, f"fan{self.index}_enable", value, "enabled")

    def read_divisor(self) -> int | None:
        return self._read_optional(self.divisor_path, f"fan{self.index}_div")

    def set_divisor(self, value: int) -> None:
        if value <= 0:
            raise ValueError("Fan divisor must be positive")
        self._write_optional(self.divisor_path, f"fan{self.index}_div", value, "divisor")

    def set_percent(self, percent: int) -> None:
        if not 0 <= percent <= 100:
            raise ValueError("Fan speed must be between 0 and 100 percent")
        if self.pwm_path is None:
            raise FanControlError(f"{self.display_name} does not expose a PWM control")

        previous_mode = self.read_mode()
        enable_path = self._existing_path(self.enable_path, f"pwm{self.index}_enable")
        if enable_path is not None:
            self._write(enable_path, 1)

        raw_value = round(percent * self.maximum / 100)
        try:
            self._write(self.pwm_path, raw_value)
        except FanControlError as write_error:
            if enable_path is not None and previous_mode not in (None, 1):
                try:
                    self._write(enable_path, previous_mode)
                except FanControlError as restore_error:
                    raise FanControlError(
                        f"{write_error}; also failed to restore mode {previous_mode}: {restore_error}"
                    ) from write_error
            raise

    def set_automatic(self) -> None:
        enable_path = self._existing_path(self.enable_path, f"pwm{self.index}_enable")
        if enable_path is None:
            raise FanControlError(f"{self.display_name} does not expose an automatic mode control")
        self._write(enable_path, 2)

    def _read_optional(self, explicit_path: Path | None, filename: str) -> int | None:
        path = self._existing_path(explicit_path, filename)
        return None if path is None else _read_int(path)

    def _write_optional(
        self, explicit_path: Path | None, filename: str, value: int, description: str
    ) -> None:
        if value < 0:
            raise ValueError(f"Fan {description} cannot be negative")
        path = self._existing_path(explicit_path, filename)
        if path is None:
            raise FanControlError(f"{self.display_name} does not expose {description} control")
        self._write(path, value)

    def _existing_path(self, explicit_path: Path | None, filename: str) -> Path | None:
        path = explicit_path or self.device_directory / filename
        return path if path.exists() else None

    @staticmethod
    def _write(path: Path, value: int) -> None:
        try:
            path.write_text(str(value), encoding="ascii")
        except OSError as exc:
            detail = exc.strerror or str(exc)
            raise FanControlError(f"Could not write {path}: {detail}") from exc


@dataclass(frozen=True)
class TemperatureSensor:
    chip: str
    index: int
    input_path: Path
    label: str | None = None
    maximum_path: Path | None = None
    critical_path: Path | None = None

    @property
    def display_name(self) -> str:
        return self.label or f"{self.chip} temperature {self.index}"

    def read_celsius(self) -> float:
        return _read_int(self.input_path) / 1000

    def read_maximum_celsius(self) -> float | None:
        if self.maximum_path is None:
            return None
        return _read_int(self.maximum_path) / 1000

    def read_critical_celsius(self) -> float | None:
        if self.critical_path is None:
            return None
        return _read_int(self.critical_path) / 1000


@dataclass(frozen=True)
class HwmonController:
    name: str
    path: Path
    fans: tuple[FanChannel, ...] = ()
    sensors: tuple[TemperatureSensor, ...] = ()

    @property
    def display_name(self) -> str:
        return self.name


def discover_hwmon(hwmon_root: Path = Path("/sys/class/hwmon")) -> list[HwmonController]:
    if not hwmon_root.is_dir():
        return []

    controllers: list[HwmonController] = []
    for device_path in sorted(hwmon_root.glob("hwmon*")):
        if not device_path.is_dir():
            continue

        name_path = device_path / "name"
        chip = _read_text(name_path) if name_path.exists() else device_path.name
        fans: list[FanChannel] = []
        sensors: list[TemperatureSensor] = []

        fan_indices: set[int] = set()
        try:
            device_files = list(device_path.iterdir())
        except OSError as exc:
            detail = exc.strerror or str(exc)
            raise FanControlError(f"Could not inspect {device_path}: {detail}") from exc
        for path in device_files:
            match = PWM_FILE.fullmatch(path.name) or FAN_FILE.fullmatch(path.name)
            if match is not None and path.is_file():
                fan_indices.add(int(match.group(1)))

        for index in sorted(fan_indices):
            pwm_path = device_path / f"pwm{index}"
            maximum_path = device_path / f"pwm{index}_max"
            maximum = (
                _read_int(maximum_path)
                if pwm_path.exists() and maximum_path.exists()
                else 255
            )
            usable_pwm_path = pwm_path if pwm_path.exists() and maximum > 0 else None
            if pwm_path.exists() and usable_pwm_path is None:
                remaining_files = (
                    device_path / f"pwm{index}_enable",
                    device_path / f"fan{index}_input",
                    device_path / f"fan{index}_min",
                    device_path / f"fan{index}_max",
                    device_path / f"fan{index}_target",
                    device_path / f"fan{index}_pulses",
                    device_path / f"fan{index}_enable",
                    device_path / f"fan{index}_div",
                    device_path / f"fan{index}_label",
                )
                if not any(path.exists() for path in remaining_files):
                    continue

            label = _find_label(device_path, index)
            enable_path = device_path / f"pwm{index}_enable"
            rpm_path = device_path / f"fan{index}_input"
            minimum_path = device_path / f"fan{index}_min"
            fan_maximum_path = device_path / f"fan{index}_max"
            target_path = device_path / f"fan{index}_target"
            pulses_path = device_path / f"fan{index}_pulses"
            fan_enable_path = device_path / f"fan{index}_enable"
            divisor_path = device_path / f"fan{index}_div"
            fans.append(
                FanChannel(
                    chip=chip,
                    index=index,
                    pwm_path=usable_pwm_path,
                    enable_path=enable_path if enable_path.exists() else None,
                    maximum=maximum,
                    label=label,
                    rpm_path=rpm_path if rpm_path.exists() else None,
                    minimum_path=minimum_path if minimum_path.exists() else None,
                    fan_maximum_path=fan_maximum_path if fan_maximum_path.exists() else None,
                    target_path=target_path if target_path.exists() else None,
                    pulses_path=pulses_path if pulses_path.exists() else None,
                    fan_enable_path=fan_enable_path if fan_enable_path.exists() else None,
                    divisor_path=divisor_path if divisor_path.exists() else None,
                    device_path=device_path,
                )
            )

        for input_path in sorted(device_path.glob("temp[0-9]*_input")):
            match = TEMP_INPUT_FILE.fullmatch(input_path.name)
            if match is None or not input_path.is_file():
                continue

            index = int(match.group(1))
            label_path = device_path / f"temp{index}_label"
            label = _read_text(label_path) if label_path.exists() else None
            maximum_path = device_path / f"temp{index}_max"
            critical_path = device_path / f"temp{index}_crit"
            sensors.append(
                TemperatureSensor(
                    chip=chip,
                    index=index,
                    input_path=input_path,
                    label=label or None,
                    maximum_path=maximum_path if maximum_path.exists() else None,
                    critical_path=critical_path if critical_path.exists() else None,
                )
            )

        controllers.append(
            HwmonController(
                name=chip,
                path=device_path,
                fans=tuple(sorted(fans, key=lambda fan: fan.index)),
                sensors=tuple(sorted(sensors, key=lambda sensor: sensor.index)),
            )
        )

    return sorted(controllers, key=lambda controller: (controller.name.casefold(), str(controller.path)))


def discover_fans(hwmon_root: Path = Path("/sys/class/hwmon")) -> list[FanChannel]:
    fans = [fan for controller in discover_hwmon(hwmon_root) for fan in controller.fans]
    return sorted(
        fans, key=lambda fan: (fan.chip.casefold(), str(fan.device_directory), fan.index)
    )


def _find_label(device_path: Path, index: int) -> str | None:
    for filename in (f"pwm{index}_label", f"fan{index}_label"):
        path = device_path / filename
        if path.exists():
            label = _read_text(path)
            if label:
                return label
    return None
