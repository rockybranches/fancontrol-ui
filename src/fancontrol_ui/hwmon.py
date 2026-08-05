from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


PWM_FILE = re.compile(r"pwm(\d+)$")


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
class FanChannel:
    chip: str
    index: int
    pwm_path: Path
    enable_path: Path | None
    maximum: int = 255
    label: str | None = None

    @property
    def display_name(self) -> str:
        return self.label or f"{self.chip} fan {self.index}"

    def read_percent(self) -> int:
        raw_value = _read_int(self.pwm_path)
        return round(max(0, min(raw_value, self.maximum)) * 100 / self.maximum)

    def read_rpm(self) -> int | None:
        rpm_path = self.pwm_path.with_name(f"fan{self.index}_input")
        if not rpm_path.exists():
            return None
        return _read_int(rpm_path)

    def set_percent(self, percent: int) -> None:
        if not 0 <= percent <= 100:
            raise ValueError("Fan speed must be between 0 and 100 percent")

        if self.enable_path is not None:
            self._write(self.enable_path, 1)

        raw_value = round(percent * self.maximum / 100)
        self._write(self.pwm_path, raw_value)

    @staticmethod
    def _write(path: Path, value: int) -> None:
        try:
            path.write_text(str(value), encoding="ascii")
        except OSError as exc:
            detail = exc.strerror or str(exc)
            raise FanControlError(f"Could not write {path}: {detail}") from exc


def discover_fans(hwmon_root: Path = Path("/sys/class/hwmon")) -> list[FanChannel]:
    if not hwmon_root.is_dir():
        return []

    fans: list[FanChannel] = []
    for device_path in sorted(hwmon_root.glob("hwmon*")):
        if not device_path.is_dir():
            continue

        name_path = device_path / "name"
        chip = _read_text(name_path) if name_path.exists() else device_path.name

        for pwm_path in sorted(device_path.glob("pwm[0-9]*")):
            match = PWM_FILE.fullmatch(pwm_path.name)
            if match is None or not pwm_path.is_file():
                continue

            index = int(match.group(1))
            maximum_path = device_path / f"pwm{index}_max"
            maximum = _read_int(maximum_path) if maximum_path.exists() else 255
            if maximum <= 0:
                continue

            label = _find_label(device_path, index)
            enable_path = device_path / f"pwm{index}_enable"
            fans.append(
                FanChannel(
                    chip=chip,
                    index=index,
                    pwm_path=pwm_path,
                    enable_path=enable_path if enable_path.exists() else None,
                    maximum=maximum,
                    label=label,
                )
            )

    return fans


def _find_label(device_path: Path, index: int) -> str | None:
    for filename in (f"pwm{index}_label", f"fan{index}_label"):
        path = device_path / filename
        if path.exists():
            label = _read_text(path)
            if label:
                return label
    return None

