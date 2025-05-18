import ffmpeg
import demucs.separate

import traceback
from PyQt6.QtCore import QThread, pyqtSignal
import os


class StemSplitter(QThread):
    finished = pyqtSignal(str)

    def __init__(self, model, file_path):
        super().__init__()
        self.stem = None
        self.model = model
        self.file_path = file_path
        os.environ["PATH"] += os.pathsep + "C:\\Users\\justm\\Downloads\\ffmpeg-7.1-essentials_build\\bin"


    def run(self):
        self.split_stems()    
    

    def split_stems(self):
        file_name = os.path.basename(self.file_path).split('.')[0]
        dir = os.path.dirname(self.file_path)  # Get the directory of the file
        output_dir = os.path.join(dir, f"{self.model[0]}_stems")  # Create a subdirectory for stems

        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)

        try:
            if self.model[1]:
                demucs.separate.main(["--two-stems", "vocals", "-n", self.model[0], "--out", output_dir, self.file_path])
            else:
                demucs.separate.main(["-n", self.model[0], "-o", output_dir, self.file_path])
            self.finished.emit(output_dir)
        except Exception as e:
            self.finished.emit(f"Error: {str(e)}")
            traceback.print_exc()