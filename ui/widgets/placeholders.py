from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore    import QTimer, QPropertyAnimation
from ..constants     import CYCLE_MS

class PlaceholderAnimator:
    """Cycles placeholder label text with a fade-out / fade-in."""
    def __init__(self, label: QLabel, msgs: list[str]):
        self.lbl, self.msgs, self.idx = label, msgs, 0
        self.fx  = QGraphicsOpacityEffect(label); label.setGraphicsEffect(self.fx)
        self.o1  = QPropertyAnimation(self.fx, b"opacity", duration=400,
                                      startValue=1.0, endValue=0.0)
        self.o2  = QPropertyAnimation(self.fx, b"opacity", duration=400,
                                      startValue=0.0, endValue=1.0)
        self.seq = QTimer(singleShot=True, interval=CYCLE_MS, timeout=self._cycle)
        self.seq.start()

    def _cycle(self):
        self.o1.finished.connect(self._swap)
        self.o1.start()

    def _swap(self):
        self.o1.finished.disconnect(self._swap)
        self.idx = (self.idx + 1) % len(self.msgs)
        self.lbl.setText(self.msgs[self.idx])
        self.o2.finished.connect(lambda: self.seq.start())
        self.o2.start()

    # public
    def stop(self):  self.seq.stop()
    def start(self): self.seq.start(CYCLE_MS)