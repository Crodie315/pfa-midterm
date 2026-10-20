"""Ripple: pass a driver object's animation to other selected objects,
each one later (delay) and weaker (falloff).

Run in Maya's Script Editor (Python tab):
    import sys, importlib
    sys.path.append(r"PATH/TO/YOUR/REPO")   # folder that contains ripple.py
    import ripple; importlib.reload(ripple); ripple.show()

Status of this file (week 1 starter):
    DONE  window with every control, Load Selection, live graph + dots,
          Apply for Translate/Rotate/Scale in selection order, one undo chunk,
          error messages.
    TODO  week 2-3: Order dropdown, real driver curve polish, Preview/Revert,
          presets (save/load JSON), remembering settings (optionVar),
          copying the driver's tangent types.
"""

import maya.cmds as cmds
import maya.OpenMayaUI as omui

try:  # Maya 2025+
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:  # Maya 2024 and earlier
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance


CHANNELS = {
    "Translate": ["translateX", "translateY", "translateZ"],
    "Rotate": ["rotateX", "rotateY", "rotateZ"],
    "Scale": ["scaleX", "scaleY", "scaleZ"],
}


def maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)


# --------------------------------------------------------------------------
# Core logic (no UI) - easy to test on its own
# --------------------------------------------------------------------------

def ripple_apply(driver, followers, attrs, delay, falloff):
    """Copy the driver's change in motion onto each follower.

    Each follower keeps its own starting value (rest) and adds the driver's
    change, scaled by falloff ** step and shifted later by delay * step frames.
    Returns a list of warnings (skipped locked channels, etc.).
    """
    warnings = []
    used_any = False
    cmds.undoInfo(openChunk=True, chunkName="Ripple")
    try:
        for attr in attrs:
            times = cmds.keyframe(driver, attribute=attr, query=True, timeChange=True)
            if not times:
                continue
            values = cmds.keyframe(driver, attribute=attr, query=True, valueChange=True)
            base = values[0]
            used_any = True

            for step, obj in enumerate(followers, start=1):
                plug = "{}.{}".format(obj, attr)
                if not cmds.attributeQuery(attr, node=obj, exists=True):
                    continue
                if cmds.getAttr(plug, lock=True):
                    warnings.append("{} is locked, skipped".format(plug))
                    continue

                rest = cmds.getAttr(plug, time=times[0])
                strength = falloff ** step
                cmds.cutKey(obj, attribute=attr, clear=True)
                for t, v in zip(times, values):
                    cmds.setKeyframe(
                        obj,
                        attribute=attr,
                        time=t + delay * step,
                        value=rest + (v - base) * strength,
                    )
    finally:
        cmds.undoInfo(closeChunk=True)

    if not used_any:
        raise ValueError("The driver has no keys on the checked channels.")
    return warnings


def driver_curve(driver, attrs):
    """Return [(frame, value), ...] for the first animated channel, or None."""
    for attr in attrs:
        times = cmds.keyframe(driver, attribute=attr, query=True, timeChange=True)
        if times and len(times) > 1:
            values = cmds.keyframe(driver, attribute=attr, query=True, valueChange=True)
            if max(values) != min(values):
                return list(zip(times, values))
    return None


# --------------------------------------------------------------------------
# Live graph widget
# --------------------------------------------------------------------------

