from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QComboBox,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fancontrol_ui.hwmon import (
    FanChannel,
    FanControlError,
    HwmonController,
    TemperatureSensor,
    discover_fans,
    discover_hwmon,
)


MAX_SAMPLES = 600


@dataclass(frozen=True)
class _Node:
    kind: str
    value: HwmonController | TemperatureSensor | FanChannel


class HistoryGraph(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("analysis-history-graph")
        self.setMinimumHeight(110)
        self._values: list[float] = []

    def set_values(self, values: list[float]) -> None:
        self._values = values
        self.update()

    def paintEvent(self, _event: Any) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().base())
        painter.setPen(QPen(self.palette().mid().color(), 1))
        area = self.rect().adjusted(8, 8, -8, -8)
        painter.drawRect(area)
        if not self._values:
            painter.drawText(area, Qt.AlignmentFlag.AlignCenter, "Waiting for telemetry")
            return

        low, high = min(self._values), max(self._values)
        span = high - low or 1
        points = []
        denominator = max(1, len(self._values) - 1)
        for index, value in enumerate(self._values):
            x = area.left() + area.width() * index / denominator
            y = area.bottom() - area.height() * (value - low) / span
            points.append(QPointF(x, y))
        painter.setPen(QPen(QColor("#2878b5"), 2))
        for start, end in zip(points, points[1:]):
            painter.drawLine(start, end)
        if len(points) == 1:
            painter.drawEllipse(points[0], 2, 2)


