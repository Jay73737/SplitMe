from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore    import Qt, QTimer, QRectF
from PyQt6.QtGui     import QPainter, QPainterPath, QPen, QBrush, \
                             QConicalGradient, QRadialGradient, QColor
from ..constants     import BORDER, R_OUTER, CLR_A, CLR_B

class AnimatedBorder(QWidget):
    """Spinning gradient ring + halo behind pill."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0.0
        QTimer(self, interval=35, timeout=self._spin).start()

    def _spin(self):
        self.angle = (self.angle + 1.2) % 360
        self.update()

    # ------------------------------------------------------------------ paint
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(BORDER/2, BORDER/2,
                                    -BORDER/2, -BORDER/2)
        cx, cy = rect.center().x(), rect.center().y()

        # halo
        halo_path = QPainterPath()
        halo_rect = rect.adjusted(-25, -25, 25, 25)
        halo_path.addRoundedRect(QRectF(halo_rect), R_OUTER+25, R_OUTER+25)
        grad = QRadialGradient(cx, cy, halo_rect.width()/2)
        grad.setColorAt(0, QColor(255, 0, 255, 80))
        grad.setColorAt(1, QColor(255, 0, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)
        p.drawPath(halo_path)

        # ring
        ring = QConicalGradient(cx, cy, -self.angle)
        ring.setColorAt(0, CLR_A)
        ring.setColorAt(0.5, CLR_B)
        ring.setColorAt(1, CLR_A)
        p.setPen(QPen(QBrush(ring), BORDER))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, R_OUTER, R_OUTER)