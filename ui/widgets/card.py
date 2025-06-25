from __future__ import annotations
import threading, pathlib, requests
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore    import Qt, QTimer, QPoint, QMimeData, QUrl, QPropertyAnimation, QRectF
from PyQt6.QtGui     import QPixmap, QPainter, QPainterPath, QPen, QBrush, \
                             QConicalGradient, QColor, QDrag
from ..models        import VideoMeta
from ..youtube       import download_audio

class ResultCard(QFrame):
    """Thumbnail card with hover border + drag-to-download."""
    def __init__(self, meta: VideoMeta, parent=None):
        super().__init__(parent)
        self.meta         = meta
        self.audio_path   : pathlib.Path | None = None
        self._drag_start  = QPoint()
        self._hover       = False
        self._angle       = 0.0
        self._timer       = QTimer(self, interval=35, timeout=self._spin)
        self._downloading = True
        self._lifted      = False

        self.setStyleSheet("background:rgba(0,0,0,180);border-radius:10px;")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        v = QVBoxLayout(self); v.setContentsMargins(8, 8, 8, 8)

        thumb = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        _load_thumb(meta.thumb_url, thumb)
        v.addWidget(thumb)

        v.addWidget(QLabel(meta.title, styleSheet="color:white;"))
        v.addWidget(QLabel(meta.duration_iso, styleSheet="color:white;font-size:8px;"))

        btn = QPushButton("SOURCE",
                          cursor=Qt.CursorShape.PointingHandCursor,
                          styleSheet="background:#ff0000;color:white;"
                                     "border-radius:4px;padding:4px;")
        btn.clicked.connect(lambda: QUrl(meta.youtube_url).openUrl())  
        h = QHBoxLayout(); h.addWidget(btn); v.addLayout(h)

        threading.Thread(target=self._bg_download, daemon=True).start()

    def _bg_download(self):
        try:
            self.audio_path = download_audio(self.meta.video_id)
        finally:
            self._downloading = False

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.position().toPoint()
            self._orig_pos   = self.pos()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.MouseButton.LeftButton):
            return super().mouseMoveEvent(e)
        if (e.position().toPoint() - self._drag_start).manhattanLength() < 10:
            return
        if self._downloading:
            return
        if not self.audio_path or not self.audio_path.exists():
            return

        self._lift()

        drag = QDrag(self)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(self.audio_path))])
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(e.position().toPoint())
        self.hide(); drag.exec(); self.show()
        self._drop()

    def _lift(self):
        if self._lifted:
            return
        self._lifted = True
        anim = QPropertyAnimation(self, b"pos", self, duration=120,
                                  startValue=self._orig_pos,
                                  endValue=self._orig_pos - QPoint(0, 15),
                                  easingCurve=QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _drop(self):
        if not self._lifted:
            return
        self._lifted = False
        anim = QPropertyAnimation(self, b"pos", self, duration=120,
                                  startValue=self.pos(), endValue=self._orig_pos,
                                  easingCurve=QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _spin(self):
        self._angle = (self._angle + 2.0) % 360
        self.update()

    def enterEvent(self, _): self._hover, self._timer = True, self._timer.start()
    def leaveEvent(self, _): self._hover, self._timer = False, self._timer.stop()

    def paintEvent(self, ev):
        super().paintEvent(ev)
        if not self._hover:
            return
        r = 10
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        grad = QConicalGradient(rect.center().toPointF(), -self._angle)
        grad.setColorAt(0, QColor("#ff0090"))
        grad.setColorAt(0.5, QColor("#0060ff"))
        grad.setColorAt(1, QColor("#ff0090"))
        p.setPen(QPen(QBrush(grad), 3)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, r, r)


def _load_thumb(url: str, lbl: QLabel) -> None:
    import requests
    try:
        data = requests.get(url, timeout=5).content
        src  = QPixmap(); src.loadFromData(data)
        src  = src.scaled(160, 90, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)

        rounded = QPixmap(src.size())
        rounded.fill(Qt.GlobalColor.transparent)

        # <─ the context-manager guarantees p.end()
        with QPainter(rounded) as p:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(QRectF(rounded.rect()), 10.0, 10.0)
            p.setClipPath(path)
            p.drawPixmap(0, 0, src)

        lbl.setPixmap(rounded)
    except Exception as exc:
        print("thumbnail error:", exc)