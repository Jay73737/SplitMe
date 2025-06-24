
import os
from _demucs.apply import get_progress
from _demucs.api import Separator, save_audio
from _demucs.audio import f32_pcm
import torch
import numpy as np
from scipy.io import wavfile
from PyQt6.QtCore import QThread, pyqtSignal,  pyqtSlot, QTimer
import ffmpeg
from pathlib import Path
import time
import sys



class UpdaterWorker(QThread):
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    def __init__(self, file_path):

        super().__init__()
        self.running = False
        self.file_path = file_path

    def run(self):
        self.running = True
        
        while self.running:
            with open(self.file_path, 'a+', encoding='utf-8') as file:
            
                line = file.readline()
                if line:
                    self.update_signal.emit(line)
                
            time.sleep(0.3)

    @pyqtSlot()
    def is_finished(self):
        self.finished_signal.emit()
        self.stop()

    def stop(self):
        self.running = False
        self.quit()



            
           


class StemSplitter(QThread):
    finished = pyqtSignal(Path)
    progress = pyqtSignal(str, int)
    get_args = pyqtSignal(list)

    def __init__(self,model, instruments, file_path, shifts=1, keep_all=False, overlap=.5 ):
        super().__init__()
        sys.path.insert(0, Path(__file__).parent)
        self.sources_list = ['guitar', 'bass', 'drums', 'vocals', 'other']
        self.stem = None
        self.shifts = shifts
        self.guitar_models=None
        if 'combo' in model:
            temp_model = model
            if 'mdx_extra' not in temp_model:
                
                temp_model.insert(0,'mdx_extra')
            temp_model.remove('combo')
            self.models = [Separator(m, shifts = shifts, split=True, overlap = overlap,progress=True) for m in temp_model]
            self.guitar_model = Separator('htdemucs_6s', shifts=shifts, split=True, overlap=.75, progress=True)
            self.model_names = temp_model 
            if 'other' not in instruments:
                instruments.append('other')
        else:
            self.models = [Separator(m, shifts = shifts, split=True, overlap = overlap,progress=True) for m in model]
            self.model_names = model        
        self.instruments = [inst.lower() for inst in sorted(instruments) if inst.lower()]        
        self.file_path =Path(file_path)
        self.timer = QTimer()
        self.timer.timeout.connect(self.get_progress_hook)
        self.timer.start(250)

        self.keep_all = keep_all
        self.ext = Path(file_path).suffix
        


    def run(self):
        self.split_stems(self.file_path)
    
    def get_progress_hook(self):
        self.progress.emit("good ",int(get_progress()))

    
    def stems_exist(self, file_path, model):
        
        self.ext_out = 'wav'
        file_path = Path(file_path)
        file_name = file_path.name
        dir = file_path.parent
        print(f"Checking stems in directory: {dir}")
        if not dir.is_dir():
            return False
        model_output_dir = dir / file_name
        if not model_output_dir.is_dir():
            return False
        files = os.listdir(model_output_dir)
        if not files:
            return False
        for file in files:
            if Path(file).name not in self.instruments:
                return False
        return True


    def split_stems(self, file_path=None):
        
        if file_path:
            file_path = Path(file_path)
            print('fp', file_path)
            file_name = file_path.stem
            ext = file_path.suffix
            if self.ext != ext:
                ffmpeg.input(self.file_path).output(Path(file_path).with_suffix('.wav')).run(overwrite_output=True)
            print(f"File name: {file_name}")
            dir = Path(file_path).parent
            print(f"Directory: {dir}")
            if not dir.exists():
                os.makedirs(dir, exist_ok=True)
            files = os.listdir(file_path.parent)
            
        else:
            return

        self.stem_list = []
        self.splitter_output = None
        self.waiting = True
        for i,m in enumerate(self.models):
            if self.stems_exist(file_path, self.model_names[i]):
                print(f"Stems already exist for model {self.model_names[i]}, skipping...")
                continue
            origin, stems = m.separate_audio_file(file_path)
            items = []
            print(type(stems))
                    
            for file,sources in stems.items():                
                out_file = f"{file}{ext}"               
                
                out_path = dir / file_name / out_file
                os.makedirs(Path(out_path).parent, exist_ok=True)
                if file in self.instruments:
                    
                    save_audio(sources, rf'{out_path.absolute()}', m.samplerate, as_float=True)
                    if 'other' in file and self.guitar_model is not None:
                        other, guitar = self.guitar_model.separate_audio_file(out_path)
                        #import pdb; pdb.set_trace()
                        other_sources = guitar['other']
                        guitar_source = guitar['guitar']
                        
                        out_path_guitar = dir / file_name / 'guitar.wav'
                        print(out_path_guitar)
                        save_audio(guitar_source, out_path_guitar, self.guitar_model.samplerate, as_float=True)
                        save_audio(other_sources, Path(out_path.with_stem('other')), self.guitar_model.samplerate, as_float=True)
                        
                        print('saved guitar file ', out_path_guitar)
                    print('saved ', file)
                    continue
                
                
                 
            print(f"Stems saved in {dir}/{file_name}/")
        
            

        self.timer.stop()
        self.finished.emit(dir / file_name)

       
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



