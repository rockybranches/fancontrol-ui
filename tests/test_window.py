from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QGraphicsView,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
)

from fancontrol_ui.hwmon import FanChannel, HwmonController, TemperatureSensor
from fancontrol_ui.window import MAX_SAMPLES, FanControlWindow


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_empty_state(app: QApplication) -> None:
    window = FanControlWindow(discover=lambda: [])

    labels = [label.text() for label in window.findChildren(QLabel)]
    assert "No fan endpoints were found." in labels
    assert "Check that your fan controller exposes Linux hwmon fan files." in labels
    window.close()


def test_slider_applies_speed(app: QApplication, tmp_path: Path) -> None:
    pwm = tmp_path / "pwm1"
    enable = tmp_path / "pwm1_enable"
    pwm.write_text("128")
    enable.write_text("2")
    fan = FanChannel("testchip", 1, pwm, enable, label="CPU Fan")
    window = FanControlWindow(discover=lambda: [fan])
    slider = window.findChild(QSlider, f"fan-{tmp_path.name}-1-slider")

    assert slider is not None
    assert slider.value() == 50
    slider.setValue(60)
    slider.sliderReleased.emit()

    assert pwm.read_text() == "153"
    assert enable.read_text() == "1"
    assert "Set CPU Fan to 60%." in [label.text() for label in window.findChildren(QLabel)]
    window.close()


def test_automatic_button_restores_driver_control(app: QApplication, tmp_path: Path) -> None:
    pwm = tmp_path / "pwm2"
    enable = tmp_path / "pwm2_enable"
    pwm.write_text("128")
    enable.write_text("1")
    fan = FanChannel("testchip", 2, pwm, enable)
    window = FanControlWindow(discover=lambda: [fan])
    button = window.findChild(QPushButton, f"fan-{tmp_path.name}-2-automatic")

    assert button is not None
    button.click()

    assert enable.read_text() == "2"
    assert "Returned testchip fan 2 to automatic control." in [
        label.text() for label in window.findChildren(QLabel)
    ]
    window.close()


def test_automatic_button_is_hidden_without_mode_control(
    app: QApplication, tmp_path: Path
) -> None:
    pwm = tmp_path / "pwm3"
    pwm.write_text("128")
    fan = FanChannel("testchip", 3, pwm, None)
    window = FanControlWindow(discover=lambda: [fan])
    button = window.findChild(QPushButton, f"fan-{tmp_path.name}-3-automatic")

    assert button is None
    window.close()


def test_non_pwm_minimum_setting_is_configurable(
    app: QApplication, tmp_path: Path
) -> None:
    minimum = tmp_path / "fan2_min"
    rpm = tmp_path / "fan2_input"
    minimum.write_text("650")
    rpm.write_text("1200")
    fan = FanChannel(
        "testchip",
        2,
        None,
        None,
        label="Case Fan",
        rpm_path=rpm,
        minimum_path=minimum,
        device_path=tmp_path,
    )
    window = FanControlWindow(discover=lambda: [fan])
    spinbox = window.findChild(QSpinBox, f"fan-{tmp_path.name}-2-minimum")
    apply_button = window.findChild(
        QPushButton, f"fan-{tmp_path.name}-2-minimum-apply"
    )

    assert spinbox is not None
    assert apply_button is not None
    assert spinbox.value() == 650
    assert window.findChild(QSlider, f"fan-{tmp_path.name}-2-slider") is None
    spinbox.setValue(800)
    apply_button.click()

    assert minimum.read_text() == "800"
    assert "Set Case Fan minimum rpm to 800." in [
        label.text() for label in window.findChildren(QLabel)
    ]
    window.close()


def test_rpm_only_fan_is_monitoring_only(app: QApplication, tmp_path: Path) -> None:
    rpm = tmp_path / "fan5_input"
    rpm.write_text("900")
    fan = FanChannel(
        "testchip", 5, None, None, rpm_path=rpm, device_path=tmp_path
    )
    controller = HwmonController("testchip", tmp_path, fans=(fan,))
    window = FanControlWindow(
        discover=lambda: [], discover_hardware=lambda: [controller]
    )

    monitoring = window.findChild(
        QLabel, f"fan-{tmp_path.name}-5-monitoring-only"
    )
    assert monitoring is not None
    assert "Monitoring only" in monitoring.text()
    assert window.findChild(QSlider, f"fan-{tmp_path.name}-5-slider") is None
    assert window.findChild(QPushButton, f"fan-{tmp_path.name}-5-automatic") is None

    _select_node(window, "fan:")
    app.processEvents()

    details = window.findChild(QLabel, "analysis-details").text()
    summary = window.findChild(QLabel, "analysis-history-summary").text()
    assert "PWM control: no" in details
    assert "RPM telemetry: yes" in details
    assert "900.0 RPM now" in summary
    assert f"fan:{tmp_path}:5:rpm" in window._history
    window.close()


def test_mode_control_without_pwm_exposes_automatic_only(
    app: QApplication, tmp_path: Path
) -> None:
    enable = tmp_path / "pwm4_enable"
    enable.write_text("1")
    fan = FanChannel(
        "testchip", 4, None, enable, device_path=tmp_path
    )
    window = FanControlWindow(discover=lambda: [fan])
    button = window.findChild(QPushButton, f"fan-{tmp_path.name}-4-automatic")

    assert button is not None
    assert window.findChild(QSlider, f"fan-{tmp_path.name}-4-slider") is None
    button.click()

    assert enable.read_text() == "2"
    window.close()


