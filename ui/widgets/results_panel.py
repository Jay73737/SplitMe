from PyQt6.QtWidgets import QFrame, QScrollArea, QWidget, QGridLayout, QVBoxLayout
from PyQt6.QtCore    import Qt, QTimer
from PyQt6.QtGui     import QPainter, QColor, QConicalGradient, QPen
from .card           import ResultCard

class SearchResults(QFrame):
    """4×2 grid of ResultCards with subtle white animated outline."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMaximumHeight(0)
        self.angle = 0.0
        QTimer(self, interval=40, timeout=self._spin).start()

        self.scroll = QScrollArea(widgetResizable=True, frameShape=QScrollArea.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background:transparent;border:0;")

        self.content = QWidget()
        self.content.setStyleSheet("background:transparent;")
        self.grid = QGridLayout(self.content)
        self.grid.setContentsMargins(12, 12, 12, 12); self.grid.setSpacing(12)
        for c in range(4): self.grid.setColumnStretch(c, 1)

        self.scroll.setWidget(self.content)
        QVBoxLayout(self).addWidget(self.scroll)

    def _spin(self): self.angle = (self.angle + 1.5) % 360; self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(0, 0, 0, 160))
        p.drawRoundedRect(rect, 20, 20)
        g = QConicalGradient(rect.center().toPointF(), self.angle)
        g.setColorAt(0, QColor("white")); g.setColorAt(1, QColor("white"))
        p.setPen(QPen(g, 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 20, 20)

    def set_results(self, metas):
        # ui/widgets/results_panel.py   inside set_results()
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                # stop any active timers before deleting
                for child in w.findChildren(QObject):
                    if isinstance(child, QTimer):
                        child.stop()
                w.deleteLater()