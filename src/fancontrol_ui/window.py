from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from fancontrol_ui.hwmon import FanChannel, FanControlError, discover_fans


class FanControlWindow(QMainWindow):
    def __init__(self, discover: Callable[[], list[FanChannel]] = discover_fans) -> None:
        super().__init__()
        self._discover = discover
        self.setWindowTitle("Fan Control")
        self.setMinimumSize(520, 280)

        root = QWidget()
        layout = QVBoxLayout(root)

        header = QHBoxLayout()
        title = QLabel("Fan speeds")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(refresh_button)
        layout.addLayout(header)

        self._fan_list = QWidget()
        self._fan_layout = QVBoxLayout(self._fan_list)
        self._fan_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._fan_list)
        layout.addWidget(scroll)

        self._status = QLabel()
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self.setCentralWidget(root)
        self.refresh()

    def refresh(self) -> None:
        while self._fan_layout.count():
            item = self._fan_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        try:
            fans = self._discover()
        except FanControlError as exc:
            self._set_error(str(exc))
            return

        if not fans:
            empty = QLabel("No controllable PWM fans were found.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._fan_layout.addWidget(empty)
            self._status.setText("Check that your fan controller exposes Linux hwmon PWM controls.")
            return

        for fan in fans:
            self._fan_layout.addWidget(self._create_fan_row(fan))
        self._status.setStyleSheet("")
        self._status.setText(f"Found {len(fans)} fan control{'s' if len(fans) != 1 else ''}.")

    def _create_fan_row(self, fan: FanChannel) -> QWidget:
        row = QFrame()
        row.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(row)
        control_id = f"{fan.pwm_path.parent.name}-{fan.index}"

        heading = QHBoxLayout()
        name = QLabel(fan.display_name)
        name.setStyleSheet("font-weight: 600;")
        rpm_label = QLabel()
        heading.addWidget(name)
        heading.addStretch()
        heading.addWidget(rpm_label)
        layout.addLayout(heading)

        controls = QHBoxLayout()
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setObjectName(f"fan-{control_id}-slider")
        slider.setRange(0, 100)
        slider.setSingleStep(1)
        slider.setPageStep(5)
        value_label = QLabel()
        value_label.setObjectName(f"fan-{control_id}-value")
        value_label.setMinimumWidth(44)
        automatic_button = QPushButton("Automatic")
        automatic_button.setObjectName(f"fan-{control_id}-automatic")
        automatic_button.setEnabled(fan.enable_path is not None)
        automatic_button.setToolTip("Return this fan to the driver's automatic control mode")

        try:
            value = fan.read_percent()
            rpm = fan.read_rpm()
            slider.setValue(value)
            value_label.setText(f"{value}%")
            rpm_label.setText(f"{rpm:,} RPM" if rpm is not None else "")
        except FanControlError as exc:
            slider.setEnabled(False)
            value_label.setText("--")
            rpm_label.setText("Unavailable")
            self._set_error(str(exc))

        slider.valueChanged.connect(lambda value, label=value_label: label.setText(f"{value}%"))
        slider.sliderReleased.connect(lambda current=slider, channel=fan: self._apply(channel, current.value()))
        automatic_button.clicked.connect(lambda _checked=False, channel=fan: self._set_automatic(channel))
        controls.addWidget(slider)
        controls.addWidget(value_label)
        controls.addWidget(automatic_button)
        layout.addLayout(controls)
        return row

    def _apply(self, fan: FanChannel, percent: int) -> None:
        try:
            fan.set_percent(percent)
        except FanControlError as exc:
            self._set_error(str(exc))
            return

        self._status.setStyleSheet("color: #287a28;")
        self._status.setText(f"Set {fan.display_name} to {percent}%.")

    def _set_automatic(self, fan: FanChannel) -> None:
        try:
            fan.set_automatic()
        except FanControlError as exc:
            self._set_error(str(exc))
            return

        self._status.setStyleSheet("color: #287a28;")
        self._status.setText(f"Returned {fan.display_name} to automatic control.")

    def _set_error(self, message: str) -> None:
        self._status.setStyleSheet("color: #b42318;")
        self._status.setText(message)
