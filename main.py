import sys
import os
import requests
from bs4 import BeautifulSoup

from PyQt6.QtWidgets import (
    QApplication, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QComboBox, QMessageBox, QProgressBar, 
    QCheckBox, QWidget, QRadioButton,QButtonGroup,QHBoxLayout, QFrame, QSpinBox, QSizePolicy
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal

import YoutubeDownloader, Downloader, StemSplitter
from Results import ResultsWindow




class MainGUI(QWidget):  

    def __init__(self):
        super().__init__()
        self.url_download = None

        self.instrument_dict = {
            "Vocals": ["htdemucs", "htdemucs_ft", "mdx", "htdemucs_6s"], 
            "Bass": ["htdemucs", "htdemucs_ft", "mdx", "htdemucs_6s"], 
            "Drums": ["htdemucs", "htdemucs_ft", "mdx", "htdemucs_6s"],
            "Guitar": ["htdemucs_6s"],
            "Piano": ["htdemucs_6s"],
            "Other": ["htdemucs", "htdemucs_ft", "mdx", "htdemucs_6s"]
        }
        
        self.setWindowTitle("Stem Splitter")
        self.setGeometry(200, 400, 600, 350)
        self.main_layout = QVBoxLayout()
        self.side_by_side_layout = QHBoxLayout()
        self.horizontal_layout = QVBoxLayout()

        # --- Left Side (horizontal_layout) ---
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_youtube)
        self.horizontal_layout.addWidget(self.search_button)

        self.platform_yt = QRadioButton("YouTube", self)
        self.platform_yt.setChecked(True)
        self.platform_soundcloud = QRadioButton("SoundCloud", self)
        self.platform_group = QButtonGroup(self)
        self.platform_group.addButton(self.platform_yt)
        self.platform_group.addButton(self.platform_soundcloud)
        self.horizontal_layout.addWidget(self.platform_yt)
        self.horizontal_layout.addWidget(self.platform_soundcloud)    

        self.url_label = QLabel("URL/Search:")
        self.horizontal_layout.addWidget(self.url_label)

        self.url_input = QLineEdit(self)
        self.horizontal_layout.addWidget(self.url_input)
        self.link_layout = QVBoxLayout()
        self.horizontal_layout.addLayout(self.link_layout, stretch=1)

        self.url_input.returnPressed.connect(self.search_youtube)
        
        self.format_label = QLabel("Select Format:")
        self.horizontal_layout.addWidget(self.format_label)

        self.format_dropdown = QComboBox(self)
        self.format_dropdown.addItems([
            "Video - mp4", "Audio - mp3", "Audio - wav", "Audio - m4a",
            "Audio - aac", "Audio - flac", "Audio - opus"
        ])
        self.horizontal_layout.addWidget(self.format_dropdown)

        self.quality_label = QLabel("Select Audio Quality:")
        self.horizontal_layout.addWidget(self.quality_label)
        self.quality_dropdown = QComboBox(self)
        self.quality_dropdown.addItems(["Low (64kbps)", "Medium (128kbps)", "High (192kbps)"])
        self.horizontal_layout.addWidget(self.quality_dropdown)

        self.save_button = QPushButton("Select Save Location")
        self.save_button.clicked.connect(self.select_save_location)
        self.horizontal_layout.addWidget(self.save_button)

        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.download_video)
        self.save_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'SplitMe')
        self.save_label = QLabel(
            f"Save Location: {os.path.join(os.path.dirname(os.path.realpath(__file__)), 'SplitMe')} "
        )
        self.horizontal_layout.addWidget(self.save_label)
        self.horizontal_layout.addWidget(self.download_button)

        # --- Divider ---
        self.vertical_divider = QFrame()
        self.vertical_divider.setFrameShape(QFrame.Shape.VLine) 
        self.vertical_divider.setFrameShadow(QFrame.Shadow.Sunken)

        # --- Right Side (stem_layout) ---
        self.stem_layout = QVBoxLayout()
        self.split_stems_file = QLabel("Loaded File: ")
        self.stem_layout.addWidget(self.split_stems_file)

        self.split_button = QPushButton("Split Stems")
        self.split_button.clicked.connect(self.split_stems)
        self.stem_file_button = QPushButton("Select File")
        self.stem_file_button.clicked.connect(self.select_file_location)

        self.checkbox_layout = QVBoxLayout()
        checkbox_labels = self.instrument_dict.keys()
        self.split_stems_checkbox_group = []
        for label in checkbox_labels:
            checkbox = QCheckBox(label)
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(self.on_checkbox_state_changed)
            self.split_stems_checkbox_group.append(checkbox)
            self.checkbox_layout.addWidget(checkbox)
        self.stem_layout.addLayout(self.checkbox_layout)

        self.shift_spinbox = QSpinBox(self)
        self.shift_spinbox.setRange(1, 20)
        self.shift_spinbox.setValue(1)
        self.shift_label = QLabel("Shifts:")

        spinbox_layout = QHBoxLayout()
        spinbox_layout.addWidget(self.shift_label)
        spinbox_layout.addWidget(self.shift_spinbox)
        self.stem_layout.addLayout(spinbox_layout)

        self.stem_layout.addWidget(self.stem_file_button)
        self.stem_layout.addWidget(self.split_button)

        self.model_checkboxes_layout = QHBoxLayout()
        self.model_checkboxes_group = []
        self.stem_layout.addLayout(self.model_checkboxes_layout)
        self.left_widget = QWidget()
        self.left_widget.setLayout(self.horizontal_layout)

        
        self.right_widget = QWidget()
        self.right_widget.setLayout(self.stem_layout)
       
        self.side_by_side_layout.addWidget(self.left_widget, 1)
        self.side_by_side_layout.addWidget(self.vertical_divider)
        self.side_by_side_layout.addWidget(self.right_widget, 1)

        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()

        
        self.progress_layout = QVBoxLayout()
        self.progress_layout.addLayout(self.side_by_side_layout)
        self.progress_layout.addWidget(self.progress_bar)
        self.main_layout.addLayout(self.progress_layout, 1)
        self.setLayout(self.main_layout)

    def on_checkbox_state_changed(self):
        selected_instruments = [checkbox.text() for checkbox in self.split_stems_checkbox_group if checkbox.isChecked()]
        models = []
        self.model_checkboxes_group = []
        while self.model_checkboxes_layout.count():
            item = self.model_checkboxes_layout.itemAt(0)
            if item is not None:
                widget = item.widget()
                self.model_checkboxes_layout.removeWidget(widget)
                widget.deleteLater()
        if selected_instruments:
            for inst in selected_instruments:
                models.extend(self.instrument_dict[inst])
            models = list(set(models))
            if len(models) >= 1:
                self.model_checkboxes_layout = QHBoxLayout()
                for model in models:
                    model_checkbox = QCheckBox(model)
                    model_checkbox.setChecked(False)
                    self.model_checkboxes_group.append(model_checkbox)
                    self.model_checkboxes_layout.addWidget(model_checkbox)
                self.stem_layout.addLayout(self.model_checkboxes_layout)


    
    def on_checkbox_state_changed(self):
        selected_instruments = [checkbox.text() for checkbox in self.split_stems_checkbox_group if checkbox.isChecked()]
        models = []
        self.model_checkboxes_group = []
        while self.model_checkboxes_layout.count():
            item = self.model_checkboxes_layout.itemAt(0)
            if item is not None:
                widget = item.widget()
                self.model_checkboxes_layout.removeWidget(widget)
                widget.deleteLater()
        if selected_instruments:
            for inst in selected_instruments:
                models.extend(self.instrument_dict[inst])
            models = list(set(models))
            if len(models) >= 1:
                self.model_checkboxes_layout = QHBoxLayout()
                for model in models:
                    model_checkbox = QCheckBox(model)
                    model_checkbox.setChecked(False)
                    self.model_checkboxes_group.append(model_checkbox)
                    self.model_checkboxes_layout.addWidget(model_checkbox)
                self.stem_layout.addLayout(self.model_checkboxes_layout)
        

    def set_url(self, input_dict):
    
        self.results_window = ResultsWindow(input_dict, self)
        self.results_window.finished.connect(self.on_link_clicked)
        self.results_window.exec()

    def on_link_clicked(self, url):
        self.url_download = url
        self.url_input.setText(url)
        if 'playlist' in url:
            
            reply = QMessageBox.question(self, "Playlist Detected", "You have selected a playlist. Do you want to download all videos?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.url_input.setText(url)
                self.url_download = url
            else:
                self.search_youtube()
        elif 'video' in url:
            self.url_input.setText(url)
            self.url_download = url

          

    def show_error(self, error):
        error_message = f"Error: {error}"
        QMessageBox.critical(self, "Error", error_message)
        self.progress_bar.hide()
        self.url_input.setText("")
        
      


    def search_youtube(self):
        if self.platform_yt.isChecked():
            self.ys = YoutubeDownloader.YoutubeDownloader(self.url_input.text())
            self.ys.finished.connect(self.set_url)
            self.ys.error.connect(self.show_error)
            self.ys.start()
        
        
        
        
    def toggle_loading(self):
        if self.progress_bar.isVisible():
            self.progress_bar.hide()
        else:
            self.progress_bar.show()
            
    
    def select_file_location(self, file_location = None):
        if file_location:
            self.filepath = file_location
            if ' ' in self.filepath:
                self.filepath = rf'{self.filepath}'
            self.split_stems_file.setText(f"Loaded File: {self.filepath}")
            return

        file, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Audio Files (*.mp3 *.wav *.m4a *.aac *.flac *.opus)")
        if file:
            self.filepath = file
            self.split_stems_file.setText(f"Loaded File: {file}")
       


    def select_save_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if folder:
            self.save_path = folder
            self.save_label.setText(f"Save Location: {folder}")

  
    def download_video(self):
        self.progress_bar.show()
        url = self.url_download
        format_selected = self.format_dropdown.currentText().split(" - ")[1].lower()
        self.format = format_selected
        quality_selected = self.quality_dropdown.currentText()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a valid URL.")
            return
        
              
        self.download_thread = Downloader.DownloadThread(url, format_selected, quality_selected, self.save_path)
        self.download_thread.finished_signal.connect(self.download_complete)   
        
        self.download_thread.start()

    

    
    def get_models(self):

        selected_models = [checkbox.text() for checkbox in self.model_checkboxes_group if checkbox.isChecked()]
        if not selected_models:
            QMessageBox.warning(self, "Error", "Please select at least one model.")
            return
        stem_types = [checkbox.text() for checkbox in self.split_stems_checkbox_group if checkbox.isChecked()]
        if not stem_types:
            QMessageBox.warning(self, "Error", "Please select at least one stem type.")
            return
        return (selected_models, stem_types)
        
        
            

    def split_complete(self, message):
        print(message)
        self.splitter.quit()
        self.progress_bar.hide()
        os.startfile(message)

    def split_stems(self):
        if not self.filepath:
            QMessageBox.warning(self, "Error", "Please select or download a file to split.")
            return
        info = self.get_models()
        self.splitter = StemSplitter.StemSplitter(info[0],info[1], self.filepath, shifts=self.shift_spinbox.value(), keep_all=False)
        self.splitter.finished.connect(self.split_complete)
        self.splitter.start()
        self.progress_bar.show()
       

    
    def download_complete(self, success, message, file_path):
        if success:
            self.select_file_location(file_path)
            self.save_label.setText(f"Save Location: {file_path}")
            print(file_path)
            self.progress_bar.hide()
        else:
            self.progress_bar.hide()
        
    
        


    
# https://www.youtube.com/watch?v=1VQ_3sBZEm0
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('icon.ico'))
    window = MainGUI()
    window.show()
    window.activateWindow()
    window.raise_()
    sys.exit(app.exec())