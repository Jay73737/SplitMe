import sys
import os
import requests
from bs4 import BeautifulSoup

from PyQt6.QtWidgets import (
    QApplication, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QComboBox, QMessageBox, QProgressBar, 
    QCheckBox, QWidget, QRadioButton,QButtonGroup,QHBoxLayout, QFrame
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal

import YoutubeDownloader, Downloader, StemSplitter
from Results import ResultsWindow




class MainGUI(QWidget):  

    def __init__(self):
        super().__init__()
        self.url_download = None
        horizontal_layout = QVBoxLayout()
        self.setWindowTitle("Stem Splitter")
        self.setGeometry(200, 400, 400, 350)
        self.main_layout = QVBoxLayout()
        side_by_side_layout = QHBoxLayout()
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_youtube)
        horizontal_layout.addWidget(self.search_button)


        self.platform_yt = QRadioButton("YouTube", self)
        self.platform_yt.setChecked(True)
        self.platform_soundcloud = QRadioButton("SoundCloud", self)
        self.platform_group = QButtonGroup(self)
        self.platform_group.addButton(self.platform_yt)
        self.platform_group.addButton(self.platform_soundcloud)
        horizontal_layout.addWidget(self.platform_yt)
        horizontal_layout.addWidget(self.platform_soundcloud)
    

        self.url_label = QLabel("URL/Search:")
        horizontal_layout.addWidget(self.url_label)

        self.url_input = QLineEdit(self)
        horizontal_layout.addWidget(self.url_input)
        self.link_layout = QVBoxLayout()
        horizontal_layout.addLayout(self.link_layout)
        self.main_layout.addLayout(self.link_layout)
        self.url_input.returnPressed.connect(self.search_youtube)
        
        self.format_label = QLabel("Select Format:")
        horizontal_layout.addWidget(self.format_label)

        self.format_dropdown = QComboBox(self)
        self.format_dropdown.addItems(["Video - mp4", "Audio - mp3", "Audio - wav", "Audio - m4a", "Audio - aac", "Audio - flac", "Audio - opus"])
        horizontal_layout.addWidget(self.format_dropdown)

        
        self.quality_label = QLabel("Select Audio Quality:")
        horizontal_layout.addWidget(self.quality_label)

        self.quality_dropdown = QComboBox(self)
        self.quality_dropdown.addItems(["Low (64kbps)", "Medium (128kbps)", "High (192kbps)"])
        horizontal_layout.addWidget(self.quality_dropdown)

        
        self.save_button = QPushButton("Select Save Location")
        self.save_button.clicked.connect(self.select_save_location)
        horizontal_layout.addWidget(self.save_button)
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.download_video)
        self.save_path = ""
        self.save_label = QLabel(f"Save Location: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Splitty')} ")
        horizontal_layout.addWidget(self.save_label)
        horizontal_layout.addWidget(self.download_button)
        
        side_by_side_layout.addLayout(horizontal_layout)
        vertical_divider = QFrame()
        vertical_divider.setFrameShape(QFrame.Shape.VLine)  # Vertical line
        vertical_divider.setFrameShadow(QFrame.Shadow.Sunken)
        side_by_side_layout.addWidget(vertical_divider)
        stem_layout = QVBoxLayout()
        self.split_stems_file = QLabel("Loaded File: ")
        stem_layout.addWidget(self.split_stems_file)
        self.split_button = QPushButton("Split Stems")
        self.split_button.clicked.connect(self.split_stems)
        self.stem_file_button = QPushButton("Select File")
        self.stem_file_button.clicked.connect(self.select_file_location)

        self.stem_options_dropdown = QComboBox(self)
        self.stem_options_dropdown.addItems(["Vocals Only", "4 Stem Split (Fast but lower quality)", "4 Stem Split (Higher Quality But Slower)", "4 Stem Split (MDX)", "6 Stem Split (Guitar + Piano)"])
        self.stem_options_dropdown.setEnabled(False)
        stem_layout.addWidget(self.stem_options_dropdown)
        stem_layout.addWidget(self.stem_file_button)
        stem_layout.addWidget(self.split_button)
        stem_layout.addStretch()
        side_by_side_layout.addLayout(stem_layout)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0,0)
        self.progress_bar.hide()
               
        stem_layout.addWidget(self.download_button)

        progress_layout = QVBoxLayout()
        progress_layout.addLayout(side_by_side_layout)
        
        progress_layout.addWidget(self.progress_bar)
        self.setLayout(progress_layout)

    def toggle_stem_options(self):
        if self.split_stems_checkbox.isChecked():
            self.stem_options_dropdown.setEnabled(True)
        else:
            self.stem_options_dropdown.setEnabled(False)
   
        

    def set_url(self, input_dict):

         
        self.results_window = ResultsWindow(input_dict, self)
        self.results_window.finished.connect(self.on_link_clicked)
        self.results_window.exec()

    def on_link_clicked(self, url):
        self.url_download = url
        self.url_input.setText(url)   

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
            self.split_stems_file.setText(f"Loaded File: {file_location}")
            self.stem_options_dropdown.setEnabled(True)
            return

        file, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Audio Files (*.mp3 *.wav *.m4a *.aac *.flac *.opus)")
        if file:
            self.filepath = file
            self.split_stems_file.setText(f"Loaded File: {file}")
            self.stem_options_dropdown.setEnabled(True)


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
        
              
        self.download_thread = Downloader.DownloadThread(url, format_selected, quality_selected, self.save_path.replace("/", "\\"))
        self.download_thread.finished_signal.connect(self.download_complete)   
        
        self.download_thread.start()

    

    # Returns model names from dropdown selection. (model, args)
    def convert_stems(self):
        stem = self.stem_options_dropdown.currentText()
        
        match stem:
            case "Vocals Only":
                return ("htdemucs",("--two-stems","vocals"))
            case "4 Stem Split (Fast but lower quality)":
                return ("htdemucs",None)
            case "4 Stem Split (Higher Quality But Slower)":
                return ("htdemucs_ft",None)
            case "4 Stem Split (MDX)":
                return ("mdx",None)
            case "6 Stem Split (Guitar + Piano)":
                return ("htdemucs_6s",None)

    def split_complete(self, message):
        print(message)
        self.splitter.quit()
        self.progress_bar.hide()
        os.startfile(message)

    def split_stems(self):
        if not self.filepath:
            QMessageBox.warning(self, "Error", "Please select or download a file to split.")
            return
        self.splitter = StemSplitter.StemSplitter(self.convert_stems(), self.filepath)
        self.splitter.finished.connect(self.split_complete)
        self.splitter.start()
        self.progress_bar.show()
       

    # Called when the download thread finishes
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
    sys.exit(app.exec())