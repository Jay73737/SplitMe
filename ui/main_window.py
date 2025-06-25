from PyQt6.QtWidgets import QWidget, QLineEdit, QLabel, QStackedLayout
from PyQt6.QtCore    import Qt, QRect, QPropertyAnimation, QEasingCurve, QEvent
from PyQt6.QtGui     import QIcon
from .constants      import *
from .widgets        import AnimatedBorder, PlaceholderAnimator, SearchResults
from .youtube        import search as yt_search
from .config         import YOUTUBE_API_KEY
from .constants      import WIDTH, HEIGHT, PAD_Y

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WIDTH + BTN_SIZE*2 + 6, HEIGHT + PAD_Y)

        self.border = AnimatedBorder(self); self.border.setGeometry(0, PAD_Y, WIDTH, HEIGHT)
        self.border.installEventFilter(self)

        self.inner = QWidget(self)
        self.inner.setGeometry(BORDER, PAD_Y + BORDER,
                               WIDTH-2*BORDER, HEIGHT-2*BORDER)
        self.inner.setStyleSheet(f"background: rgba({FILL.red()},{FILL.green()},{FILL.blue()},"
                            f"{FILL.alpha()});border-radius:{R_INNER}px;")

        self.cont = QWidget(self.inner)
        self.cont.setGeometry(0, 0, self.inner.width(), self.inner.height())
        stack = QStackedLayout(self.cont)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        stack.setContentsMargins(30, 0, 30, 0)

        self.search = QLineEdit(alignment=Qt.AlignmentFlag.AlignCenter,
                                styleSheet="background:transparent;color:white;font:22px;border:0;")
        self.search.setPlaceholderText("Type and press Enter to search...")
        self.placeholder = QLabel("Drop in a file…",
                                  alignment=Qt.AlignmentFlag.AlignCenter,
                                  styleSheet="color:white;font:22px;")
        self.search.installEventFilter(self)
        stack.addWidget(self.search); stack.addWidget(self.placeholder)
        self.placeholder_anim = PlaceholderAnimator(
            self.placeholder,
            ["Drop in a file…", "Paste a URL…", "Type and search…"],
        )

        self.results = SearchResults(self); self.results.hide()
        self.results.move(0, PAD_Y + HEIGHT + 8)

        self.search.returnPressed.connect(self._search)

    def _search(self):
        txt = self.search.text().strip()
        print("DEBUG: _search invoked. Query:", repr(txt))
        print("DEBUG: YOUTUBE_API_KEY present?", bool(YOUTUBE_API_KEY))
        if not txt or not YOUTUBE_API_KEY:
            print("DEBUG: Aborting search—empty query or missing key.")
            return
        try:
            metas = yt_search(txt, limit=8)
        except Exception as exc:
            print("YouTube error:", exc)
            return

        self.results.set_results(metas)

        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        self.results.adjustSize()

        self.results.show()
        self.results.content.adjustSize()

        panel_h = max(self.results.sizeHint().height() + 12,
                      self.results.content.sizeHint().height() + 24)
        panel_w = WIDTH

        self.results.setFixedWidth(panel_w)
        self.results.setFixedHeight(panel_h)
        self.results.setMinimumHeight(panel_h)
        self.results.setMaximumHeight(panel_h)
        self.results.content.setFixedWidth(panel_w - 24)

        self.results.move(0, PAD_Y + HEIGHT + 8)
        self.results.raise_()
        self.results.update()
        print(f"DEBUG: Displaying {len(metas)} results, panel_h={panel_h}")

        self.setFixedSize(WIDTH + BTN_SIZE*2 + 6, PAD_Y + HEIGHT + panel_h + 12)

        self._animate_height(panel_h)

    def _animate_height(self, panel_h: int):
        start = self.geometry()
        end = QRect(start.x(), start.y(),
                    start.width(), PAD_Y + HEIGHT + panel_h + 12)

        anim = QPropertyAnimation(self, b"geometry", self)
        anim.setDuration(800)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.OutBack)
        anim.start()
        self._anim = anim

    
    def eventFilter(self, obj, ev):
        if obj is self.search and ev.type() == QEvent.Type.FocusIn:
            self.placeholder.hide(); self.placeholder_anim.stop()
        elif obj is self.search and ev.type() == QEvent.Type.FocusOut:
            if not self.search.text():
                self.placeholder.show(); self.placeholder_anim.start()
        return super().eventFilter(obj, ev)