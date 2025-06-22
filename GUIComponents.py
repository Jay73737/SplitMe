from PyQt6.QtCore import Qt, QUrl, QMimeData, pyqtSignal
from PyQt6.QtCore import Qt, QUrl, QMimeData, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import (QFrame, QLabel, QPushButton, QSlider, QHBoxLayout,
                            QVBoxLayout, QDialog, QMessageBox, QRadioButton, QButtonGroup, QWidget, QLineEdit)
import torch
from pathlib import Path
class APIKeyWindow(QDialog):
    finished = pyqtSignal(str)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter API Key")
        self.setFixedSize(300, 120)
        self.api_key = ""

        layout = QVBoxLayout()

        self.label = QLabel("Enter your API key:")
        layout.addWidget(self.label)

        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("your api key")
        layout.addWidget(self.api_input)

        self.submit_button = QPushButton("Save API Key")
        self.submit_button.clicked.connect(self.save_api_key)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

    def save_api_key(self):
        self.finished.emit(self.api_input.text())
        self.accept()
class DraggableStemLabel(QFrame):
    
    currently_playing = None

    def __init__(self, text, file_path: Path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.label = QLabel(text, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.label.font()
        font.setBold(True)
        font.setPointSize(12)
        self.label.setFont(font)
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.setStyleSheet("QFrame { border: 2px solid #888; border-radius: 6px; background: #888888; }")
        self.setCursor(Qt.CursorShape.OpenHandCursor)        

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(str(self.file_path)))
        self.play_button = QPushButton("▶", self)
        self.play_button.setFixedWidth(32)
        self.play_button.setToolTip("Play this stem")
        self.play_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_button.clicked.connect(self.toggle_play_pause)

        
        self.position_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.position_slider.setRange(0, 100)
        self.position_slider.setValue(0)
        self.position_slider.setToolTip("Seek")
        self.position_slider.setFixedWidth(220) 
        self.position_slider.sliderReleased.connect(self.seek_position)
        self.position_slider.sliderPressed.connect(self.pause_song)
        self.position_slider.setEnabled(False)

        
        self.time_label = QLabel(f"00:00 / {self.format_time(self.player.duration())}", self)
        self.time_label.setFixedWidth(90)

        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setToolTip("Volume")
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.volume_slider.hide()  

        
        self.volume_label = QLabel("Volume", self)
        self.volume_label.setFixedWidth(50)
        self.volume_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.label)
        top_layout.addStretch(1)
        top_layout.addWidget(self.play_button)

        
        track_layout = QHBoxLayout()
        track_layout.addWidget(self.time_label)
        track_layout.addWidget(self.position_slider)

        
        vol_layout = QHBoxLayout()
        vol_layout.addWidget(self.volume_label)
        vol_layout.addWidget(self.volume_slider)

        
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(top_layout)
        main_layout.addLayout(track_layout)
        main_layout.addLayout(vol_layout)
        main_layout.setSpacing(5)
        self.setLayout(main_layout)

        self.player.playbackStateChanged.connect(self.on_state_changed)
        self.progress_timer = None
        self.progress_color = '#b0b0b0'
        self.player.positionChanged.connect(self.update_position_slider)
        self.player.durationChanged.connect(self.update_duration)

    def set_audio_source(self, source):
        self.player.setSource(QUrl(source))

    def pause_song(self):
        """Pause the song while seeking."""
        self.player.pause()

    def set_text(self, text):
        self.label.setText(text)
        self.setToolTip(text)

    def set_volume(self, value):
        self.audio_output.setVolume(value / 100)

    def reset(self, file_path):
        self.file_path = file_path
        self.player.setSource(QUrl.fromLocalFile(str(self.file_path)))
        self.time_label.setText(f"00:00 / {self.format_time(self.player.duration())}")
        self.position_slider.setValue(0)
        self.position_slider.setEnabled(False)
        self.play_button.setText("▶")
        self.play_button.setToolTip("Play this stem")
        self.setToolTip(file_path)
        self.label.setText(file_path.split('/')[-1])

    def toggle_play_pause(self):
        
        if DraggableStemLabel.currently_playing and DraggableStemLabel.currently_playing is not self:
            DraggableStemLabel.currently_playing.player.stop()
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            DraggableStemLabel.currently_playing = None
        else:
            self.player.setSource(QUrl.fromLocalFile(str(self.file_path)))
            self.audio_output.setVolume(self.volume_slider.value() / 100)
            self.player.play()
            DraggableStemLabel.currently_playing = self

    def on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setText("⏸")
            self.play_button.setToolTip("Pause")
            self.volume_slider.show()
        else:
            self.play_button.setText("▶")
            self.play_button.setToolTip("Play this stem")
            self.volume_slider.hide()

    def update_position_slider(self, position):
        duration = self.player.duration()
        if duration > 0:
            percent = int((position / duration) * 100)
            self.position_slider.setValue(percent)
            self.time_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}")
            self.player.play()
        else:
            self.position_slider.setValue(0)
            self.time_label.setText("00:00 / 00:00")

    def update_duration(self, duration):
        self.position_slider.setEnabled(duration > 0)
        if duration == 0:
            self.position_slider.setValue(0)
            self.time_label.setText("00:00 / 00:00")
        else:
            self.time_label.setText(f"00:00 / {self.format_time(duration)}")
        

    def seek_position(self):
        slider_value = self.position_slider.value()
        duration = self.player.duration()  
        seek_position = int((slider_value / 100) * duration)
        self.player.setPosition(seek_position)
        

    def format_time(self, ms):
        seconds = int(ms // 1000)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02}:{seconds:02}"

    def enterEvent(self, event):
        self.setStyleSheet("QFrame { border: 2px solid #0078d7; background: #444444; }")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("QFrame { border: 2px solid #888; border-radius: 6px; background: #888888; }")
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(self.file_path))])
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction)
        super().mousePressEvent(event)

class CudaDeviceDialog(QDialog):
    device = pyqtSignal(int, str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select CUDA Devices")
        self.setGeometry(300, 300, 400, 200)
        self.layout = QVBoxLayout(self)

        self.checkboxes = []
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            self.btn_group = QButtonGroup(self)
            for i in range(device_count):
                device_name = torch.cuda.get_device_name(i)
                radio_button = QRadioButton(f"Device {i}: {device_name}", self)
                
                self.btn_group.addButton(radio_button, i)
                self.layout.addWidget(radio_button)
            self.btn_group.button(0).setChecked(True)
        
        else:
            QMessageBox.warning(self, "No CUDA Devices", "No CUDA devices are available on this system.")
            
        
        self.ok_button = QPushButton("OK", self)
        self.ok_button.clicked.connect(self.accept_prompt)
        self.layout.addWidget(self.ok_button)

    def accept_prompt(self):
        selected_device = self.btn_group.checkedId()
        if selected_device:
            QMessageBox.warning(self, "No Device Selected", "Please select at least one CUDA device.")
            return
        self.device.emit(self.btn_group.button(selected_device), torch.cuda.get_device_name(self.btn_group.button(selected_device)))
        self.accept()

    