class FanControlWindow(QMainWindow):
    def __init__(
        self,
        discover: Callable[[], list[FanChannel]] = discover_fans,
        discover_hardware: Callable[[], list[HwmonController]] | None = None,
    ) -> None:
        super().__init__()
        self._discover = discover
        self._discover_hardware = (
            discover_hwmon if discover_hardware is None and discover is discover_fans else discover_hardware
        )
        self._controllers: list[HwmonController] = []
        self._nodes: dict[str, _Node] = {}
        self._history: dict[str, deque[float]] = {}
        self._selected_node: str | None = None
        self._telemetry_errors: dict[str, str] = {}
        self.setWindowTitle("Fan Control")
        self.setMinimumSize(720, 480)

        root = QWidget()
        layout = QVBoxLayout(root)

        header = QHBoxLayout()
        title = QLabel("Fan speeds")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("refresh-button")
        refresh_button.clicked.connect(self.refresh)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(refresh_button)
        layout.addLayout(header)

        tabs = QTabWidget()
        tabs.setObjectName("main-tabs")
        controls_tab = QWidget()
        controls_layout = QVBoxLayout(controls_tab)

        self._fan_list = QWidget()
        self._fan_layout = QVBoxLayout(self._fan_list)
        self._fan_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._fan_list)
        controls_layout.addWidget(scroll)
        tabs.addTab(controls_tab, "Controls")
        tabs.addTab(self._create_analysis_tab(), "Analysis")
        layout.addWidget(tabs)

        self._status = QLabel()
        self._status.setObjectName("status-label")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self.setCentralWidget(root)
        self.refresh()
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.setObjectName("telemetry-timer")
        self._telemetry_timer.setInterval(1000)
        self._telemetry_timer.timeout.connect(self._poll_telemetry)
        self._telemetry_timer.start()

    def _create_analysis_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._scene = QGraphicsScene(self)
        self._scene.selectionChanged.connect(self._topology_selection_changed)
        topology = QGraphicsView(self._scene)
        topology.setObjectName("analysis-topology")
        topology.setRenderHint(QPainter.RenderHint.Antialiasing)
        topology.setMinimumWidth(400)
        splitter.addWidget(topology)

        details = QWidget()
        details_layout = QVBoxLayout(details)
        heading = QLabel("Select a controller, sensor, or fan")
        heading.setObjectName("analysis-selection-title")
        heading.setStyleSheet("font-size: 17px; font-weight: 600;")
        self._analysis_title = heading
        self._analysis_details = QLabel()
        self._analysis_details.setObjectName("analysis-details")
        self._analysis_details.setWordWrap(True)
        self._history_summary = QLabel("No telemetry samples")
        self._history_summary.setObjectName("analysis-history-summary")
        self._history_summary.setWordWrap(True)
        self._history_series = QComboBox()
        self._history_series.setObjectName("analysis-history-series")
        self._history_series.currentIndexChanged.connect(self._history_series_changed)
        self._history_graph = HistoryGraph()
        self._analysis_error = QLabel()
        self._analysis_error.setObjectName("analysis-telemetry-error")
        self._analysis_error.setStyleSheet("color: #b42318;")
        self._analysis_error.setWordWrap(True)
        details_layout.addWidget(heading)
        details_layout.addWidget(self._analysis_details)
        details_layout.addWidget(self._history_summary)
        details_layout.addWidget(self._history_series)
        details_layout.addWidget(self._history_graph)
        details_layout.addWidget(self._analysis_error)
        details_layout.addStretch()
        splitter.addWidget(details)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        return tab

    def refresh(self) -> None:
        while self._fan_layout.count():
            item = self._fan_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        try:
            if self._discover_hardware is not None:
                controllers = self._discover_hardware()
                fans = [fan for controller in controllers for fan in controller.fans]
            else:
                fans = self._discover()
                controllers = self._controllers_from_fans(fans)
        except FanControlError as exc:
            self._controllers = []
            self._history = {}
            self._telemetry_errors = {}
            self._selected_node = None
            self._rebuild_topology()
            self._set_error(str(exc))
            return

        self._controllers = controllers
        self._history = {}
        self._telemetry_errors = {}
        self._selected_node = None
        self._rebuild_topology()

        if not fans:
            empty = QLabel("No fan endpoints were found.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._fan_layout.addWidget(empty)
            if controllers:
                self._status.setText("No fan endpoints found; sensor analysis is still available.")
            else:
                self._status.setText("Check that your fan controller exposes Linux hwmon fan files.")
            self._poll_telemetry()
            return

        self._status.setStyleSheet("")
        self._status.setText(f"Found {len(fans)} fan endpoint{'s' if len(fans) != 1 else ''}.")
        for fan in fans:
            self._fan_layout.addWidget(self._create_fan_row(fan))
        self._poll_telemetry()

    @staticmethod
    def _controllers_from_fans(fans: list[FanChannel]) -> list[HwmonController]:
        grouped: dict[tuple[str, str], list[FanChannel]] = {}
        paths: dict[tuple[str, str], Any] = {}
        for fan in fans:
            device_path = fan.device_directory
            key = (fan.chip, str(device_path))
            grouped.setdefault(key, []).append(fan)
            paths[key] = device_path
        return [
            HwmonController(name=key[0], path=paths[key], fans=tuple(grouped[key]))
            for key in sorted(grouped, key=lambda item: (item[0].casefold(), item[1]))
        ]

    def _rebuild_topology(self) -> None:
        self._scene.clear()
        self._nodes = {}
        self._analysis_title.setText("Select a controller, sensor, or fan")
        self._analysis_details.setText("")
        self._history_summary.setText("No telemetry samples")
        self._history_series.clear()
        self._history_graph.set_values([])
        self._analysis_error.setText("")

        y = 20
        for controller in self._controllers:
            controller_key = f"controller:{controller.path}"
            controller_item = self._add_node(
                controller_key, _Node("controller", controller), 20, y, 170, 54, "#dbeafe"
            )
            children = [
                *[("sensor", sensor) for sensor in controller.sensors],
                *[("fan", fan) for fan in controller.fans],
            ]
            for child_index, (kind, value) in enumerate(children):
                child_y = y + child_index * 72
                if kind == "sensor":
                    key = f"temperature:{value.input_path}"
                    color = "#fee2e2"
                else:
                    key = self._fan_key(controller.path, value.index)
                    color = "#dcfce7"
                child_item = self._add_node(key, _Node(kind, value), 270, child_y, 190, 54, color)
                self._scene.addLine(
                    controller_item.rect().right() + controller_item.pos().x(),
                    controller_item.rect().center().y() + controller_item.pos().y(),
                    child_item.rect().left() + child_item.pos().x(),
                    child_item.rect().center().y() + child_item.pos().y(),
                    QPen(QColor("#64748b"), 2),
                ).setZValue(-1)
            y += max(90, len(children) * 72 + 20)
        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-10, -10, 10, 10))

    def _add_node(
        self, key: str, node: _Node, x: float, y: float, width: float, height: float, color: str
    ) -> QGraphicsRectItem:
        item = self._scene.addRect(
            QRectF(0, 0, width, height), QPen(QColor("#475569"), 1.5), QColor(color)
        )
        item.setPos(x, y)
        item.setData(0, key)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        item.setToolTip(f"Select {node.kind} details")
        label = self._scene.addText(node.value.display_name)
        label.setTextWidth(width - 16)
        label.setPos(x + 8, y + 8)
        label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._nodes[key] = node
        return item

    def _topology_selection_changed(self) -> None:
        selected = [item for item in self._scene.selectedItems() if item.data(0)]
        if not selected:
            return
        self._selected_node = str(selected[0].data(0))
        self._update_analysis_details()

    def _poll_telemetry(self) -> None:
        active_series: set[str] = set()
        self._telemetry_errors = {}
        for key, node in self._nodes.items():
            if node.kind == "sensor":
                self._sample(f"{key}:temperature", node.value.read_celsius, active_series)
            elif node.kind == "fan":
                fan = node.value
                capabilities = fan.capabilities
                if capabilities.pwm_available:
                    self._sample(f"{key}:pwm", fan.read_percent, active_series)
                if capabilities.rpm_available:
                    self._sample(f"{key}:rpm", fan.read_rpm, active_series)
        self._history = {
            key: values for key, values in self._history.items() if key in active_series
        }
        self._update_analysis_details()

    def _sample(
        self, series_key: str, reader: Callable[[], float | int | None], active: set[str]
    ) -> None:
        active.add(series_key)
        try:
            value = reader()
            if value is not None:
                self._history.setdefault(series_key, deque(maxlen=MAX_SAMPLES)).append(float(value))
        except FanControlError as exc:
            node_key = series_key.rsplit(":", 1)[0]
            self._telemetry_errors[node_key] = str(exc)

    def _update_analysis_details(self) -> None:
        if self._selected_node is None or self._selected_node not in self._nodes:
            return
        node = self._nodes[self._selected_node]
        value = node.value
        series: list[tuple[str, str, str]] = []

        if node.kind == "controller":
            controller = value
            self._analysis_title.setText(controller.display_name)
            current_values = []
            for sensor in controller.sensors:
                values = self._history.get(f"temperature:{sensor.input_path}:temperature")
                if values:
                    current_values.append(f"{sensor.display_name}: {values[-1]:.1f} °C")
            for fan in controller.fans:
                fan_key = self._fan_key(controller.path, fan.index)
                pwm_values = self._history.get(f"{fan_key}:pwm")
                rpm_values = self._history.get(f"{fan_key}:rpm")
                if pwm_values or rpm_values:
                    readings = []
                    if pwm_values:
                        readings.append(f"{pwm_values[-1]:.1f}%")
                    if rpm_values:
                        readings.append(f"{rpm_values[-1]:.0f} RPM")
                    current = f"{fan.display_name}: {', '.join(readings)}"
                    current_values.append(current)
            self._analysis_details.setText(
                f"Controller: {controller.path}\n"
                f"Temperature sensors: {len(controller.sensors)}\n"
                f"Fan channels: {len(controller.fans)}"
                + (f"\n\nCurrent telemetry:\n{chr(10).join(current_values)}" if current_values else "")
            )
        elif node.kind == "sensor":
            sensor = value
            self._analysis_title.setText(sensor.display_name)
            limits = []
            try:
                maximum = sensor.read_maximum_celsius()
                critical = sensor.read_critical_celsius()
                if maximum is not None:
                    limits.append(f"Maximum: {maximum:.1f} °C")
                if critical is not None:
                    limits.append(f"Critical: {critical:.1f} °C")
            except FanControlError as exc:
                self._telemetry_errors[self._selected_node] = str(exc)
            self._analysis_details.setText(
                f"Temperature sensor {sensor.index}\n"
                f"Label available: {'yes' if sensor.label else 'no'}"
                + (f"\n{chr(10).join(limits)}" if limits else "")
            )
            series.append(
                (f"{self._selected_node}:temperature", "Temperature", "°C")
            )
        else:
            fan = value
            capabilities = fan.capabilities
            self._analysis_title.setText(fan.display_name)
            details = [
                f"Fan channel {fan.index}",
                f"PWM control: {'yes' if capabilities.pwm_available else 'no'}",
            ]
            if capabilities.pwm_available:
                details.append(f"PWM maximum: {capabilities.pwm_maximum}")
            mode_text = "no"
            if capabilities.mode_control:
                try:
                    mode = fan.read_mode()
                    mode_text = f"yes (current: {mode})"
                except FanControlError as exc:
                    mode_text = "yes (read failed)"
                    self._telemetry_errors[self._selected_node] = str(exc)
            details.extend(
                (
                    f"Mode control: {mode_text}",
                    f"RPM telemetry: {'yes' if capabilities.rpm_available else 'no'}",
                    f"Minimum RPM control: {'yes' if capabilities.minimum_control else 'no'}",
                    f"Maximum RPM control: {'yes' if capabilities.maximum_control else 'no'}",
                    f"Target RPM control: {'yes' if capabilities.target_control else 'no'}",
                    f"Pulses control: {'yes' if capabilities.pulses_control else 'no'}",
                    f"Fan enable control: {'yes' if capabilities.enable_control else 'no'}",
                    f"Fan divisor control: {'yes' if capabilities.divisor_control else 'no'}",
                    f"Label available: {'yes' if capabilities.label_available else 'no'}",
                )
            )
            self._analysis_details.setText("\n".join(details))
            if capabilities.pwm_available:
                series.append((f"{self._selected_node}:pwm", "PWM", "%"))
            if capabilities.rpm_available:
                series.append((f"{self._selected_node}:rpm", "Speed", "RPM"))

        summaries = []
        for series_key, name, unit in series:
            values = list(self._history.get(series_key, ()))
            if values:
                summaries.append(
                    f"{name}: {values[-1]:.1f} {unit} now; "
                    f"{min(values):.1f}–{max(values):.1f}; {len(values)} samples"
                )
        self._history_summary.setText("\n".join(summaries) or "No telemetry samples")
        selected_series = self._history_series.currentData()
        self._history_series.blockSignals(True)
        self._history_series.clear()
        for series_key, name, unit in series:
            self._history_series.addItem(f"{name} history ({unit})", series_key)
        if selected_series is not None:
            selected_index = self._history_series.findData(selected_series)
            if selected_index >= 0:
                self._history_series.setCurrentIndex(selected_index)
        self._history_series.setVisible(bool(series))
        self._history_series.blockSignals(False)
        self._history_series_changed()
        self._analysis_error.setText(self._telemetry_errors.get(self._selected_node, ""))

    def _history_series_changed(self) -> None:
        series_key = self._history_series.currentData()
        self._history_graph.set_values(list(self._history.get(series_key, ())))

    def _create_fan_row(self, fan: FanChannel) -> QWidget:
        row = QFrame()
        row.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(row)
        control_id = f"{fan.device_directory.name}-{fan.index}"
        capabilities = fan.capabilities

        heading = QHBoxLayout()
        name = QLabel(fan.display_name)
        name.setStyleSheet("font-weight: 600;")
        rpm_label = QLabel()
        rpm_label.setObjectName(f"fan-{control_id}-rpm")
        heading.addWidget(name)
        heading.addStretch()
        heading.addWidget(rpm_label)
        layout.addLayout(heading)

        if capabilities.rpm_available:
            try:
                rpm = fan.read_rpm()
                rpm_label.setText(f"{rpm:,} RPM" if rpm is not None else "")
            except FanControlError as exc:
                rpm_label.setText("Unavailable")
                self._set_error(str(exc))

        if capabilities.pwm_available:
            controls = QHBoxLayout()
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setObjectName(f"fan-{control_id}-slider")
            slider.setRange(0, 100)
            slider.setSingleStep(1)
            slider.setPageStep(5)
            value_label = QLabel()
            value_label.setObjectName(f"fan-{control_id}-value")
            value_label.setMinimumWidth(44)
            try:
                value = fan.read_percent()
                slider.setValue(value)
                value_label.setText(f"{value}%")
            except FanControlError as exc:
                slider.setEnabled(False)
                value_label.setText("--")
                self._set_error(str(exc))

            slider.valueChanged.connect(
                lambda value, label=value_label: label.setText(f"{value}%")
            )
            slider.sliderReleased.connect(
                lambda current=slider, channel=fan: self._apply(channel, current.value())
            )
            controls.addWidget(slider)
            controls.addWidget(value_label)
            layout.addLayout(controls)

        if capabilities.mode_control:
            automatic_button = QPushButton("Automatic")
            automatic_button.setObjectName(f"fan-{control_id}-automatic")
            automatic_button.setToolTip(
                "Return this fan to the driver's conventional automatic control mode (2)"
            )
            automatic_button.clicked.connect(
                lambda _checked=False, channel=fan: self._set_automatic(channel)
            )
            layout.addWidget(automatic_button)

        settings = (
            (
                capabilities.minimum_control,
                "minimum",
                "Minimum RPM",
                fan.read_minimum_rpm,
                fan.set_minimum_rpm,
                1_000_000,
            ),
            (
                capabilities.maximum_control,
                "maximum",
                "Maximum RPM",
                fan.read_maximum_rpm,
                fan.set_maximum_rpm,
                1_000_000,
            ),
            (
                capabilities.target_control,
                "target",
                "Target RPM",
                fan.read_target_rpm,
                fan.set_target_rpm,
                1_000_000,
            ),
            (
                capabilities.pulses_control,
                "pulses",
                "Pulses per revolution",
                fan.read_pulses,
                fan.set_pulses,
                255,
            ),
            (
                capabilities.enable_control,
                "enabled",
                "Enabled (0 or 1)",
                fan.read_enabled,
                fan.set_enabled,
                1,
            ),
            (
                capabilities.divisor_control,
                "divisor",
                "Fan divisor",
                fan.read_divisor,
                fan.set_divisor,
                1_000_000,
            ),
        )
        for available, setting_id, description, reader, writer, default_maximum in settings:
            if not available:
                continue
            setting_layout = QHBoxLayout()
            setting_layout.addWidget(QLabel(description))
            spinbox = QSpinBox()
            spinbox.setObjectName(f"fan-{control_id}-{setting_id}")
            spinbox.setRange(0, default_maximum)
            apply_button = QPushButton("Apply")
            apply_button.setObjectName(f"fan-{control_id}-{setting_id}-apply")
            try:
                current_value = reader()
                if current_value is not None:
                    spinbox.setMaximum(max(default_maximum, current_value))
                    spinbox.setValue(current_value)
            except FanControlError as exc:
                spinbox.setEnabled(False)
                apply_button.setEnabled(False)
                self._set_error(str(exc))
            apply_button.clicked.connect(
                lambda _checked=False,
                channel=fan,
                current=spinbox,
                setter=writer,
                setting=description: self._apply_setting(
                    channel, setter, current.value(), setting
                )
            )
            setting_layout.addWidget(spinbox)
            setting_layout.addWidget(apply_button)
            layout.addLayout(setting_layout)

        if not capabilities.configurable:
            monitoring = QLabel("Monitoring only — no configurable controls are exposed.")
            monitoring.setObjectName(f"fan-{control_id}-monitoring-only")
            layout.addWidget(monitoring)
        return row

    @staticmethod
    def _fan_key(controller_path: Any, fan_index: int) -> str:
        return f"fan:{controller_path}:{fan_index}"

    def _apply_setting(
        self,
        fan: FanChannel,
        setter: Callable[[int], None],
        value: int,
        description: str,
    ) -> None:
        try:
            setter(value)
        except (FanControlError, ValueError) as exc:
            self._set_error(str(exc))
            return

        self._status.setStyleSheet("color: #287a28;")
        self._status.setText(f"Set {fan.display_name} {description.lower()} to {value}.")

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
