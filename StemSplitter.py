import numpy as np
from scipy.io import wavfile


import shutil




import traceback
from PySide6.QtCore import QThread, Signal, QObject
import os
import ffmpeg

class StemSplitterOutput(QObject):
    update = Signal(str)
    def __init__(self, process_args ):
        super().__init__()
        self.process_args = process_args
        self.running = True
        

    def run(self):
        import subprocess
        self.running = True
        self.process = subprocess.Popen(
            self.process_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",  
            bufsize=1 
        )
        
        for line in self.process.stdout:
            if not self.running:
                break
            if line:
                self.update.emit(line)
                print(line, end="")
        self.process.stdout.close()
        self.process.wait()

    def stop(self):
        self.running = False
        

      



class StemSplitter(QThread):
    finished = Signal(str)
    progress = Signal(str, int)
    get_progress = Signal(int)
    def __init__(self,model, instruments, file_path, shifts=1, keep_all=False ):
        super().__init__()
        self.stem = None
        self.model = model
        self.instruments = [inst.lower() for inst in instruments]
        self.file_path = file_path
        self.shifts = shifts
        self.progress_length = len(self.model)
        

        
        
        self.paths = []
        
        self.keep_all = keep_all
        self.ext = file_path.split('.')[-1]
        if self.ext == 'mp4':
            ffmpeg.input(file_path).output(file_path.replace('.mp4', '.wav')).run(overwrite_output=True)
            self.ext = 'wav'
            self.file_path = file_path.replace('.mp4', '.wav')  

    def run(self):
        self.split_stems(self.file_path)
    

    def update_progress(self, message):
        
        self.progress.emit(message, self.progress_length)
        #self.progress.emit(message)
       

        

    def split_stems(self, file_path=None):
        if file_path:
            file_name = os.path.basename(file_path).split('.')[0]
            dir = os.path.dirname(file_path)
        if not os.path.isdir(dir):
            os.makedirs(dir, exist_ok=True)
       
        
        self.splitter_output = None
        for m in self.model:
            model_output_dir = os.path.join(dir, f"{file_name}_{m}_stems")
            os.makedirs(model_output_dir, exist_ok=True)
            try:                    

                if len(self.instruments) == 1:
                    process_args = ["demucs","-n", m, "-o", rf'{model_output_dir}', file_path, '--shifts=' + str(self.shifts), '--two-stems=' + self.instruments[0]] # Can use the --two-stems flag
                    
                    self.splitter_output = StemSplitterOutput(process_args)
                    self.splitter_output.update.connect(self.update_progress)
                    self.splitter_output.run()
                    
                    
                    #separate.main(["-n", m, "-o", rf'{model_output_dir}', file_path, '--shifts=' + str(self.shifts), '--two-stems=' + self.instruments[0]])
                else:
                    
                    process_args = ["demucs","-n", m, "-o", rf'{model_output_dir}', file_path, '--shifts=' + str(self.shifts)] # Can use the --two-stems flag
                    #self.progress.emit(output)
                    #separate.main(["-n", m, "-o", rf'{model_output_dir}', file_path, '--shifts=' + str(self.shifts)])
                    self.splitter_output = StemSplitterOutput(process_args)
                    self.splitter_output.update.connect(self.update_progress)
                    self.splitter_output.run()
                   
                temp_directory = os.path.join(model_output_dir, m, file_name)
                print(f"Temp directory: {temp_directory}")
                files = os.listdir(temp_directory)
                print(f"Files in temp directory: {files}")
                
                for file in files:
                    if len(self.instruments) == 1:
                        if file.endswith('.wav') and file.startswith(self.instruments[0]):
                            shutil.move(os.path.join(temp_directory, file), model_output_dir)
                            continue
                        else:
                            if file.split('.')[0] not in self.instruments:
                                os.remove(os.path.join(temp_directory, file))
                    else:
                        if file.endswith('.wav') and file.split('.')[0] not in self.instruments:
                            os.remove(os.path.join(temp_directory, file))
                        else:
                            shutil.move(os.path.join(temp_directory, file), model_output_dir)
                shutil.rmtree(os.path.join(model_output_dir, m))
                            
                    
                    
                
                

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