class RippleGraph(QtWidgets.QWidget):
    """Draws one curve per object plus a row of dots. Redraws on every change."""

    DRIVER = QtGui.QColor(83, 74, 183)
    FOLLOWER = QtGui.QColor(127, 119, 221)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.count, self.delay, self.falloff = 5, 3, 0.8
        self.curve = None  # None = sample wave

    def set_params(self, count, delay, falloff):
        self.count, self.delay, self.falloff = max(2, count), delay, falloff
        self.update()

    def set_curve(self, curve):
        self.curve = curve
        self.update()

    def _driver_value(self, t):
        if self.curve is None:  # sample: a decaying bounce
            import math
            if t < 0:
                return 0.0
            return math.sin(t / 72.0 * 4 * math.pi) * math.exp(-t / 60.0)
        frames = [f for f, _ in self.curve]
        values = [v for _, v in self.curve]
        start, base = frames[0], values[0]
        t += start
        if t <= frames[0]:
            return 0.0
        if t >= frames[-1]:
            return values[-1] - base
        for i in range(len(frames) - 1):
            if frames[i] <= t <= frames[i + 1]:
                k = (t - frames[i]) / float(frames[i + 1] - frames[i])
                return values[i] + (values[i + 1] - values[i]) * k - base
        return 0.0

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor(42, 42, 42))

        w, h = self.width(), self.height()
        left, right, top, graph_bottom = 12, w - 12, 12, h - 50
        mid = (top + graph_bottom) / 2.0
        length = 72
        if self.curve:
            length = int(self.curve[-1][0] - self.curve[0][0]) or 72
        frames = length + self.delay * (self.count - 1)
        sx = (right - left) / float(max(frames, 1))

        peak = max(abs(self._driver_value(f)) for f in range(length + 1)) or 1.0
        amp = (graph_bottom - top) / 2.0 * 0.9 / peak

        p.setPen(QtGui.QPen(QtGui.QColor(80, 80, 80), 1))
        p.drawLine(int(left), int(mid), int(right), int(mid))

        for i in reversed(range(self.count)):
            color = QtGui.QColor(self.DRIVER if i == 0 else self.FOLLOWER)
            color.setAlphaF(1.0 - i / float(self.count + 1))
            p.setPen(QtGui.QPen(color, 2.5 if i == 0 else 1.5))
            strength = self.falloff ** i
            path = QtGui.QPainterPath()
            for f in range(frames + 1):
                v = self._driver_value(f - i * self.delay) * strength
                x, y = left + f * sx, mid - v * amp
                if f == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            p.drawPath(path)

        dots_y = h - 24
        gap = (right - left - 20) / float(self.count - 1)
        p.setPen(QtGui.QPen(QtGui.QColor(80, 80, 80), 1))
        p.drawLine(int(left + 10), int(dots_y), int(right - 10), int(dots_y))
        p.setPen(QtCore.Qt.NoPen)
        for i in range(self.count):
            color = QtGui.QColor(self.DRIVER if i == 0 else self.FOLLOWER)
            color.setAlphaF(1.0 - i / float(self.count + 1))
            p.setBrush(color)
            r = max(3.0, 12.0 * self.falloff ** i)
            p.drawEllipse(QtCore.QPointF(left + 10 + i * gap, dots_y), r, r)
        p.end()


# --------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------

