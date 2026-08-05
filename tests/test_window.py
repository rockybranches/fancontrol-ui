from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QSlider

from fancontrol_ui.hwmon import FanChannel
from fancontrol_ui.window import FanControlWindow


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_empty_state(app: QApplication) -> None:
    window = FanControlWindow(discover=lambda: [])

    labels = [label.text() for label in window.findChildren(QLabel)]
    assert "No controllable PWM fans were found." in labels
    assert "Check that your fan controller exposes Linux hwmon PWM controls." in labels
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


def test_automatic_button_is_disabled_without_mode_control(
    app: QApplication, tmp_path: Path
) -> None:
    pwm = tmp_path / "pwm3"
    pwm.write_text("128")
    fan = FanChannel("testchip", 3, pwm, None)
    window = FanControlWindow(discover=lambda: [fan])
    button = window.findChild(QPushButton, f"fan-{tmp_path.name}-3-automatic")

    assert button is not None
    assert not button.isEnabled()
    window.close()
