import sys, requests, json
import os
import re

config_path = os.path.join(os.path.dirname(__file__), "config.json")
YOUTUBE_API_KEY = ""
try:
    with open(config_path, "r", encoding="utf-8") as cfg_file:
        cfg = json.load(cfg_file)
        YOUTUBE_API_KEY = (
            cfg.get("api_key") or
            cfg.get("YOUTUBE_API_KEY") or
            cfg.get("youtube_api_key") or
            ""
        )
except (FileNotFoundError, json.JSONDecodeError):
    pass
from PyQt6.QtCore import (
    Qt, QTimer, QPoint, QEvent, QRectF, QRect,
    QPropertyAnimation, QEasingCurve, QSize, QUrl
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QConicalGradient, QPixmap,
    QPainterPath, QRadialGradient, QIcon, QDesktopServices
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFrame, QScrollArea,
    QStackedLayout, QGraphicsOpacityEffect, QSizePolicy,
    QToolButton, QPushButton, QGridLayout
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
BTN_SIZE      = 32
BTN_MARGIN    = 12
BTN_HIDE_OFF  = 40
BTN_Y_OFFSET  = 50
PAD_Y = BTN_Y_OFFSET



class AnimatedBorder(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.angle = 0.0
        self.timer = QTimer(self, timeout=self._spin, interval=35)
        self.timer.start()

    def _spin(self):
        self.angle = (self.angle + 1.2) % 360
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(BORDER // 2, BORDER // 2,
                                    -BORDER // 2, -BORDER // 2)
        cx, cy = float(rect.center().x()), float(rect.center().y())
        halo_path = QPainterPath()
        halo_rect = rect.adjusted(-25, -25, 25, 25)
        halo_path.addRoundedRect(QRectF(halo_rect), R_OUTER + 25, R_OUTER + 25)
        halo_grad = QRadialGradient(cx, cy, halo_rect.width() / 2)
        halo_grad.setColorAt(0.0, QColor(255, 0, 255, 80))
        halo_grad.setColorAt(1.0, QColor(255, 0, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo_grad)
        p.drawPath(halo_path)
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

class ResultCard(QFrame):
    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background:rgba(0,0,0,180);border-radius:10px;")
        v = QVBoxLayout(self); v.setContentsMargins(8, 8, 8, 8)
        thumb = QLabel()
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
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
        dur_label = QLabel(info.get("duration", ""))
        dur_label.setStyleSheet("color:white;font-size:8px;")
        v.addWidget(thumb)
        v.addWidget(title)
        v.addWidget(dur_label)
        btn = QPushButton("SOURCE")
        btn.setStyleSheet("background:#FF0000;color:white;border-radius:4px;padding:4px;")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _, url=info.get("url"): QDesktopServices.openUrl(QUrl(url)))
        row = QHBoxLayout()
        row.addWidget(btn)
        v.addLayout(row)

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
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.grid = QGridLayout(self.content)
        for col in range(4):
            self.grid.setColumnStretch(col, 1)
        self.grid.setContentsMargins(12, 12, 12, 12)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self.content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
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
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for idx, info in enumerate(items[:8]):
            row = idx // 4
            col = idx % 4
            self.grid.addWidget(ResultCard(info), row, col)
        for col in range(4):
            self.grid.setColumnStretch(col, 1)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFixedSize(WIDTH + BTN_SIZE*2 + 6, HEIGHT + PAD_Y)
        self.drag_offset = QPoint()
        self._dragging = False
        self.border = AnimatedBorder(self)
        
        self.border.installEventFilter(self)
        self.border.setGeometry(0, PAD_Y, WIDTH, HEIGHT)
        inner = QWidget(self)
        inner.setGeometry(BORDER, PAD_Y + BORDER, WIDTH - 2*BORDER, HEIGHT - 2*BORDER)
        inner.setStyleSheet(f"background: rgba({FILL.red()},{FILL.green()},{FILL.blue()},{FILL.alpha()});"
                            f"border-radius:{R_INNER}px;")
        cont = QWidget(inner); cont.setGeometry(0, 0, inner.width(), inner.height())
        st   = QStackedLayout(cont); st.setStackingMode(QStackedLayout.StackingMode.StackAll)
        st.setContentsMargins(30, 0, 30, 0)
        self.search = QLineEdit()
        self.search.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.search.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.search.setStyleSheet("background:transparent;color:white;font:22px;border:0;")
        self.search.installEventFilter(self)
        self.ph = QLabel("Drop in a file...")
        self.ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ph.setStyleSheet("color:white;font:22px;")
        st.addWidget(self.search); st.addWidget(self.ph)
        self.anim = PlaceholderAnimator(self.ph,
                                        ["Drop in a file...", "Paste a URL...", "Type and search..."])
        self.results = SearchResults(self); self.results.hide()
        self.results.move(0, PAD_Y + HEIGHT + 8)
        self.search.returnPressed.connect(self.do_search)
        self.btn_min = QToolButton(self, autoRaise=True)
        self.btn_min.setFixedSize(BTN_SIZE, BTN_SIZE)
        self.btn_min.setIcon(QIcon("MINIMIZE.svg"))
        self.btn_min.setStyleSheet(f"background:rgba(0,0,0,180);border-radius:{BTN_SIZE//2}px;color:white;")
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_min.setIconSize(QSize(BTN_SIZE-8, BTN_SIZE-8))
        self.btn_min.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
       

        self.btn_close = QToolButton(self, autoRaise=True)
        self.btn_close.setFixedSize(BTN_SIZE, BTN_SIZE)
        self.btn_close.setIcon(QIcon("CLOSE.svg"))
        self.btn_close.setStyleSheet(f"background:rgba(0,0,0,180);border-radius:{BTN_SIZE//2}px;color:white;")
        self.btn_close.clicked.connect(self.close)
        self.btn_close.setIconSize(QSize(BTN_SIZE-8, BTN_SIZE-8))
        self.btn_close.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        

        self._placeButtons(initial=False)
        self._buttonsVisible = False
        self.btn_min.hide()
        self.btn_close.hide()
        self.search.setFocus()

    def _placeButtons(self, *, initial=False):
        mid_y = PAD_Y + (HEIGHT - BTN_SIZE) // 2 - BTN_Y_OFFSET
        x0 = WIDTH - BTN_SIZE // 2
        positions = {
            self.btn_close: QPoint(x0, mid_y),
            self.btn_min: QPoint(x0 - BTN_SIZE - 6, mid_y)
        }
        for btn, pos in positions.items():
            target = QPoint(pos.x(), self.height() + BTN_HIDE_OFF) if initial else pos
            btn.move(target)
            btn.raise_()

    def _animateButtons(self, show: bool):
        for btn in (self.btn_close, self.btn_min):
            btn.raise_()
            start = btn.pos()
            end_y = PAD_Y + (HEIGHT - BTN_SIZE) // 2 - BTN_Y_OFFSET if show else PAD_Y + HEIGHT + BTN_HIDE_OFF
            anim = QPropertyAnimation(btn, b"pos", self)
            anim.setDuration(200)
            anim.setStartValue(start)
            anim.setEndValue(QPoint(btn.x(), end_y))
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
            btn._anim = anim

    def _hoveringButtons(self, local_pos) -> bool:
        pill_rect = QRect(0, PAD_Y, WIDTH, HEIGHT)
        return pill_rect.contains(local_pos)

    def eventFilter(self, obj, ev):
        if obj is self.search:
            if ev.type() == QEvent.Type.FocusIn:
                self.ph.hide(); self.anim.stop()
            elif ev.type() == QEvent.Type.FocusOut and not self.search.text():
                self.ph.show(); self.anim.start()
        elif obj is self.border:
            if ev.type() == QEvent.Type.Enter:
                self.btn_min.show()
                self.btn_close.show()
                self._animateButtons(True)
                self._buttonsVisible = True
           
        return super().eventFilter(obj, ev)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self.drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.search.setFocus()
            e.accept()
            pos = e.position().toPoint()
            if self._buttonsVisible and not self._hoveringButtons(pos):
                self._animateButtons(False)
                self._buttonsVisible = False
                QTimer.singleShot(200, lambda: (self.btn_min.hide(), self.btn_close.hide()))

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        inside = self._hoveringButtons(pos)
        if inside != self._buttonsVisible:
            self._animateButtons(inside)
            self._buttonsVisible = inside
        if self._dragging and (e.buttons() & Qt.MouseButton.LeftButton):
            self.move(e.globalPosition().toPoint() - self.drag_offset)
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._dragging = False
        super().mouseReleaseEvent(e)

    def _parse_duration(self, iso: str) -> str:
        h = m = s = 0
        parts = re.findall(r'(\d+)([HMS])', iso)
        for value, unit in parts:
            if unit == 'H': h = int(value)
            elif unit == 'M': m = int(value)
            elif unit == 'S': s = int(value)
        if h:
            return f"{h}:{m:02}:{s:02}"
        return f"{m}:{s:02}"

    def do_search(self):
        query = self.search.text().strip()
        print("do_search called; query:", query)
        print("API key loaded? ", bool(YOUTUBE_API_KEY))
        if not query or not YOUTUBE_API_KEY:
            print("Search aborted – missing query or API key.")
            return
        try:
            params = {
                "part": "snippet",
                "q": query,
                "maxResults": 8,
                "type": "video",
                "key": YOUTUBE_API_KEY
            }
            resp = requests.get("https://www.googleapis.com/youtube/v3/search", params=params)
            print("YouTube search status:", resp.status_code)
            if resp.status_code != 200:
                print("Search error payload:", resp.text)
            data = resp.json().get("items", [])
            print("Items returned:", len(data))
            video_ids = [item["id"]["videoId"] for item in data if item.get("id", {}).get("videoId")]
            details = {}
            if video_ids:
                params = {
                    "part": "contentDetails",
                    "id": ",".join(video_ids),
                    "key": YOUTUBE_API_KEY
                }
                resp2 = requests.get("https://www.googleapis.com/youtube/v3/videos", params=params)
                for item in resp2.json().get("items", []):
                    vid = item["id"]
                    details[vid] = self._parse_duration(item["contentDetails"]["duration"])
            results = []
            for item in data:
                vid = item["id"].get("videoId")
                if not vid: continue
                snippet = item["snippet"]
                thumb = snippet["thumbnails"]["medium"]["url"]
                title = snippet["title"]
                duration = details.get(vid, "")
                url = f"https://www.youtube.com/watch?v={vid}"
                results.append({
                    "thumbnail": thumb,
                    "title": title,
                    "duration": duration,
                    "url": url
                })
            if not results:
                print("No results to display.")
            self.results.set_results(results)

            self.results.content.adjustSize()
            panel_h = self.results.content.sizeHint().height() + 24  
            panel_w = WIDTH
            self.results.setFixedWidth(panel_w)
            self.results.setFixedHeight(panel_h)
            self.results.content.setFixedWidth(panel_w - 24)
            self.results.move(0, PAD_Y + HEIGHT + 8)
            self.results.show()

            self.setFixedSize(WIDTH + BTN_SIZE * 2 + 6, PAD_Y + HEIGHT + panel_h + 12)
        except Exception as e:
            print("YouTube search error:", e)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow(); win.show()
    sys.exit(app.exec())