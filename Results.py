from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal
import requests
import traceback
class ClickableLabel(QLabel):
    clicked = pyqtSignal(str) 

    def __init__(self, text, url, pixmap=None, parent=None):
        super().__init__(text, parent)
        if pixmap:
            super().setPixmap(pixmap.scaled(120, 90, Qt.AspectRatioMode.KeepAspectRatio))
        self.url = url

    def mousePressEvent(self, event):
        self.clicked.emit(self.url)
        super().mousePressEvent(event)

class ResultsWindow(QDialog):
    finished = pyqtSignal(str)

    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.setWindowTitle("YouTube Search Results")
        layout = QVBoxLayout(self)
 
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget()
        vbox = QVBoxLayout(content)

        for result in results:
            hbox = QHBoxLayout()
            
            thumb_url = result.get('thumbnail')
            if thumb_url:
                try:
                    response = requests.get(thumb_url)
                    pixmap = QPixmap()
                    pixmap.loadFromData(response.content)
                    thumb_label = ClickableLabel(result['title'], result['url'], pixmap)
                    thumb_label.clicked.connect(self.send_url)
                    hbox.addWidget(thumb_label)
                except Exception:
                    traceback.print_exc()
                    hbox.addWidget(QLabel("No Image"))
            else:
                hbox.addWidget(QLabel("No Image"))

            title = result['title']
            url = result['url']
            desc = result.get('description', '')

            title_label = ClickableLabel(f"<b>{title}</b>", url)
            title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            title_label.setOpenExternalLinks(False)
            title_label.clicked.connect(self.send_url)
            hbox.addWidget(title_label)

            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            hbox.addWidget(desc_label)
            vbox.addLayout(hbox)

        content.setLayout(vbox)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def send_url(self, url):
        self.finished.emit(url)
        self.accept()

