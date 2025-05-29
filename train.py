import yaml
import os
from pydub import AudioSegment
import sys
import librosa
import soundfile as sf




import traceback
#from demucs.train import get_datasets 

#path = r'C:\Users\justm\Downloads\babyslakh_16k.tar\babyslakh_16k'
path = r'D:\slakh2100_flac_redux.tar\slakh2100_flac_redux\validation'
folders = os.listdir(path)
import os
os.environ["PATH"] += os.pathsep + os.path.abspath("ytdownloader/ffmpeg")
dataset_path = r'D:\dataset'
output_path = os.path.join(dataset_path, 'train')
sources = ["vocals", "drums", "bass", "guitar", "other"]
os.makedirs(output_path, exist_ok=True)
os.makedirs(dataset_path, exist_ok=True)
temp_dict = {}

def align_audio_length(folder_path):
    
# Force stems to match the length of the mixture
    y_mix, sr = librosa.load(os.path.join(folder_path, "mixture.wav"), sr=44100)
    expected_len = len(y_mix)

    for stem in ["vocals", "drums", "guitar", "bass", "other"]:
        y, _ = librosa.load(f"{stem}.wav", sr=44100)
        y = librosa.util.fix_length(y, expected_len)
        sf.write(f"{stem}.wav", y, sr)
        print(f"Aligned {os.path.join(folder_path,stem)} to {expected_len} samples.")


def generate_silent_audio(stem, duration, fpath):
    """
    Generate a silent audio file with the given duration.
    """
    silent_audio = AudioSegment.silent(duration=duration)
    dir_path = os.path.dirname(fpath)
    out_path = os.path.join(dir_path, f"{stem}.wav")
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    silent_audio.export(out_path, format='wav')
    return out_path

def get_duration(path):
    """
    Get the duration of an audio file in milliseconds.
    """
    audio = get_audio_segment(path)
    return len(audio)

def get_audio_segment(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.wav':
        return AudioSegment.from_wav(filepath)
    elif ext == '.flac':
        return AudioSegment.from_file(filepath, format='flac')
    else:
        raise ValueError(f"Unsupported file extension: {ext}")


def combine_audios(source, paths, output_location):
    if not paths:
        return None
    if source != 'vocals':
        try:
            if os.path.exists(paths[0]):
                combined = get_audio_segment(paths[0])

        except FileNotFoundError:
            traceback.print_exc()

            print(f"{source} File not found: {paths[0]}")
            return None
        if len(paths) == 1:
            out_path = os.path.join(output_path, output_location)
            if not os.path.exists(out_path):
                os.makedirs(out_path)
            out_path = os.path.join(out_path, f"{source}.wav")
            result = combined.export(out_path, format='wav')
            return out_path
        for p in paths[1:]:
            try:
                if os.path.exists(p):
                    combined.overlay(get_audio_segment(p))
                else:
                    print(f"File not found: {p}")
                    combined.overlay(get_audio_segment(p))
            except FileNotFoundError:
                traceback.print_exc()

                print(f"{source} File not found: {p}")
                continue
    
        out_path = os.path.join(output_path,output_location)
        if not os.path.exists(out_path):
            os.makedirs(out_path)
        out_path = os.path.join(out_path, f"{source}.wav")
        result = combined.export(out_path, format='wav')
        print(f'{out_path} is {str(get_duration(out_path))} miliseconds')

        return out_path

def prepare_dataset(path):
    for folder in folders:
        out_file_list = []
        folder_path = os.path.join(path, folder)
        if os.path.isdir(folder_path):
            files = os.listdir(folder_path)
            if 'validation' in folders:
                folders.remove('validation')
                continue
            
            for file in files:
                
                if file == 'metadata.yaml':
                    meta_path = os.path.join(folder_path, file)
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta = yaml.safe_load(f)
                    temp_dict = {}
                    for st in meta['stems'].keys():
                        name = st
                        source = meta['stems'][st]['inst_class'].lower()
                        if source not in sources:
                            source = 'other'
                        # Try both .wav and .flac
                        wav_path = os.path.join(folder_path, 'stems', st + '.wav')
                        flac_path = os.path.join(folder_path, 'stems', st + '.flac')
                        if os.path.exists(wav_path):
                            audio_path = wav_path
                        elif os.path.exists(flac_path):
                            audio_path = flac_path
                        else:
                            print(f"File not found for stem {st}: {wav_path} or {flac_path}")
                            continue
                        if temp_dict.get(source) is None:
                            temp_dict[source] = {'paths': [audio_path]}
                        else:
                            temp_dict[source]['paths'].append(audio_path)
                    for s in sources:
                        if temp_dict.get(s) is None:
                            continue
                        else:
                            if len(temp_dict[s]['paths']) > 0:
                                # Combine the audio files for this source
                                print(f"Combining {s} audio files...")
                                # Combine the audio files for this source
                                new_out = combine_audios(s, temp_dict[s]['paths'], folder)
                                out_file_list.append(new_out)
                                temp_dict[s]['paths'] = None
                                vocals = generate_silent_audio('vocals', get_duration(new_out), new_out)
                                out_file_list.append(vocals)
                                new_out = combine_audios('mixture', out_file_list, folder)
                                align_audio_length(folder_path)

                    break
prepare_dataset(output_path)
'''import torch
from demucs.htdemucs import HTDemucs

# 5-source model
sources = ["vocals", "drums", "bass", "guitar", "other"]
model = HTDemucs(sources=sources)

# Load pretrained state dict from 4-source htdemucs
state = torch.load("htdemucs_ft.pth")

# Remove head weights (they won't match)
for key in list(state["state"].keys()):
    if key.startswith("out"):
        del state["state"][key]

# Load remaining weights
model.load_state_dict(state["state"], strict=False)'''

