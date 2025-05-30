import sys
import os



# Set environment variables for ffmpeg-python

import subprocess
import numpy as np
from scipy.io import wavfile
import shutil
import traceback
from PyQt6.QtCore import QThread, pyqtSignal, QObject
import ffmpeg
import sys
import time

ffmpeg_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), 'ffmpeg'))
os.environ["PATH"] += os.pathsep + ffmpeg_dir

class UpdaterWorker(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, file_path):

        super().__init__()
        self.running = False
        self.file_path = file_path

    def run(self):
        self.running = True
        with open(self.file_path, 'r', encoding='utf-8') as file:
            while self.running:
                line = file.readline()
                if line:
                    self.update_signal.emit(line)
                
                time.sleep(0.1)

    def stop(self):
        self.running = False
        self.quit()


class StemSplitterOutput(QObject):
    finished = pyqtSignal()
    def __init__(self, process_args ):
        super().__init__()
        self.process_args = process_args
        self.running = True
        self.creationflags = 0
        

    def run(self):

        self.running = True
        # Copy current environment and prepend ffmpeg folder to PATH
       
        print(self.process_args)
        os.environ["PATH"] += os.pathsep + ffmpeg_dir 
        with open("demucs_output.log", "w+", encoding="utf-8") as logfile:
            self.process = subprocess.Popen(
                self.process_args,
                stdout=logfile,  # <--- FIXED: Now you can read from self.process.stdout
                stderr=logfile,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
            self.process.wait()
           


class StemSplitter(QThread):
    finished = pyqtSignal(str)
    progress = pyqtSignal(str, int)
    get_progress = pyqtSignal(int)
    def __init__(self,model, instruments, file_path, shifts=1, keep_all=False ):
        super().__init__()
        self.stem = None
        self.model = model
        self.instruments = [inst.lower() for inst in instruments]
        self.file_path = file_path.replace("\\", "/")

        self.shifts = shifts
        self.progress_length = len(self.model)
        
        self.two_stems = len(self.instruments) == 1 and self.instruments[0] in ['vocals', 'drums', 'bass', 'other', 'guitar', 'piano']

        self.paths = []

        self.keep_all = keep_all
        self.ext = file_path.split('.')[-1]
        if self.ext == 'mp4':
            ffmpeg.input(self.file_path).output(self.file_path.replace('.mp4', '.wav')).run(overwrite_output=True)
            self.ext = 'wav'
            self.file_path = self.file_path.replace('.mp4', '.wav')  


    def run(self):
        self.split_stems(self.file_path)

    
        #self.progress.emit(message)
    
    @staticmethod   
    def get_console_python():
        import shutil
        import os
        
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        python_executable = os.path.join(cur_dir, 'cx', 'Scripts', 'python.exe')
        if not os.path.exists(python_executable):
            python_executable = shutil.which('python')
            if not python_executable:
                raise EnvironmentError("Python executable not found in the expected location or in PATH.")
        return python_executable


    def stems_exist(self, file_path, model):
        file_name = os.path.basename(file_path).split('.')[0]
        dir = os.path.dirname(file_path).replace("\\", "/")
        print(f"Checking stems in directory: {dir}")
        if not os.path.isdir(dir):
            return False
        model_output_dir = os.path.join(dir, f"{file_name}").replace("\\", "/")
        if not os.path.isdir(model_output_dir):
            return False
        files = os.listdir(model_output_dir)
        if not files:
            return False
        for file in files:
            if file.endswith('.wav') or file.endswith('.mp3'):
                if file.split('.')[0] not in self.instruments:
                    return False
        return True


    def split_stems(self, file_path=None):
        
        if file_path:
            file_name = os.path.basename(file_path).split('.')[0]
            print(f"File name: {file_name}")
            dir = os.path.dirname(file_path).replace("\\", "/")
            print(f"Directory: {dir}")
        if not os.path.isdir(dir):
            os.makedirs(dir, exist_ok=True)
        
        self.splitter_output = None
        self.waiting = True
        for m in self.model:
            
            model_output_dir = os.path.join(dir, f"{file_name}_{m}_stems")
            model_output_dir = model_output_dir.replace("\\", "/")
            if self.stems_exist(model_output_dir, m):
                print(f"Stems already exist for model {m}, skipping...")
                continue
            print(f"Model output directory: {model_output_dir}")
            os.makedirs(model_output_dir, exist_ok=True)
            try:                    
                if len(self.instruments) == 1:
                    process_args = [self.get_console_python(), "-m", "demucs", "-n", m, "-o", os.path.abspath(model_output_dir).replace("\\", "/"), os.path.abspath(file_path), '--shifts=' + str(self.shifts), '--two-stems=' + self.instruments[0]]
                    self.splitter_output = StemSplitterOutput(process_args)
                 
                    self.splitter_output.run()
                else:
                    process_args = [self.get_console_python(), "-m", "demucs", "-n", m, "-o", os.path.abspath(model_output_dir).replace("\\", "/"), os.path.abspath(file_path), '--shifts=' + str(self.shifts)]
                    self.splitter_output = StemSplitterOutput(process_args)

                    self.splitter_output.run()

                temp_directory = os.path.join(model_output_dir, m, file_name).replace("\\", "/")
                print(f"Temp directory: {temp_directory}")
                files = os.listdir(temp_directory)
                print(f"Files in temp directory: {files}")

                for file in files:
                    if file.endswith('.wav') or file.endswith('.mp3'):
                        if file.split('.')[0] in self.instruments:
                            shutil.move(os.path.join(temp_directory,file),model_output_dir)
                            continue
                        elif file.split('.')[0] not in self.instruments:
                            os.remove(os.path.join(temp_directory,file))
                    else:
                        shutil.move(os.path.join(temp_directory,file),model_output_dir)

                shutil.rmtree(os.path.join(model_output_dir, m).replace("\\", "/"))

                    
                
                

            except Exception as e:
                self.finished.emit(f"Error: {str(e)}")
                traceback.print_exc()
                return
        self.finished.emit(f"Stem splitting completed for {str(self.model)} models.")


        #self.combine_outputs(os.listdir(os.path.join(model_output_dir, file_name)), os.path.join(model_output_dir, file_name, 'combined.wav'), different_instruments=self.instruments)

    # Combines the outputs of the stems, not sure whether this helps or not, but keeping it for potential future use
    def combine_outputs(self, files, output_path, different_instruments=None):
        if different_instruments:
            combining = len(different_instruments)
            sound_list = []
            for i in range(combining):
                sound_list.append(different_instruments[i])

        sample_rates = []
        audio_data = []

        for file in files:
            rate, data = wavfile.read(file)
            sample_rates.append(rate)
            audio_data.append(data.astype(np.float32))
        if len(set(sample_rates)) != 1:
            raise ValueError("All audio files must have the same sample rate") 
        min_length = min([len(d) for d in audio_data])
        audio_data = [d[:min_length] for d in audio_data]
        avg_audio = np.mean(audio_data, axis=0)
        avg_audio = np.clip(avg_audio, -32768, 32767).astype(np.int16)
        os.makedirs(output_path.split('.')[0].split('\\')[0], exist_ok=True)
        wavfile.write(os.path.join(output_path, 'mixture.wav'), sample_rates[0], avg_audio)