def test_fan_enable_and_divisor_are_configurable(
    app: QApplication, tmp_path: Path
) -> None:
    enabled = tmp_path / "fan6_enable"
    divisor = tmp_path / "fan6_div"
    enabled.write_text("1")
    divisor.write_text("2")
    fan = FanChannel(
        "testchip",
        6,
        None,
        None,
        fan_enable_path=enabled,
        divisor_path=divisor,
        device_path=tmp_path,
    )
    window = FanControlWindow(discover=lambda: [fan])
    enabled_box = window.findChild(QSpinBox, f"fan-{tmp_path.name}-6-enabled")
    enabled_apply = window.findChild(
        QPushButton, f"fan-{tmp_path.name}-6-enabled-apply"
    )
    divisor_box = window.findChild(QSpinBox, f"fan-{tmp_path.name}-6-divisor")
    divisor_apply = window.findChild(
        QPushButton, f"fan-{tmp_path.name}-6-divisor-apply"
    )

    assert enabled_box is not None
    assert enabled_apply is not None
    assert divisor_box is not None
    assert divisor_apply is not None
    enabled_box.setValue(0)
    enabled_apply.click()
    divisor_box.setValue(8)
    divisor_apply.click()

    assert enabled.read_text() == "0"
    assert divisor.read_text() == "8"
    window.close()


def _analysis_hardware(tmp_path: Path) -> tuple[HwmonController, Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    pwm = tmp_path / "pwm1"
    rpm = tmp_path / "fan1_input"
    enable = tmp_path / "pwm1_enable"
    temperature = tmp_path / "temp1_input"
    pwm.write_text("128")
    rpm.write_text("1400")
    enable.write_text("2")
    temperature.write_text("42000")
    fan = FanChannel(
        "testchip", 1, pwm, enable, label="CPU Fan", rpm_path=rpm
    )
    sensor = TemperatureSensor("testchip", 1, temperature, label="CPU Temperature")
    return (
        HwmonController("testchip", tmp_path, fans=(fan,), sensors=(sensor,)),
        temperature,
        rpm,
    )


def _select_node(window: FanControlWindow, prefix: str) -> None:
    view = window.findChild(QGraphicsView, "analysis-topology")
    assert view is not None
    item = next(item for item in view.scene().items() if str(item.data(0)).startswith(prefix))
    item.setSelected(True)


def test_analysis_diagram_selection_shows_sensor_telemetry(
    app: QApplication, tmp_path: Path
) -> None:
    controller, _temperature, _rpm = _analysis_hardware(tmp_path)
    window = FanControlWindow(
        discover=lambda: [], discover_hardware=lambda: [controller]
    )

    _select_node(window, "temperature:")
    app.processEvents()

    assert window.findChild(QLabel, "analysis-selection-title").text() == "CPU Temperature"
    details = window.findChild(QLabel, "analysis-details").text()
    summary = window.findChild(QLabel, "analysis-history-summary").text()
    assert "Temperature sensor 1" in details
    assert "42.0 °C now" in summary
    assert "1 samples" in summary
    window.close()


def test_fan_analysis_can_graph_pwm_and_rpm_history(
    app: QApplication, tmp_path: Path
) -> None:
    controller, _temperature, _rpm = _analysis_hardware(tmp_path)
    window = FanControlWindow(
        discover=lambda: [], discover_hardware=lambda: [controller]
    )

    _select_node(window, "fan:")
    app.processEvents()
    series = window.findChild(QComboBox, "analysis-history-series")

    assert series is not None
    assert [series.itemText(index) for index in range(series.count())] == [
        "PWM history (%)",
        "Speed history (RPM)",
    ]
    assert window._history_graph._values == [50.0]
    series.setCurrentIndex(1)
    assert window._history_graph._values == [1400.0]
    window.close()


def test_polling_retains_at_most_ten_minutes(
    app: QApplication, tmp_path: Path
) -> None:
    controller, temperature, _rpm = _analysis_hardware(tmp_path)
    window = FanControlWindow(
        discover=lambda: [], discover_hardware=lambda: [controller]
    )
    sensor_key = f"temperature:{temperature}:temperature"

    for value in range(MAX_SAMPLES + 5):
        temperature.write_text(str(value * 1000))
        window._poll_telemetry()

    history = window._history[sensor_key]
    assert len(history) == MAX_SAMPLES
    assert history[0] == 5
    assert history[-1] == MAX_SAMPLES + 4
    assert window._telemetry_timer.isActive()
    assert window._telemetry_timer.interval() == 1000
    window.close()


def test_poll_error_is_visible_and_does_not_stop_timer(
    app: QApplication, tmp_path: Path
) -> None:
    controller, temperature, _rpm = _analysis_hardware(tmp_path)
    window = FanControlWindow(
        discover=lambda: [], discover_hardware=lambda: [controller]
    )
    _select_node(window, "temperature:")
    temperature.unlink()

    window._poll_telemetry()

    error = window.findChild(QLabel, "analysis-telemetry-error")
    assert "Could not read" in error.text()
    assert window._telemetry_timer.isActive()
    window.close()


def test_refresh_replaces_analysis_nodes_and_history(
    app: QApplication, tmp_path: Path
) -> None:
    first, first_temperature, _rpm = _analysis_hardware(tmp_path / "first")
    second_root = tmp_path / "second"
    second_root.mkdir()
    second_temperature = second_root / "temp2_input"
    second_temperature.write_text("35000")
    second = HwmonController(
        "secondchip",
        second_root,
        sensors=(TemperatureSensor("secondchip", 2, second_temperature),),
    )
    discovered = [first]
    window = FanControlWindow(
        discover=lambda: [], discover_hardware=lambda: discovered
    )
    old_series = f"temperature:{first_temperature}:temperature"
    assert old_series in window._history

    discovered[:] = [second]
    window.refresh()

    assert old_series not in window._history
    assert all(str(first.path) not in key for key in window._nodes)
    assert any(str(second_root) in key for key in window._nodes)
    window.close()
