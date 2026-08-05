from pathlib import Path

import pytest

from fancontrol_ui.hwmon import FanChannel, FanControlError, discover_fans


def test_discovers_fan_metadata(tmp_path: Path) -> None:
    device = tmp_path / "hwmon0"
    device.mkdir()
    (device / "name").write_text("testchip\n")
    (device / "pwm1").write_text("128\n")
    (device / "pwm1_enable").write_text("2\n")
    (device / "pwm1_max").write_text("255\n")
    (device / "fan1_label").write_text("CPU Fan\n")
    (device / "fan1_input").write_text("1450\n")

    fans = discover_fans(tmp_path)

    assert len(fans) == 1
    assert fans[0].display_name == "CPU Fan"
    assert fans[0].read_percent() == 50
    assert fans[0].read_rpm() == 1450
    assert fans[0].read_mode() == 2


def test_set_percent_enables_manual_mode(tmp_path: Path) -> None:
    pwm = tmp_path / "pwm2"
    enable = tmp_path / "pwm2_enable"
    pwm.write_text("0")
    enable.write_text("2")
    fan = FanChannel("testchip", 2, pwm, enable)

    fan.set_percent(40)

    assert enable.read_text() == "1"
    assert pwm.read_text() == "102"


def test_set_percent_rejects_out_of_range_value(tmp_path: Path) -> None:
    pwm = tmp_path / "pwm1"
    pwm.write_text("0")
    fan = FanChannel("testchip", 1, pwm, None)

    with pytest.raises(ValueError):
        fan.set_percent(101)


def test_set_percent_restores_mode_after_failed_write(tmp_path: Path) -> None:
    enable = tmp_path / "pwm1_enable"
    enable.write_text("2")
    fan = FanChannel("testchip", 1, tmp_path / "missing" / "pwm1", enable)

    with pytest.raises(FanControlError):
        fan.set_percent(50)

    assert enable.read_text() == "2"


def test_set_automatic_mode(tmp_path: Path) -> None:
    pwm = tmp_path / "pwm1"
    enable = tmp_path / "pwm1_enable"
    pwm.write_text("128")
    enable.write_text("1")
    fan = FanChannel("testchip", 1, pwm, enable)

    fan.set_automatic()

    assert enable.read_text() == "2"


def test_set_automatic_requires_enable_control(tmp_path: Path) -> None:
    fan = FanChannel("testchip", 1, tmp_path / "pwm1", None)

    with pytest.raises(FanControlError, match="does not expose"):
        fan.set_automatic()


def test_clamps_out_of_range_device_value(tmp_path: Path) -> None:
    pwm = tmp_path / "pwm1"
    pwm.write_text("999")
    fan = FanChannel("testchip", 1, pwm, None)

    assert fan.read_percent() == 100


def test_reports_invalid_numeric_value(tmp_path: Path) -> None:
    pwm = tmp_path / "pwm1"
    pwm.write_text("invalid")
    fan = FanChannel("testchip", 1, pwm, None)

    with pytest.raises(FanControlError, match="Invalid numeric value"):
        fan.read_percent()


def test_ignores_non_pwm_and_invalid_maximum(tmp_path: Path) -> None:
    device = tmp_path / "hwmon0"
    device.mkdir()
    (device / "pwm1_enable").write_text("1")
    (device / "pwm2").write_text("1")
    (device / "pwm2_max").write_text("0")

    assert discover_fans(tmp_path) == []


def test_sorts_fans_by_chip_and_numeric_index(tmp_path: Path) -> None:
    device_b = tmp_path / "hwmon0"
    device_b.mkdir()
    (device_b / "name").write_text("zeta")
    (device_b / "pwm2").write_text("100")
    (device_b / "pwm10").write_text("100")

    device_a = tmp_path / "hwmon1"
    device_a.mkdir()
    (device_a / "name").write_text("Alpha")
    (device_a / "pwm1").write_text("100")

    assert [(fan.chip, fan.index) for fan in discover_fans(tmp_path)] == [
        ("Alpha", 1),
        ("zeta", 2),
        ("zeta", 10),
    ]
