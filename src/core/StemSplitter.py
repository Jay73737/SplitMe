
import os
from demucs.apply import get_progress
from demucs.api import Separator, save_audio
from demucs.audio import f32_pcm
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
        requested_device = device if device is not None else ("cuda" if torch.cuda.is_available() else "cpu")
        self.device = self._resolve_device(requested_device)
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
        self.timer.timeout.connect(self._get_progress_hook)
        self.timer.start(250)

        self.keep_all = keep_all
        self.ext = Path(file_path).suffix
        self.current_status = f"Preparing separation on {self.device}..."
        self._active_separator_name = ""

        for separator in self.models:
            self._prune_bag_for_sources(separator, self.instruments)
        if self.guitar_models is not None:
            self._prune_bag_for_sources(self.guitar_models, ['guitar', 'other'])

    @staticmethod
    def _resolve_device(requested_device):
        requested = str(requested_device)
        if requested.startswith("cuda"):
            if not torch.cuda.is_available():
                print("CUDA requested but torch.cuda.is_available() is False. Falling back to CPU.")
                return "cpu"
            try:
                torch.empty(1, device=requested)
            except Exception as exc:
                print(f"Failed to initialize CUDA device '{requested}': {exc}. Falling back to CPU.")
                return "cpu"
        return requested

    @staticmethod
    def _prune_bag_for_sources(separator, requested_sources):
        # For one-hot weighted bags like htdemucs_ft, this can skip irrelevant submodels.
        model = separator.model
        if not isinstance(model, BagOfModels):
            return
        source_set = set(requested_sources)
        kept_models = []
        kept_weights = []
        for sub_model, model_weights in zip(model.models, model.weights):
            contributes = any(
                (src in source_set) and (weight != 0)
                for src, weight in zip(model.sources, model_weights)
            )
            if contributes:
                kept_models.append(sub_model)
                kept_weights.append(model_weights)

        if kept_models and len(kept_models) < len(model.models):
            model.models = torch.nn.ModuleList(kept_models)
            model.weights = kept_weights
        


    def run(self):
        self._split_stems(self.file_path)

    def _separation_callback(self, callback_data):
        bag_models = int(callback_data.get('models', 1))
        bag_index = int(callback_data.get('model_idx_in_bag', 0)) + 1
        shift_index = int(callback_data.get('shift_idx', 0)) + 1

        stem_text = ", ".join(self.instruments) if self.instruments else "all stems"
        if bag_models > 1:
            self.current_status = (
                f"{self._active_separator_name}: bag model {bag_index}/{bag_models} "
                f"(targeting {stem_text}, shift {shift_index}/{self.shifts})"
            )
        else:
            self.current_status = (
                f"{self._active_separator_name}: separating {stem_text} "
                f"(shift {shift_index}/{self.shifts})"
            )
    
    def _get_progress_hook(self):
        self.progress.emit(self.current_status, int(get_progress()))

    
    def _stems_exist(self, file_path, model):
        
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


    def _split_stems(self, file_path=None):
        
        if file_path:
            dir = Path(file_path).parent
            if not dir.exists():
                os.makedirs(dir, exist_ok=True)
            files = os.listdir(file_path.parent)
            
        else:
            return
        file_name = Path(file_path).stem
        self.stem_list = []
        self.splitter_output = None
        self.waiting = True
        #import pdb; pdb.set_trace()
        for i,m in enumerate(self.models):
            if self._stems_exist(file_path, self.model_names[i]):
                print(f"Stems already exist for model {self.model_names[i]}, skipping...")
                continue
            self._active_separator_name = self.model_names[i]
            self.current_status = f"{self._active_separator_name}: loading audio..."
            m.update_parameter(callback=self._separation_callback, callback_arg={})
            origin, stems = m.separate_audio_file(file_path)
            items = []
            print(type(stems))
                    
            for file,sources in stems.items():                
                out_file = f"{file}.wav"               
                
                out_path = dir / file_name / out_file
                os.makedirs(Path(out_path).parent, exist_ok=True)
                if file in self.instruments:
                    
                    save_audio(sources, rf'{Path(out_path).absolute()}', m.samplerate, as_float=True)
                    if 'other' in file and self.guitar_models is not None:
                        other, guitar = self.guitar_models.separate_audio_file(out_path)
                        #import pdb; pdb.set_trace()
                        other_sources = guitar['other']
                        guitar_source = guitar['guitar']
                        
                        out_path_guitar = dir / file_name / 'guitar.wav'
                        print(out_path_guitar)
                        save_audio(guitar_source, out_path_guitar, self.guitar_models.samplerate, as_float=True)
                        save_audio(other_sources, Path(out_path.with_stem('other')), self.guitar_models.samplerate, as_float=True)
                        
                        print('saved guitar file ', out_path_guitar)
                    print('saved ', file)
                    continue
                
                
                 
            print(f"Stems saved in {dir}/{file_name}/")
        
            

        self.timer.stop()
        self.finished.emit(dir / file_name)


