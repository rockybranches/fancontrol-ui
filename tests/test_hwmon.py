from pathlib import Path

import pytest

from fancontrol_ui.hwmon import (
    FanChannel,
    FanControlError,
    discover_fans,
    discover_hwmon,
)


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
    assert fans[0].capabilities.pwm_maximum == 255
    assert fans[0].capabilities.mode_control
    assert fans[0].capabilities.rpm_available
    assert fans[0].capabilities.label_available


def test_discovers_controller_and_temperature_sensor(tmp_path: Path) -> None:
    device = tmp_path / "hwmon0"
    device.mkdir()
    (device / "name").write_text("coretemp\n")
    (device / "temp2_input").write_text("42500\n")
    (device / "temp2_label").write_text("CPU Package\n")
    (device / "temp2_max").write_text("80000\n")
    (device / "temp2_crit").write_text("100000\n")

    controllers = discover_hwmon(tmp_path)

    assert len(controllers) == 1
    controller = controllers[0]
    assert controller.name == "coretemp"
    assert controller.path == device
    assert controller.fans == ()
    assert len(controller.sensors) == 1
    sensor = controller.sensors[0]
    assert sensor.display_name == "CPU Package"
    assert sensor.read_celsius() == 42.5
    assert sensor.read_maximum_celsius() == 80
    assert sensor.read_critical_celsius() == 100
    assert discover_fans(tmp_path) == []


def test_temperature_sensor_read_errors_use_domain_error(tmp_path: Path) -> None:
    device = tmp_path / "hwmon0"
    device.mkdir()
    (device / "temp1_input").write_text("not-a-temperature")
    sensor = discover_hwmon(tmp_path)[0].sensors[0]

    with pytest.raises(FanControlError, match="Invalid numeric value"):
        sensor.read_celsius()


def test_fan_capabilities_report_optional_files(tmp_path: Path) -> None:
    pwm = tmp_path / "pwm1"
    pwm.write_text("100")
    fan = FanChannel("testchip", 1, pwm, None, maximum=200)

    assert fan.capabilities.pwm_available
    assert fan.capabilities.pwm_maximum == 200
    assert not fan.capabilities.mode_control
    assert not fan.capabilities.rpm_available
    assert not fan.capabilities.label_available
    assert not fan.capabilities.minimum_control
    assert not fan.capabilities.maximum_control
    assert not fan.capabilities.target_control
    assert not fan.capabilities.pulses_control
    assert fan.capabilities.configurable


def test_discovers_rpm_only_fan_endpoint(tmp_path: Path) -> None:
    device = tmp_path / "hwmon0"
    device.mkdir()
    (device / "name").write_text("tachometer\n")
    (device / "fan3_input").write_text("1725\n")
    (device / "fan3_label").write_text("Case Fan\n")

    fan = discover_fans(tmp_path)[0]

    assert fan.index == 3
    assert fan.pwm_path is None
    assert fan.device_directory == device
    assert fan.identity == (device, 3)
    assert fan.display_name == "Case Fan"
    assert fan.read_rpm() == 1725
    assert not fan.capabilities.pwm_available
    assert fan.capabilities.rpm_available
    assert not fan.capabilities.configurable


def test_discovers_and_changes_non_pwm_fan_settings(tmp_path: Path) -> None:
    device = tmp_path / "hwmon0"
    device.mkdir()
    (device / "fan2_min").write_text("700\n")
    (device / "fan2_max").write_text("2200\n")
    (device / "fan2_target").write_text("1400\n")
    (device / "fan2_pulses").write_text("2\n")

    fan = discover_fans(tmp_path)[0]

    assert fan.pwm_path is None
    assert fan.read_minimum_rpm() == 700
    assert fan.read_maximum_rpm() == 2200
    assert fan.read_target_rpm() == 1400
    assert fan.read_pulses() == 2
    assert fan.capabilities.minimum_control
    assert fan.capabilities.maximum_control
    assert fan.capabilities.target_control
    assert fan.capabilities.pulses_control

    fan.set_minimum_rpm(850)
    fan.set_maximum_rpm(2400)
    fan.set_target_rpm(1600)
    fan.set_pulses(4)

    assert (device / "fan2_min").read_text() == "850"
    assert (device / "fan2_max").read_text() == "2400"
    assert (device / "fan2_target").read_text() == "1600"
    assert (device / "fan2_pulses").read_text() == "4"


def test_discovers_and_changes_enable_and_divisor_controls(tmp_path: Path) -> None:
    device = tmp_path / "hwmon0"
    device.mkdir()
    (device / "fan6_enable").write_text("1\n")
    (device / "fan6_div").write_text("2\n")

    fan = discover_fans(tmp_path)[0]

    assert fan.pwm_path is None
    assert fan.capabilities.enable_control
    assert fan.capabilities.divisor_control
    assert fan.read_enabled() == 1
    assert fan.read_divisor() == 2

    fan.set_enabled(0)
    fan.set_divisor(4)

    assert (device / "fan6_enable").read_text() == "0"
    assert (device / "fan6_div").read_text() == "4"


def test_discovers_enable_control_without_pwm(tmp_path: Path) -> None:
    device = tmp_path / "hwmon0"
    device.mkdir()
    enable = device / "pwm4_enable"
    enable.write_text("1\n")

    fan = discover_fans(tmp_path)[0]

    assert fan.pwm_path is None
    assert fan.capabilities.mode_control
    fan.set_automatic()
    assert enable.read_text() == "2"


def test_non_pwm_setting_errors_use_domain_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    minimum = tmp_path / "fan1_min"
    minimum.write_text("500")
    fan = FanChannel("testchip", 1, None, None, minimum_path=minimum)
    original_write_text = Path.write_text

    def deny_write(path: Path, *args: object, **kwargs: object) -> int:
        if path == minimum:
            raise PermissionError(13, "Permission denied", path)
        return original_write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", deny_write)

    with pytest.raises(FanControlError, match="Could not write.*Permission denied"):
        fan.set_minimum_rpm(600)


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


def test_discovers_mode_only_endpoint_and_ignores_invalid_pwm_maximum(tmp_path: Path) -> None:
    device = tmp_path / "hwmon0"
    device.mkdir()
    (device / "pwm1_enable").write_text("1")
    (device / "pwm2").write_text("1")
    (device / "pwm2_max").write_text("0")

    fans = discover_fans(tmp_path)

    assert [(fan.index, fan.pwm_path) for fan in fans] == [(1, None)]


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
