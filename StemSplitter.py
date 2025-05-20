import numpy as np
from scipy.io import wavfile



import demucs.separate

import traceback
from PyQt6.QtCore import QThread, pyqtSignal
import os


class StemSplitter():#QThread):
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

    def run(self):
        self.split_stems()
    

    def split_stems(self):
        file_name = os.path.basename(self.file_path).split('.')[0]
        dir = os.path.dirname(self.file_path)
        base_output_dir = os.path.join(dir, f"{self.model[0]}_stems")

        os.makedirs(base_output_dir, exist_ok=True)
        for m in self.model:
            model_output_dir = os.path.join(base_output_dir, m)
            os.makedirs(model_output_dir, exist_ok=True)
            try:
                if len(self.instruments) == 1:
                    demucs.separate.main(["-n", m, "-o", base_output_dir, self.file_path, '--shifts=' + str(self.shifts), '--two-stems=' + self.instruments[0]])
                else:
                    demucs.separate.main(["-n", m, "-o", base_output_dir, self.file_path, '--shifts=' + str(self.shifts)])
                # The separated files should be in base_output_dir/m/file_name/
                target_dir = os.path.join(model_output_dir, file_name)
                if os.path.exists(target_dir):
                    split_files = os.listdir(target_dir)
                    for file in split_files:
                        keep = any(p in file for p in self.instruments)
                        if keep:
                            print(file)
                        elif not self.keep_all:
                            os.remove(os.path.join(target_dir, file))
                            print(f"Removed {file} from {target_dir}")
                    #self.finished.emit(target_dir)
            except Exception as e:
                self.finished.emit(f"Error: {str(e)}")
                traceback.print_exc()

    def combine_outputs(self, files, output_path):

        # Read all files and store sample rates and data
        sample_rates = []
        audio_data = []

        for file in files:
            rate, data = wavfile.read(file)
            sample_rates.append(rate)
            audio_data.append(data.astype(np.float32))  # Convert to float for safe averaging

        # Ensure all sample rates match
        if len(set(sample_rates)) != 1:
            raise ValueError("All audio files must have the same sample rate")

        # Trim or pad to the same length
        min_length = min([len(d) for d in audio_data])
        audio_data = [d[:min_length] for d in audio_data]

        # Average the audio
        avg_audio = np.mean(audio_data, axis=0)

        # Clip to int16 range and convert back
        avg_audio = np.clip(avg_audio, -32768, 32767).astype(np.int16)
        os.makedirs(output_path.split('.')[0].split('\\')[0], exist_ok=True)
        # Save to output file
        wavfile.write(output_path, sample_rates[0], avg_audio)



st = StemSplitter(model=["htdemucs", "mdx", "htdemucs_ft", "mdx_extra"], instruments=["Vocals"], file_path="C:\\Users\\justm\\Desktop\\Code\\New folder\\Black Dog (Remaster).wav")
#st.split_stems()
st.combine_outputs(["C:\\Users\\justm\\Desktop\\Code\\New folder\\htdemucs_stems\\htdemucs\\Black Dog (Remaster)\\no_vocals.wav", 
                    "C:\\Users\\justm\\Desktop\\Code\\New folder\\htdemucs_stems\\htdemucs_ft\\Black Dog (Remaster)\\no_vocals.wav",
                   "C:\\Users\\justm\\Desktop\\Code\\New folder\\htdemucs_stems\\mdx\\Black Dog (Remaster)\\no_vocals.wav",
                     "C:\\Users\\justm\\Desktop\\Code\\New folder\\htdemucs_stems\\mdx_extra\\Black Dog (Remaster)\\no_vocals.wav"], "C:\\Users\\justm\\Desktop\\Code\\New folder\\combined\\Black Dog (Remaster)_combined.wav")
        #self.finished.emit(target_dir)