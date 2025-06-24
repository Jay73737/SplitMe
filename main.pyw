import sys
import os
import subprocess
import psutil

from PyQt6.QtWidgets import (
    QApplication, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QComboBox, QMessageBox, QProgressBar, 
    QCheckBox, QWidget, QPushButton,QStyle,QHBoxLayout, QFrame,
      QSpinBox, QSizePolicy, QGroupBox, QSlider
)
from PyQt6.QtGui import QIcon, QDesktopServices
from PyQt6.QtCore import Qt, QUrl
from YoutubeDownloader import YoutubeDownloader
from Downloader import DownloadThread
from StemSplitter import StemSplitter
from Results import ResultsWindow

from GUIComponents import DraggableStemLabel, CudaDeviceDialog, APIKeyWindow
from contextvars import ContextVar
from pathlib import Path
import json
import traceback

_ffmpeg_location = ContextVar('ffmpeg_location', default=None)


_ffmpeg_location.set('ffmpeg')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

import torch



# Main GUI class for the app
class MainGUI(QWidget):

    def __init__(self):
        super().__init__()
        self.url_download = None
        self.sources = ['vocals', 'bass', 'drums', 'other', 'guitar', 'piano']
        
        
        
        self.instrument_dict = {
            "Vocals": ["htdemucs", "htdemucs_ft", "mdx_extra", "htdemucs_6s", "combo"], 
            "Bass": ["htdemucs", "htdemucs_ft", "mdx_extra", "htdemucs_6s", "combo"], 
            "Drums": ["htdemucs", "htdemucs_ft", "mdx_extra", "htdemucs_6s", "combo"],
            "Guitar": ["htdemucs_6s", "combo"],
            "Piano": ["htdemucs_6s"],
            "Other": ["htdemucs", "htdemucs_ft", "mdx_extra", "htdemucs_6s", "combo"]
        }
        last_file_downloader = None
        last_file_splitter = None
        self.config_params= {}
        try:
            self.load_config('config.json')
        except:
            self.config_params = {
                "api_key": "",
                "cache": {
                    "last_file_path_downloader": Path(__file__),
                    "last_file_path_splitter": Path(__file__),
                    "sources": []
                }
            }
            
        




        self.file_formats = [
         "Audio - wav","Audio - mp3", "Video - mp4"
        ]
        sys.path.insert(0, Path(__file__).absolute() / "demucs")

        self.filepath = ""
        self.split_ind = 1
        try:
            with open(Path(__file__).parent / 'config.json', 'r') as f:
                self.config_params = json.load(f)
            
                key = self.config_params['api_key']
            
        except:
            traceback.print_exc()
            api_window = APIKeyWindow(self)

            api_window.finished.connect(self.config_writer)
            api_window.show()
            result = api_window.exec()
        self.setup_ui()

    def load_config(self, path):
        if os.path.exists(path):
            with open(path, "r") as f:
                self.config_params = json.load(f)
                return self.config_params
        else:
            self.config_params = {
                "api_key": "",
                "cache": {
                    "last_file_path_downloader": Path(__file__),
                    "last_file_path_splitter": Path(__file__),
                    "sources": []
                }
            }
            return self.config_params

    def save_config(path, config):
        with open(path, "w") as f:
            json.dump(config, f, indent=4)


    # Writes the config data passed in args to the config file. 
    # class_var will usually be self (or whatever self.config_params you want to write)
    # param is the parameter to update (api_key, cache)
    # value is the value you want to set it to
    @staticmethod
    def write_config(class_var,param,value):
        
        try:
            temp = None
            with open(Path(__file__).parent / 'config.json', 'r') as f:            
                temp = json.load(f)
                if param == 'sources':
                    if len(temp['cache']['sources']) > 50:
                        temp['cache']['sources'].pop(0)
                        temp['cache']['sources'].append(value)
                        class_var.config_params['cache']['sources'] = temp['cache']['sources']
                    else:
                        temp['cache']['sources'].append(value)
                        class_var.config_params['cache']['sources'] = temp['cache']['sources']
                
                elif param == 'api_key':
                    temp['api_key'] = value
                else:
                    temp['cache'][param] = value
            os.remove(Path(__file__).parent / 'config.json')
            with open(Path(__file__).parent / 'config.json', 'w') as f:
                json.dump(temp, f)
                class_var.config_params = temp
        except:
            if not os.path.exists(Path(__file__).parent / 'config.json'):
                with open(Path(__file__).parent / 'config.json', 'a+') as f:
                    json.dump(temp, f)
                    class_var.config_params = temp


    # Setus up main UI layout
    def setup_ui(self):

        self.setWindowTitle("Stem Splitter")
        self.setGeometry(200, 400, 600, 350)
        self.main_layout = QVBoxLayout()
        self.side_by_side_layout = QHBoxLayout()
        self.horizontal_layout = QVBoxLayout()       

        # Youtube API checkbox     
        self.platform_yt = QCheckBox("Use YouTube API?", self)
        self.platform_yt.setChecked(True)
        self.platform_yt.setToolTip("Use YouTube API to search for videos. \nIf unchecked, you can paste a direct URL.")
        
        ## Yoube URL/Search text box and label and search button
        self.url_label = QLabel("URL/Search:")
        self.url_input = QLineEdit(self)
        self.url_input.returnPressed.connect(self.search_youtube)
        self.link_layout = QVBoxLayout()
        self.link_layout = QVBoxLayout()
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_youtube)
        self.link_layout.addWidget(self.search_button)
        self.link_layout.addWidget(self.search_button)

        # Select format dropdown and quality dropdown
        self.format_label = QLabel("Select Format:")
        self.quality_dropdown = QComboBox(self)
        self.quality_dropdown.addItems(["Low (64kbps)", "Medium (128kbps)", "High (192kbps)"])
        self.quality_dropdown.setDisabled(True)
        self.format_dropdown = QComboBox(self)
        self.format_dropdown.addItems(self.file_formats)      
        self.format_dropdown.currentTextChanged.connect(lambda: self.quality_dropdown.setDisabled('Audio - mp3' not in self.format_dropdown.currentText()))
        self.quality_label = QLabel("Select Audio Quality:")

        # Select Save location, and download buttons
        self.save_button = QPushButton("Select Save Location")
        self.save_button.clicked.connect(self.select_save_location)
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.download_video)
        self.save_path = Path(__file__).parent.absolute()
        self.save_label = QLabel(
            f"Save Location: {self.save_path}"
        )
        # Media player for when song is downloaded, might move to other side
        self.downloaded_song_box = DraggableStemLabel("None", None)
        self.downloaded_song_box.setVisible(False)
        
        # This is for the entire left side up to the divider
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
        
        # Divider in the middle
        self.vertical_divider = QFrame()
        self.vertical_divider.setFrameShape(QFrame.Shape.VLine) 
        self.vertical_divider.setFrameShadow(QFrame.Shadow.Sunken)
        self.right_side_total = QVBoxLayout()
        # Layout for stems
        self.stem_layout = QVBoxLayout()
        self.split_stems_file = QLabel("Loaded File: ")
        self.delete_original = QCheckBox("Delete original file?") # If you want to delete the downloaded song
  
        
        # The different sources that can be separated
        self.stems_group = QGroupBox("Stems")
   
        self.stems_group.setVisible(False)
        
        self.right_side_total.addWidget(self.split_stems_file)  
        self.right_side_total.addWidget(self.delete_original)
        self.right_side_total.addWidget(self.split_stems_file)        
        self.right_side_total.addWidget(self.stems_group)

        
        
        self.stem_box = QFrame(self)

        self.stem_box.setObjectName("myFrame")
        self.stem_box.setFrameShape(QFrame.Shape.Box)
        self.stem_box.setLineWidth(2)
        self.stem_box.setStyleSheet("myFrame { border: 2px solid #888; border-radius: 6px; background-color: transparent; }" )
        self.checkbox_layout = QVBoxLayout()
       
        checkbox_labels = sorted(self.instrument_dict.keys())
        checkbox_labels = sorted(self.instrument_dict.keys())
        self.split_stems_checkbox_group = []
        for label in checkbox_labels:
            checkbox = QCheckBox(label)
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(self.on_checkbox_state_changed)
            self.split_stems_checkbox_group.append(checkbox)
            self.checkbox_layout.addWidget(checkbox)
        self.right_side_total.addLayout(self.checkbox_layout)
        self.overlap_label = QLabel(f"Overlap {50*1.5/100:.2f} sec")
        self.overlap_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.overlap_label.setToolTip('Changes how much the segments of the track overlap when recombining. Higher values take longer but improve overall quality.')
        self.overlap_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.overlap_slider.setFixedWidth(100)
        self.overlap_slider.setRange(0, 100)
        self.overlap_slider.setValue(50)
        self.overlap_slider.valueChanged.connect(self.update_overlap_stem)
        self.overlap_slider.setToolTip('Changes how much the segments of the track overlap when recombining. Higher values take longer but improve overall quality.')
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
        spinbox_layout.addWidget(self.overlap_label)
        spinbox_layout.addWidget(self.overlap_slider)
        spinbox_layout.addStretch(1)
        spinbox_layout.addWidget(self.shift_label)
        spinbox_layout.addWidget(self.shift_spinbox)
        self.stem_layout.addLayout(spinbox_layout)
        self.models_label = QLabel("Select Models:")
        self.models_label.setVisible(False)
        stems_box = QVBoxLayout()
        stems_box.addWidget(self.models_label)
        
        

        self.model_checkboxes_layout = QHBoxLayout()
        
        self.model_checkboxes_group = []
        self.model_group = QGroupBox(self.stem_box)
        self.model_group.setObjectName('model')
        self.model_group.setStyleSheet("myFrame { border: 2px solid #888; border-radius: 6px; background-color: transparent; }" )
        
    
        if cuda:
            self.stem_layout.addWidget(self.gpu_checkbox)    
        stems_box.addLayout(self.model_checkboxes_layout)
        self.model_group.setLayout(stems_box)
        self.stem_layout.addWidget(self.model_group)
        self.btn_layout = QVBoxLayout()
        
        # Split stems buttons
        self.split_button = QPushButton("Split Stems")
        self.split_button.clicked.connect(self.split_stems)
        self.stem_file_button = QPushButton("Select File")
        self.stem_file_button.clicked.connect(self.select_file_location)

        self.btn_layout.addWidget(self.stem_file_button)
        self.split_button.setEnabled(False)
        self.btn_layout.addWidget(self.split_button)    
        self.stem_box.setLayout(self.stem_layout)    
        self.right_side_total.addWidget(self.stem_box)
        self.right_side_total.addLayout(self.btn_layout)
        self.left_widget = QWidget()
        self.left_widget.setMinimumWidth(300)
        self.left_widget.setMaximumHeight(500)
        self.left_widget.setLayout(self.horizontal_layout)        
        
        self.right_widget = QWidget()
        self.right_widget.setLayout(self.right_side_total)
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
        self.stem_box.repaint()
        self.current_shift = 1

    def update_overlap_stem(self, value):
        self.overlap_label.setText(f"Overlap {(value/100)*1.5:.2f} sec")

    # Checks if cuda is available and if so, opens a dialog to select which device you want to use
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

    # When a stem checkbox is clicked, this updates the models that are available for those stems (eg. guitar and piano are only on htdemucs_6s)
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

        self.stem_box.repaint()
        if selected_instruments:
            for inst in selected_instruments:
                models.append(set(self.instrument_dict[inst]))

            models = sorted(list(set.intersection(*models)))

            

            if len(models) >= 1:
                for model in models:
                    if 'Guitar' not in selected_instruments and 'combo' in models:
                        models.remove('combo')
                        continue
                    model_checkbox = QCheckBox(model)
                   
                    model_checkbox.setChecked(previous_states.get(model, False))
                   
                    model_checkbox.setChecked(previous_states.get(model, False))
                    self.model_checkboxes_group.append(model_checkbox)
                    self.model_checkboxes_layout.addWidget(model_checkbox)
            
        self.models_label.setVisible(any(checkbox.isChecked() for checkbox in self.split_stems_checkbox_group))
    
    
    
    

    
    
        
    # Result returned from the youtube api search are sent here.

    def set_url(self, input_dict):
    
        self.results_window = ResultsWindow(input_dict, self)
        self.results_window.finished.connect(self.on_link_clicked)
        self.results_window.exec()

    # Sets the text in the text input to the url of the youtube video
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
            if 'sources' in self.config_params:

                self.config_params['cache']['sources'].append()
            else:
                self.config_params['cache']['sources'] = [url]
            self.url_download = url

          
    # Displays an error and hides progress bar.
    def show_error(self, error):
        error_message = f"Error: {error}"
        QMessageBox.critical(self, "Error", error_message)
        self.progress_bar.hide()
        self.url_input.setText("")
        
      

    # Searches for the URL through the youtube API.  Must have an api_key in the config.json storage file in the root directory (this should be created automatically)
    def search_youtube(self):
        if self.platform_yt.isChecked():
            self.ys = YoutubeDownloader(self.url_input.text(), self.config_params)
            
            self.ys.finished.connect(self.set_url)
            self.ys.error.connect(self.show_error)
            self.ys.start()
        
        
        
    # Toggles the progress bar on and off
    def toggle_loading(self):
        if self.progress_bar.isVisible():
            self.progress_bar.hide()
        else:
            self.progress_bar.show()
            
    # Sets the file location of the splitter to an audio file specified by file_location.
    # Enables/Disables the Split Stems button based on if all of the required selections are made.
    def select_file_location(self, file_location = None):
        if file_location:
            self.filepath = file_location
            if ' ' in self.filepath:
                self.filepath = rf'{self.filepath}'
            self.split_stems_file.setText(f"Loaded File: {self.filepath}")
            return
        else:
        

            file, _ = QFileDialog.getOpenFileName(self, "Select File", self.config_params['cache']["last_file_path_splitter"], "Audio Files (*.mp3 *.wav *.m4a *.aac *.flac *.opus)", )
            if file:
                self.filepath = file
                self.split_stems_file.setText(f"Loaded File: {file}")
                self.config_params['cache']["last_file_path_splitter"] = file
                MainGUI.write_config(self,"last_file_path_splitter",self.config_params['cache']["last_file_path_splitter"])
                
            
            self.split_button.setEnabled(self.filepath != "" and any(checkbox.isChecked() for checkbox in self.split_stems_checkbox_group))
       


    # Selects the save location for the split stems
    def select_save_location(self):
        
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", directory=self.config_params['cache']['last_file_path_downloader'])
        if folder:
            self.save_path = folder
            self.save_label.setText(f"Save Location: {folder}")
            self.config_params['cache']['last_file_path_downloader'] = self.save_path
            MainGUI.write_config(self,'last_file_path_downloader',self.config_params['cache']['last_file_path_downloader'])


  
    # Creates the download thread to download the video.
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

    
     
    # Gets the models selected by the checkboxes for splitting
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
        
    def is_file_in_use(filepath):
        for proc in psutil.process_iter(['open_files']):
            for file in proc.info['open_files'] or []:
                if file.path == filepath:
                    return True
        return False

    # Runs when the split is complete, calls update_stems_display which is for displaying/playing the split audio files
    def split_complete(self, message):        
        self.progress_label.setText("Splitting complete!")
        self.progress_bar.hide()
        self.current_shift = 1
        self.splitter.quit()
        if self.delete_original.isChecked():
            print('Attempting to delete original file ', Path(message).with_suffix('.wav'))
            print(os.path.exists(Path(message).with_suffix('.wav')))
            if os.path.exists(Path(message).with_suffix('.wav')):
                self.downloaded_song_box.set_audio_source("")
                self.downloaded_song_box = DraggableStemLabel("","",self)
                self.downloaded_song_box.setVisible(False)
                
                os.remove(Path(message).with_suffix('.wav'))
                print('removed ' + str(message))

        if self.filepath:
            stems_folder = Path(message)
            self.update_stems_display(stems_folder)
            

    # Progress for stem splitting
    def update_progress(self, message, percent_done=None):
        percentage = 0
        if percent_done > percentage:       
            percentage = percent_done      
        if percent_done >= 98:
            self.current_shift += 1
        
        self.progress_label.setText(f"{str(percentage)}% || Shift {self.current_shift}/{self.shift_spinbox.value()}")
        self.progress_bar.setValue(int(percentage))   

    # Called when the Split button is pressed, creates as new thread to split stems
    def split_stems(self):
        self.downloaded_song_box.reset("")
        self.downloaded_song_box.setVisible(True)
        if not self.filepath:
            QMessageBox.warning(self, "Error", "Please select or download a file to split.")
            return
        if self.model_checkboxes_group:
            if len(self.model_checkboxes_group) <= 0:
                QMessageBox.warning(self, "Error", "Please select at least one model to split the stems.")
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
            self.splitter = StemSplitter(info[0],sorted(info[1]), self.filepath, shifts=self.shift_spinbox.value(), keep_all=False, overlap=float(self.overlap_slider.value()*1.5/100))
            self.splitter.progress.connect(self.update_progress)
            self.splitter.finished.connect(self.split_complete)
            
            self.splitter.start()            
            self.progress_bar.show()
            self.stems_group.setVisible(True)
        

    
    # Runs when the download is finished.  Converts the .webm file to a .wav file with ffmpeg, then sets the downloaded song box to the downloaded file
    def download_complete(self,valid,  file_path: Path):
        file = str(file_path.absolute())
        if valid:
            if file_path.suffix != '.wav':
                ffmpg = subprocess.Popen(['ffmpeg', '-y', '-i', str(Path(file_path).with_suffix('.webm').absolute()), str(Path(file_path).with_suffix('.wav').absolute())])
                ffmpg.wait()
                file = str(file_path.absolute().with_suffix('.wav'))
                if os.path.exists(file):
                    os.remove(Path(file).with_suffix('.webm'))
            
            
            self.downloaded_song_box.reset(file)
            self.downloaded_song_box.file_path = file
            self.downloaded_song_box.setVisible(True)
            self.select_file_location(file)
            self.save_label.setText(f"Save Location: {file}")
            self.filepath = file
            self.split_stems_file.setText(f"Loaded File: {file}")
            self.progress_bar.hide()
        else:
            
            print('didnt get a valid file back from downloader')
            raise FileNotFoundError()

    # This updates the draggable stem boxes that are displayed after the stems are split.    
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
    