class RippleWindow(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent or maya_main_window())
        self.setWindowTitle("Ripple")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.setMinimumWidth(380)
        self.driver, self.followers = None, []
        self._build_ui()
        self._refresh_graph()

    # ---- layout ----------------------------------------------------------
    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Preset:"))
        self.preset_box = QtWidgets.QComboBox()
        self.preset_box.addItems(["Custom", "Floppy Tail", "Wave Pop", "Domino Spin", "Heavy Rope"])
        row.addWidget(self.preset_box, 1)
        self.save_btn = QtWidgets.QPushButton("Save")
        row.addWidget(self.save_btn)
        layout.addLayout(row)

        self.driver_label = QtWidgets.QLabel("Driver: (none)")
        layout.addWidget(self.driver_label)
        self.object_list = QtWidgets.QListWidget()
        self.object_list.setMaximumHeight(90)
        layout.addWidget(self.object_list)
        self.load_btn = QtWidgets.QPushButton("Load Selection")
        self.load_btn.setToolTip("First selected object = driver, the rest = followers")
        layout.addWidget(self.load_btn)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Order:"))
        self.order_box = QtWidgets.QComboBox()
        self.order_box.addItems(["Selection order", "Distance from driver", "Left to right (X)"])
        row.addWidget(self.order_box, 1)
        layout.addLayout(row)

        self.delay_slider, delay_row = self._slider("Delay per object", 0, 20, 3, " fr")
        self.falloff_slider, falloff_row = self._slider("Falloff", 10, 100, 80, " %")
        layout.addLayout(delay_row)
        layout.addLayout(falloff_row)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Channels:"))
        self.channel_boxes = {}
        for name in CHANNELS:
            box = QtWidgets.QCheckBox(name)
            box.setChecked(name != "Scale")
            self.channel_boxes[name] = box
            row.addWidget(box)
        layout.addLayout(row)

        self.graph = RippleGraph()
        layout.addWidget(self.graph)

        row = QtWidgets.QHBoxLayout()
        self.preview_btn = QtWidgets.QPushButton("Preview")
        self.revert_btn = QtWidgets.QPushButton("Revert")
        self.apply_btn = QtWidgets.QPushButton("Apply")
        for b in (self.preview_btn, self.revert_btn, self.apply_btn):
            row.addWidget(b)
        layout.addLayout(row)

        self.status = QtWidgets.QLabel("Ready. Select a driver, then the objects to follow.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.load_btn.clicked.connect(self.load_selection)
        self.apply_btn.clicked.connect(self.apply)
        self.preview_btn.clicked.connect(lambda: self._todo("Preview"))
        self.revert_btn.clicked.connect(lambda: self._todo("Revert"))
        self.save_btn.clicked.connect(lambda: self._todo("Saving presets"))
        self.delay_slider.valueChanged.connect(self._refresh_graph)
        self.falloff_slider.valueChanged.connect(self._refresh_graph)
        for box in self.channel_boxes.values():
            box.toggled.connect(self._refresh_curve)

    def _slider(self, label, lo, hi, value, suffix):
        row = QtWidgets.QHBoxLayout()
        name = QtWidgets.QLabel(label)
        name.setMinimumWidth(110)
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(value)
        readout = QtWidgets.QLabel("{}{}".format(value, suffix))
        readout.setMinimumWidth(44)
        slider.valueChanged.connect(lambda v: readout.setText("{}{}".format(v, suffix)))
        row.addWidget(name)
        row.addWidget(slider, 1)
        row.addWidget(readout)
        return slider, row

    # ---- helpers ---------------------------------------------------------
    def _attrs(self):
        attrs = []
        for name, box in self.channel_boxes.items():
            if box.isChecked():
                attrs.extend(CHANNELS[name])
        return attrs

    def _say(self, text, error=False):
        color = "#e57373" if error else "#c8c8c8"
        self.status.setText('<span style="color:{}">{}</span>'.format(color, text))

    def _todo(self, feature):
        self._say("{} is planned for week 3.".format(feature))

    def _refresh_graph(self, *_):
        count = len(self.followers) + 1 if self.driver else 5
        self.graph.set_params(count, self.delay_slider.value(), self.falloff_slider.value() / 100.0)

    def _refresh_curve(self, *_):
        if self.driver and cmds.objExists(self.driver):
            self.graph.set_curve(driver_curve(self.driver, self._attrs()))

    # ---- actions ---------------------------------------------------------
    def load_selection(self):
        sel = cmds.ls(selection=True, type="transform")
        if len(sel) < 2:
            self._say("Select at least 2 objects: the driver first, then the followers.", error=True)
            return
        self.driver, self.followers = sel[0], sel[1:]
        self.driver_label.setText("Driver: {}".format(self.driver))
        self.object_list.clear()
        self.object_list.addItems(self.followers)
        self._refresh_curve()
        self._refresh_graph()
        self._say("Loaded {} followers.".format(len(self.followers)))

    def apply(self):
        if not self.driver:
            self._say("Click Load Selection first.", error=True)
            return
        missing = [o for o in [self.driver] + self.followers if not cmds.objExists(o)]
        if missing:
            self._say("These objects no longer exist: {}. Load Selection again.".format(", ".join(missing)), error=True)
            return
        attrs = self._attrs()
        if not attrs:
            self._say("Check at least one channel.", error=True)
            return
        try:
            warnings = ripple_apply(
                self.driver, self.followers, attrs,
                self.delay_slider.value(), self.falloff_slider.value() / 100.0,
            )
        except ValueError as exc:
            self._say(str(exc), error=True)
            return
        msg = "Rippled {} objects. Ctrl+Z undoes it in one step.".format(len(self.followers))
        if warnings:
            msg += " " + "; ".join(warnings)
        self._say(msg)


_window = None


def show():
    global _window
    if _window is not None:
        try:
            _window.close()
            _window.deleteLater()
        except RuntimeError:
            pass
    _window = RippleWindow()
    _window.show()
    return _window
