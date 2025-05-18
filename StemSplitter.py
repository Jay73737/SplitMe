import numpy as np
import soundfile as sf



import demucs.separate

import traceback
from PyQt6.QtCore import QThread, pyqtSignal
import os


class StemSplitter(QThread):
    finished = pyqtSignal(str)

    def __init__(self, model, file_path, shifts=1):
        super().__init__()
        self.stem = None
        self.model = model
        self.file_path = file_path
        self.paths = []
        self.shifts = shifts


    def run(self):
        self.split_stems()    
    

    def split_stems(self):
        file_name = os.path.basename(self.file_path).split('.')[0]
        dir = os.path.dirname(self.file_path)  # Get the directory of the file
        output_dir = os.path.join(dir, f"{self.model[0]}_stems")  # Create a subdirectory for stems

        # Ensure the output directory exists--------------------------------
        os.makedirs(output_dir, exist_ok=True)
        for s in self.model:
            try:
                
                demucs.separate.main(["-n", s, "-o", output_dir, self.file_path, '--shifts=' + str(self.shifts)])
                self.finished.emit(output_dir)
            except Exception as e:
                self.finished.emit(f"Error: {str(e)}")
                traceback.print_exc()

    

#for testing
#s = StemSplitter(["htdemucs"], "C:\\Users\\justm\\Desktop\\Code\\New folder\Eagles - Hotel California (Lyrics).wav")
#s.split_stems(2)
