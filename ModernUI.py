import sys, requests, json
from PyQt6.QtCore import (
    Qt, QTimer, QPoint, QEvent, QRectF,
    QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QConicalGradient, QPixmap
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFrame, QScrollArea,
    QStackedLayout, QGraphicsOpacityEffect, QSizePolicy
)

import json
# defining constants because i cant be fucked to type these out every time
WIDTH, HEIGHT = 800, 80
BORDER        = 6
R_OUTER       = HEIGHT // 2
R_INNER       = R_OUTER - BORDER
FILL          = QColor(25, 20, 35, 220)
CLR_A         = QColor("#ff00a1")
CLR_B         = QColor("#2a00ff")
CYCLE_MS      = 2200

# outer neon stroke border 
class AnimatedBorder(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.angle = 0.0
        self.timer = QTimer(self, timeout=self._spin, interval=35)
        self.timer.start()

    def _spin(self):
        self.angle = (self.angle + 1.2) % 360
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # use ints for adjusted() to avoid deprecation warning cuz these motherfuckers love to deprec every fucking thing and the warnings annoy me 
        rect = self.rect().adjusted(BORDER // 2, BORDER // 2,
                                    -BORDER // 2, -BORDER // 2)
        # centre coords as floats for QConicalGradient
        cx, cy = float(rect.center().x()), float(rect.center().y())
        g = QConicalGradient(cx, cy, -self.angle)
        g.setColorAt(0.0, CLR_A)
        g.setColorAt(0.5, CLR_B)
        g.setColorAt(1.0, CLR_A)
        p.setPen(QPen(QBrush(g), BORDER))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, R_OUTER, R_OUTER)

class PlaceholderAnimator:
    def __init__(self, label: QLabel, msgs: list[str]):
        self.lbl, self.msgs, self.idx = label, msgs, 0
        self.fx = QGraphicsOpacityEffect(label); label.setGraphicsEffect(self.fx)
        self.out = QPropertyAnimation(self.fx, b"opacity", duration=400,
                                      startValue=1.0, endValue=0.0)
        self._swap = QPropertyAnimation(self.fx, b"opacity", duration=400,
                                        startValue=0.0, endValue=1.0)
        self.seq = QTimer(singleShot=True, interval=CYCLE_MS, timeout=self._cycle)
        self.seq.start()

    def _cycle(self):
        self.out.finished.connect(self._set_next)
        self.out.start()

    def _set_next(self):
        self.out.finished.disconnect(self._set_next)
        self.idx = (self.idx + 1) % len(self.msgs)
        self.lbl.setText(self.msgs[self.idx])
        self._swap.finished.connect(lambda: self.seq.start())
        self._swap.start()

    def stop(self):
        self.seq.stop(); self.out.stop(); self._swap.stop(); self.fx.setOpacity(1)

    def start(self):
        if not self.seq.isActive():
            self.seq.start(CYCLE_MS)

# jsut some UI components for the results to be loaded in special shaped cards ill finish these later
class ResultCard(QFrame):
    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:rgba(0,0,0,180);border-radius:10px;")
        v = QVBoxLayout(self); v.setContentsMargins(8, 8, 8, 8)
        thumb = QLabel()
        if info.get("thumbnail"):
            try:
                data = requests.get(info["thumbnail"]).content
                pm   = QPixmap(); pm.loadFromData(data)
                thumb.setPixmap(pm.scaled(160, 90,
                                          Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))
            except Exception:
                pass
        title = QLabel(info.get("title", ""))
        title.setStyleSheet("color:white;")
        dur   = QLabel(info.get("duration", ""))
        dur.setStyleSheet("color:white;font-size:8px;")
        v.addWidget(thumb); v.addWidget(title); v.addWidget(dur)
        
# where we dynamically get the results to display, let me know how you wanna handle the API key jay cuz i have one saved in the config json file but idk if you wanna just use that one and hide it when we package it jsut let me know homie
class SearchResults(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)
        self.setMaximumHeight(0)
        self.rad, self.angle = 20, 0.0
        QTimer(self, timeout=self._spin, interval=40).start()

        self.scroll = QScrollArea(widgetResizable=True, frameShape=QScrollArea.Shape.NoFrame)
        self.content = QWidget()
        self.hbox = QHBoxLayout(self.content)
        self.hbox.setContentsMargins(12, 12, 12, 12)
        self.scroll.setWidget(self.content)
        QVBoxLayout(self).addWidget(self.scroll)

    def _spin(self):
        self.angle = (self.angle + 1.5) % 360
        self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 160))
        p.drawRoundedRect(rect, self.rad, self.rad)
        g = QConicalGradient(float(rect.center().x()), float(rect.center().y()), self.angle)
        g.setColorAt(0, QColor("white")); g.setColorAt(1, QColor("white"))
        p.setPen(QPen(QBrush(g), 2))
        p.drawRoundedRect(rect, self.rad, self.rad)

    def set_results(self, items: list[dict]):
        while self.hbox.count():
            self.hbox.takeAt(0).widget().deleteLater()
        for it in items:
            self.hbox.addWidget(ResultCard(it))

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WIDTH, HEIGHT)
        self.drag_offset = QPoint()

        self.border = AnimatedBorder(self)
        self.border.setGeometry(0, 0, WIDTH, HEIGHT)

        # inner pill
        inner = QWidget(self)
        inner.setGeometry(BORDER, BORDER, WIDTH - 2*BORDER, HEIGHT - 2*BORDER)
        inner.setStyleSheet(f"background: rgba({FILL.red()},{FILL.green()},{FILL.blue()},{FILL.alpha()});"
                            f"border-radius:{R_INNER}px;")

        cont = QWidget(inner); cont.setGeometry(0, 0, inner.width(), inner.height())
        st   = QStackedLayout(cont); st.setStackingMode(QStackedLayout.StackingMode.StackAll)
        st.setContentsMargins(30, 0, 30, 0)

        self.search = QLineEdit()
        self.search.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.search.setStyleSheet("background:transparent;color:white;font:22px;border:0;")
        self.search.installEventFilter(self)

        self.ph = QLabel("Drop in a file...")
        self.ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ph.setStyleSheet("color:white;font:22px;")

        st.addWidget(self.search); st.addWidget(self.ph)
        self.anim = PlaceholderAnimator(self.ph,
                                        ["Drop in a file...", "Paste a URL...", "Type and search..."])

        # results panel
        self.results = SearchResults(self); self.results.hide()
        self.results.move(0, HEIGHT + 8)

    def eventFilter(self, obj, ev):
        if obj is self.search:
            if ev.type() == QEvent.Type.FocusIn:
                self.ph.hide(); self.anim.stop()
            elif ev.type() == QEvent.Type.FocusOut and not self.search.text():
                self.ph.show(); self.anim.start()
        return super().eventFilter(obj, ev)
# This part is where we fucking get the window to be draggable no matter where tf you decide to click on it 
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self.drag_offset)
            e.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow(); win.show()
    sys.exit(app.exec())