import numpy as np
from scipy.io import wavfile


import shutil

import demucs.separate as separate

import traceback
from PyQt6.QtCore import QThread, pyqtSignal, QObject
import os
import ffmpeg





class StemSplitter(QThread):
    finished = pyqtSignal(str)

    def __init__(self,model, instruments, file_path, shifts=1, keep_all=False ):
        super().__init__()
        self.stem = None
        self.model = model
        self.instruments = [inst.lower() for inst in instruments]
        self.file_path = file_path
    
        self.paths = []
        self.shifts = shifts
        self.keep_all = keep_all
        self.ext = file_path.split('.')[-1]
        if self.ext == 'mp4':
            ffmpeg.input(file_path).output(file_path.replace('.mp4', '.wav')).run(overwrite_output=True)
            self.ext = 'wav'
            self.file_path = file_path.replace('.mp4', '.wav')  

    def run(self):
        self.split_stems(self.file_path)
    

    

        

    def split_stems(self, file_path=None):
        if file_path:
            file_name = os.path.basename(file_path).split('.')[0]
            dir = os.path.dirname(file_path)
        if not os.path.isdir(dir):   
            os.makedirs(dir, exist_ok=True)
        # Run through each model
        for m in self.model:
            model_output_dir = dir
            os.makedirs(model_output_dir, exist_ok=True)
            try:
                if len(self.instruments) == 1: # Can use the --two-stems flag
                    separate.main(["-n", m, "-o", rf'{model_output_dir}', file_path, '--shifts=' + str(self.shifts), '--two-stems=' + self.instruments[0], '-r'])
                else:
                    separate.main(["-n", m, "-o", rf'{model_output_dir}', file_path, '--shifts=' + str(self.shifts), '-r'])
                    
                    # Get the files in the output directory
                    files = os.listdir(os.path.join(model_output_dir, file_name))
                    rm_files = [] #so we only have the stems we wanted to be stored
                    for file in files:
                        for ins in self.instruments:
                            if ins+'.wav' in rm_files:
                                rm_files.remove(ins+'.wav')
                                continue
                            if ins in file:
                                continue
                            else:
                                if file not in rm_files and file.split('.')[0] not in self.instruments:
                                    rm_files.append(file) 
                                
                    for file in rm_files:
                        if file in files:
                            if os.path.isfile(os.path.join(model_output_dir, file_name, file)):
                                os.remove(os.path.join(model_output_dir, file_name, file))
                os.makedirs(os.path.join(model_output_dir,file_name, m), exist_ok=True)
                files = os.listdir(os.path.join(model_output_dir, file_name))
                
                for file in files:
                    if '[' not in file and os.path.isfile(os.path.join(model_output_dir, file_name, file)):
                        shutil.move(os.path.join(model_output_dir, file_name, file), os.path.join(model_output_dir, file_name, m, file))
                        continue
                    temp_str = "["
                    if '.wav' in file or '.mp3' in file:
                        
                        shutil.move(os.path.join(model_output_dir, file_name, file), os.path.join(model_output_dir, file_name, m, file))
                        if '[' in file:
                            os.rename(os.path.join(model_output_dir, file_name, m, file),
                            os.path.join(model_output_dir, file_name, m, self.instruments[0] +'.' + file.split('.')[1]))
                                
                                
                                
                                    
                    
           
                           
                self.finished.emit(model_output_dir)
            except Exception as e:
                self.finished.emit(f"Error: {str(e)}")
                traceback.print_exc()
              # Reset stdout to original

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
        wavfile.write(output_path, sample_rates[0], avg_audio)