class StemSplitterSingle():
    

    def __init__(self,model, instruments, file_path, shifts=1, keep_all=False, overlap=.5, device=None ):
        
        sys.path.insert(0, Path(__file__).parent)
        requested_device = device if device is not None else ("cuda" if torch.cuda.is_available() else "cpu")
        self.device = StemSplitter._resolve_device(requested_device)
        self.sources_list = ['guitar', 'bass', 'drums', 'vocals', 'other']
        self.stem = None
        self.shifts = shifts
        self.guitar_models=None
        if 'combo' in model:
            temp_model = model
            if 'mdx_extra' not in temp_model:
                
                temp_model.insert(0,'mdx_extra')
            temp_model.remove('combo')
            self.models = [Separator(m, shifts = shifts, split=True, overlap = overlap,progress=True, device=self.device) for m in temp_model]
            self.guitar_models = Separator('htdemucs_6s', shifts=shifts, split=True, overlap=.75, progress=True, device=self.device)
            self.model_names = temp_model 
            if 'other' not in instruments:
                instruments.append('other')
        else:
            self.models = [Separator(m, shifts = shifts, split=True, overlap = overlap,progress=True, device=self.device) for m in model]
            self.model_names = model        
        self.instruments = [inst.lower() for inst in sorted(instruments) if inst.lower()]        
        self.file_path =Path(file_path)
     

        self.keep_all = keep_all
        self.ext = Path(file_path).suffix

        for separator in self.models:
            self._prune_bag_for_sources(separator, self.instruments)
        if self.guitar_models is not None:
            self._prune_bag_for_sources(self.guitar_models, ['guitar', 'other'])

    @staticmethod
    def _prune_bag_for_sources(separator, requested_sources):
        # For one-hot weighted bags like htdemucs_ft, this can skip irrelevant submodels.
        model = separator.model
        if not isinstance(model, BagOfModels):
            return
        source_set = set(requested_sources)
        kept_models = []
        kept_weights = []
        for sub_model, model_weights in zip(model.models, model.weights):
            contributes = any(
                (src in source_set) and (weight != 0)
                for src, weight in zip(model.sources, model_weights)
            )
            if contributes:
                kept_models.append(sub_model)
                kept_weights.append(model_weights)

        if kept_models and len(kept_models) < len(model.models):
            model.models = torch.nn.ModuleList(kept_models)
            model.weights = kept_weights
        


    def run(self):
        return self._split_stems(self.file_path)
    
    

    
    def _stems_exist(self, file_path, model):
        
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


    


    def _split_stems(self, file_path=None):
        
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
            
        
            
            

        self.stem_list = []
        self.splitter_output = None
        self.waiting = True
        for i,m in enumerate(self.models):
            if self._stems_exist(file_path, self.model_names[i]):
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
    def _combine_outputs(self, files, output_path, different_instruments=None):
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



