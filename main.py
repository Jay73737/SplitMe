import sys
import os
import psutil




from PyQt6.QtWidgets import (
    QApplication, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QComboBox, QMessageBox, QProgressBar, 
    QCheckBox, QWidget, QPushButton,QStyle,QHBoxLayout, QFrame,
      QSpinBox, QSizePolicy, QGroupBox, QSplitter,  QSplitter, QSplitterHandle
)
from PyQt6.QtGui import QIcon, QDesktopServices, QPainter, QColor
from PyQt6.QtCore import Qt, QUrl, QSize
from YoutubeDownloader import YoutubeDownloader
from Downloader import DownloadThread
from StemSplitter import StemSplitter
from Results import ResultsWindow
import subprocess
from GUIComponents import DraggableStemLabel, CudaDeviceDialog
from contextvars import ContextVar
from pathlib import Path
import json

_ffmpeg_location = ContextVar('ffmpeg_location', default=None)


_ffmpeg_location.set('ffmpeg')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

import torch

class VerticalTextButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumSize(40, 100)  # Taller than wide by default

    def sizeHint(self):
        # Swap width/height hint to better fit vertical text
        size = super().sizeHint()
        return QSize(size.height() + 20, size.width() + 20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Rotate around center
        painter.translate(self.width(), 0)
        painter.rotate(90)

        # Draw the text vertically
        painter.drawText(0, 0, self.height() + 25, self.width() + 20,
                         Qt.AlignmentFlag.AlignBottom, self.text())

class ToggleHandle(QSplitterHandle):
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)

        self.toggle_btn = VerticalTextButton("v Downloader", self)
        self.toggle_btn.setFixedSize(60, 60)  # adjust size as needed

        # Place the button centered vertically in the handle
        self.toggle_btn.move(0, (self.height() - self.toggle_btn.height()) // 2)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)

        self._collapsed = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep button vertically centered
        self.toggle_btn.move(0, (self.height() - self.toggle_btn.height()) // 2)

    def toggle_sidebar(self):
        splitter = self.parent()  # the QSplitter
        sizes = splitter.sizes()
        if not self._collapsed:
            # Collapse left widget
            splitter.setSizes([0, 600])
            self.toggle_btn.setText("Downloader ^")
            self._collapsed = True
        else:
            # Restore left widget width, give right widget remaining space
            splitter.setSizes([200, max(1, sum(sizes) - 200)])
            self.toggle_btn.setText("v Downloader")
            self.toggle_btn.setStyleSheet("""
    QPushButton {
        text-align: bottom;
        font-size: 12px;
    }
""")
            self._collapsed = False
    
    def sizeHint(self):
        size = super().sizeHint()
        # Make the splitter handle wider (e.g., 30px)
        if self.orientation() == Qt.Orientation.Horizontal:
            size.setWidth(30)
        else:
            size.setHeight(30)
        return size


class ToggleSplitter(QSplitter):
    def __init__(self, orientation):
        super().__init__(orientation)

    def createHandle(self):
        return ToggleHandle(self.orientation(), self)


class MainGUI(QWidget):

    def __init__(self):
        super().__init__()
        self.url_download = None
        self.sources = ['vocals', 'bass', 'drums', 'other', 'guitar', 'piano']
        
        self.instrument_dict = {
            "Vocals": ["htdemucs", "htdemucs_ft", "mdx", "htdemucs_6s"], 
            "Bass": ["htdemucs", "htdemucs_ft", "mdx", "htdemucs_6s"], 
            "Drums": ["htdemucs", "htdemucs_ft", "mdx", "htdemucs_6s"],
            "Guitar": ["htdemucs_6s"],
            "Piano": ["htdemucs_6s"],
            "Other": ["htdemucs", "htdemucs_ft", "mdx", "htdemucs_6s"]
        }
        last_file_downloader = None
        last_file_splitter = None
        self.config_params= {}
        try:
            with open(Path(__file__).parent / 'config.json', 'r') as config:
                print(config.read())
                config.seek(0)
                data = json.load(config)
                params = data["user"]
                if "last_file_path_downloader" in params['cache'].keys():
                    last_file_downloader = str(params['cache'].get('last_file_path_downloader'))
                else:
                    last_file_downloader = str(Path(__file__).absolute())
                if "last_file_path_splitter" in params['cache'].keys():
                    last_file_splitter = str(params['cache'].get("last_file_path_splitter"))
                else:
                    last_file_splitter = str(Path(__file__).absolute())
                if "sources" in params['cache'].keys():
                    last_source = str(params['cache'].get("sources"))
                else:
                    last_source = []
                self.config_params = {"user":{"cache":{
                                                "last_file_path_downloader": last_file_downloader,
                                                "last_file_path_splitter": last_file_splitter,
                                                "sources": last_source
            },
                                        "api_key": params['api_key']}}
        except:
            print('do some shit')
        os.remove(Path(__file__).parent / 'config.json')
            
        with open(Path(__file__).parent / 'config.json', 'a+') as con: 

            json.dump(self.config_params, con)
          
            
            

        

        
        
        



        self.file_formats = [
        "Audio - mp3", "Audio - wav"
        ]
        sys.path.insert(0, Path(__file__).absolute() / "demucs")

        self.filepath = ""
        self.split_ind = 1
        with open(Path(__file__).parent / 'config.json', 'r+') as f:
            self.config_params = json.load(f)
        self.setup_ui()
        
        
    @staticmethod
    def write_config(class_var,param,value):
        
            
        temp = None
        with open(Path(__file__).parent / 'config.json', 'r') as f:            
            temp = json.load(f)
            if param == 'sources':
                if len(temp['user']['cache']['sources']) > 50:
                    temp['user']['cache']['sources'].pop(0)
                    temp['user']['cache']['sources'].append(value)
                    class_var.config_params['user']['cache']['sources'] = temp['user']['cache']['sources']
                else:
                    temp['user']['cache']['sources'].append(value)
                    class_var.config_params['user']['cache']['sources'] = temp['user']['cache']['sources']
            
            else:
                temp['user']['cache'][param] = value
        os.remove(Path(__file__).parent / 'config.json')
        with open(Path(__file__).parent / 'config.json', 'a+') as f:
            json.dump(temp, f)
            class_var.config_params = temp


    def setup_ui(self):

        self.setWindowTitle("Stem Splitter")
        self.setGeometry(200, 400, 600, 350)
        self.main_layout = QVBoxLayout()
        self.side_by_side_layout = QHBoxLayout()
        self.horizontal_layout = QVBoxLayout()

        
        
        
        self.platform_yt = QCheckBox("Use YouTube API?", self)
        self.platform_yt.setChecked(True)        
        self.platform_yt.setToolTip("Use YouTube API to search for videos. \nIf unchecked, you can paste a direct URL.") 
        
        self.url_label = QLabel("URL/Search:")
        self.url_input = QLineEdit(self)
        self.url_input.returnPressed.connect(self.search_youtube)

        self.link_layout = QVBoxLayout()
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_youtube)
        self.link_layout.addWidget(self.search_button)

        self.format_label = QLabel("Select Format:")
        self.quality_dropdown = QComboBox(self)
        self.quality_dropdown.addItems(["Low (64kbps)", "Medium (128kbps)", "High (192kbps)"])
        self.quality_dropdown.setDisabled(True)
        self.format_dropdown = QComboBox(self)
        self.format_dropdown.addItems(self.file_formats)
        self.format_dropdown.currentTextChanged.connect(lambda: self.quality_dropdown.setDisabled('Audio - mp3' not in self.format_dropdown.currentText()))
        self.quality_label = QLabel("Select Audio Quality:")

        self.save_button = QPushButton("Select Save Location")
        self.save_button.clicked.connect(self.select_save_location)
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.download_video)
        self.save_path = os.path.abspath('SplitMe')
        self.save_label = QLabel(
            f"Save Location: {self.config_params['user']['cache']['last_file_path_downloader']}"
        )

        self.downloaded_song_box = DraggableStemLabel("None", None)
        self.downloaded_song_box.setVisible(False)
        
        self.horizontal_layout.addWidget(self.platform_yt)   
        self.horizontal_layout.addWidget(self.url_label)
        self.horizontal_layout.addWidget(self.url_input)
        self.horizontal_layout.addLayout(self.link_layout, stretch=1)              
        self.horizontal_layout.addWidget(self.format_label)        
        self.horizontal_layout.addWidget(self.format_dropdown)
        self.horizontal_layout.addWidget(self.quality_label)
        self.horizontal_layout.addWidget(self.quality_dropdown)        
        self.horizontal_layout.addWidget(self.save_button)        
        self.horizontal_layout.addWidget(self.save_label)
        self.horizontal_layout.addWidget(self.download_button)
        self.horizontal_layout.addWidget(self.downloaded_song_box)
        
        
        self.vertical_divider = QFrame()
        self.vertical_divider.setFrameShape(QFrame.Shape.VLine) 
        self.vertical_divider.setFrameShadow(QFrame.Shadow.Sunken)
        
        self.stem_layout = QVBoxLayout()
        self.split_stems_file = QLabel("Loaded File: ")

        self.stems_group = QGroupBox("Stems")
        self.stems_layout = QVBoxLayout()
        self.stems_group.setVisible(False)
        self.stems_group.setLayout(self.stems_layout)



        self.stem_layout.addWidget(self.split_stems_file)        
        self.stem_layout.addWidget(self.stems_group)
        self.split_button = QPushButton("Split Stems")
        self.split_button.clicked.connect(self.split_stems)
        self.stem_file_button = QPushButton("Select File")
        self.stem_file_button.clicked.connect(self.select_file_location)

        self.checkbox_layout = QVBoxLayout()
        checkbox_labels = sorted(self.instrument_dict.keys())
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
        self.shift_spinbox.setToolTip("This will run the model multiple times with a random .5 second shift. \nThis will multiply the splitting time by this number.")
        self.shift_label = QLabel("Shifts:")
        self.shift_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.shift_label.setToolTip("This will run the model multiple times with a random .5 second shift. \nThis will multiply the splitting time by this number.")
        cuda = False
        
        if torch.cuda.is_available():
            cuda = True
            self.gpu_checkbox = QCheckBox(f"Use GPU {torch.cuda.get_device_name(0)}", self)
            self.gpu_checkbox.setChecked(True)
            self.gpu_checkbox.clicked.connect(self.check_cuda_devices)
            self.gpu_checkbox.setToolTip("Dramatically reduces split time, but uses a lot of GPU resources.")
        spinbox_layout = QHBoxLayout()
        spinbox_layout.addWidget(self.shift_label)
        spinbox_layout.addWidget(self.shift_spinbox)
        self.stem_layout.addLayout(spinbox_layout)
        self.models_label = QLabel("Select Models:")
        self.models_label.setVisible(False)
        self.stem_layout.addWidget(self.models_label)
        self.model_checkboxes_layout = QHBoxLayout()
        self.model_checkboxes_group = []
        self.stem_layout.addLayout(self.model_checkboxes_layout)
    
        if cuda:
            self.stem_layout.addWidget(self.gpu_checkbox)
        self.stem_layout.addWidget(self.stem_file_button)
        self.split_button.setEnabled(False)
        self.stem_layout.addWidget(self.split_button)
        

        self.left_widget = QWidget()
        self.left_widget.setMinimumWidth(300)
        self.left_widget.setLayout(self.horizontal_layout)
        self.left_widget.setMaximumHeight(350)
        
        self.right_widget = QWidget()
        self.right_widget.setLayout(self.stem_layout)
        self.right_widget.setMinimumWidth(500)
        self.side_by_side_layout.addWidget(self.left_widget)
        self.side_by_side_layout.addWidget(self.vertical_divider)
        self.side_by_side_layout.addWidget(self.right_widget)
        
        self.last_percent_done = 0
        self.progress_label = QLabel("")
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()

        
        self.progress_layout = QVBoxLayout()
        self.split_progress_label = QLabel(f"Shift 1/{self.shift_spinbox.value()}")
        self.split_progress_label.setVisible(False)
        split_progress_layout = QHBoxLayout()
        split_progress_layout.addWidget(self.split_progress_label)
        self.progress_layout.addLayout(self.side_by_side_layout)
        split_progress_layout.addWidget(self.progress_bar)
        
        
        self.progress_layout.addWidget(self.progress_label)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_layout.addLayout(split_progress_layout)

        self.main_layout.addLayout(self.progress_layout, 0)
        self.percent_done = 0
        self.setLayout(self.main_layout)
        self.current_shift = 1

    def check_cuda_devices(self):
        if self.gpu_checkbox.isChecked():
            if torch.cuda.is_available():
                if torch.cuda.device_count() > 1:
                    cuda_prompt = CudaDeviceDialog(self)
                    cuda_prompt.setWindowTitle("Select CUDA Device")
                    cuda_prompt.device.connect(lambda _,device: self.gpu_checkbox.setText(f"Using GPU: {device}"))
                    cuda_prompt.exec()
                else:
                    self.gpu_checkbox.setText(f"Use GPU: {torch.cuda.get_device_name(0)}")
            else:
                QMessageBox.warning(self, "No GPU", "CUDA is not available. The GPU will not be used for processing.")
                self.gpu_checkbox.setChecked(False)
        else:
            QMessageBox.information(self, "GPU Disabled", "The GPU will not be used for processing.")

    def on_checkbox_state_changed(self):
   
        previous_states = {checkbox.text(): checkbox.isChecked() for checkbox in self.model_checkboxes_group}

        self.split_button.setEnabled(self.filepath != "" and any(checkbox.isChecked() for checkbox in self.split_stems_checkbox_group))
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
                models.append(set(self.instrument_dict[inst]))

            models = sorted(list(set.intersection(*models)))

            if len(models) >= 1:
                for model in models:
                    model_checkbox = QCheckBox(model)
                   
                    model_checkbox.setChecked(previous_states.get(model, False))
                    self.model_checkboxes_group.append(model_checkbox)
                    self.model_checkboxes_layout.addWidget(model_checkbox)

        self.models_label.setVisible(any(checkbox.isChecked() for checkbox in self.split_stems_checkbox_group))
    
    

    
    
        

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
            self.config_params['user']['config']['sources']
            self.url_download = url

          

    def show_error(self, error):
        error_message = f"Error: {error}"
        QMessageBox.critical(self, "Error", error_message)
        self.progress_bar.hide()
        self.url_input.setText("")
        
      


    def search_youtube(self):
        if self.platform_yt.isChecked():
            self.ys = YoutubeDownloader(self.url_input.text())
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
        else:

            file, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Audio Files (*.mp3 *.wav *.m4a *.aac *.flac *.opus)", directory=self.config_params['user']['cache']["last_file_path_splitter"])
            if file:
                self.filepath = file
                self.split_stems_file.setText(f"Loaded File: {file}")
                self.config_params['cache']["last_file_path_splitter"] = file
                MainGUI.write_config(self,"last_file_path_splitter",self.config_params['user']['cache']["last_file_path_splitter"])
                
            
            self.split_button.setEnabled(self.filepath != "" and any(checkbox.isChecked() for checkbox in self.split_stems_checkbox_group))
       


    def select_save_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", directory=self.config_params['user']['cache']['last_file_path_downloader'])
        if folder:
            self.save_path = folder
            self.save_label.setText(f"Save Location: {folder}")
            self.config_params['user']['cache']['last_file_path_downloader'] = self.save_path
            MainGUI.write_config(self,'last_file_path_downloader',self.config_params['user']['cache']['last_file_path_downloader'])

  
    def download_video(self):
        self.progress_bar.show()
        url = self.url_download
        format_selected = self.format_dropdown.currentText().split(" - ")[1].lower()
        self.format = format_selected
        quality_selected = self.quality_dropdown.currentText()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a valid URL.")
            return
        
              
        self.download_thread = DownloadThread(url=url, save_path=self.save_path)
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
        
    def update_progress_bar(self, value):
            self.progress_label.setText(f"Downloading... {value}%")
            self.progress_bar.setValue(value)

    def split_complete(self, message):        
        self.progress_label.setText("Splitting complete!")
        self.progress_bar.hide()
        self.current_shift = 1
        self.splitter.quit()
        if self.filepath:
            stems_folder = Path(message)
            self.update_stems_display(stems_folder)

    
    def update_progress(self, message, percent_done=None):
        percentage = 0
        if percent_done:
            percentage = percent_done      
       
        
        self.progress_label.setText(f"{str(percentage)}% || Shift {self.current_shift}/{self.shift_spinbox.value()}")
        self.progress_bar.setValue(int(percentage))

        

    def last_percent_reset(self):
        self.last_percent_done = 0
        self.percent_done = 0
        self.progress_bar.setValue(0)
        
        self.progress_bar.show()
        self.current_shift += 1
        self.split_progress_label.setText(f"Split {self.current_shift}/{self.shift_spinbox.value()}")
    
    


    def split_stems(self):

        if not self.filepath:
            QMessageBox.warning(self, "Error", "Please select or download a file to split.")
            return
        if self.model_checkboxes_group:
            if len(self.model_checkboxes_group) <= 0:
                QMessageBox.warning(self, "Error", "Please select at least one model to split the stems.")
                return
        else:
            QMessageBox.warning(self, "Error", "Please select at least one model to split the stems.")
            return
        info = self.get_models()
        self.shift_label.setVisible(True)
        if info is not None:
            self.splitter = StemSplitter(info[0],sorted(info[1]), self.filepath, shifts=self.shift_spinbox.value(), keep_all=False)
            self.splitter.progress.connect(self.update_progress)
            self.splitter.finished.connect(self.split_complete)
            
            self.splitter.start()            
            self.progress_bar.show()
            self.stems_group.setVisible(True)
        

    

    def download_complete(self,valid,  file_path: Path):
        if valid:
            subprocess.run(['ffmpeg', '-y', '-i', file_path.with_suffix('.webm'), file_path.with_suffix('.wav')],)
            file = str(file_path.absolute())
            file_path.with_suffix('.webm').unlink()
            
            self.downloaded_song_box.reset(file)
            self.downloaded_song_box.file_path = file
            self.downloaded_song_box.setVisible(True)
            self.select_file_location(file)
            self.save_label.setText(f"Save Location: {file}")
            self.filepath = file_path
            self.split_stems_file.setText(f"Loaded File: {file}")
            self.progress_bar.hide()
        else:
            
            print('didnt get a valid file back from downloader')
            raise FileNotFoundError()
        
    def update_stems_display(self, stems_folder: Path):
        for i in reversed(range(self.stems_layout.count())):
            widget = self.stems_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if stems_folder.is_dir():
            
            folder_button = QPushButton()
            folder_button.setIcon(folder_button.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)) 
            folder_button.setToolTip("Open folder containing stems")
            folder_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(stems_folder))))
            self.stems_layout.addWidget(folder_button)

            # Add stem files
            t_file = [file for file in stems_folder.iterdir() if file.is_file()]
            for fname in t_file:
                stem_box = DraggableStemLabel(str(fname.name), fname.absolute())
                self.stems_layout.addWidget(stem_box)
        else:
            self.stems_layout.addWidget(QLabel("No stems found."))

        


def main():

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('icon.ico'))
    window = MainGUI()
    window.show()
    window.activateWindow()
    window.raise_()
    sys.exit(app.exec())
    

if __name__ == "__main__":
    main()