from demucs import wav
from moisesdb.dataset import MoisesDB
from pathlib import Path
import os
from pydub import AudioSegment
import shutil
from pydub.generators import Sine
from concurrent.futures import ThreadPoolExecutor, wait
import traceback

standard_folders = ['bass', 'drums', 'vocals', 'guitar', 'other']

# Parses the track number from the file name
def parse_track(file):
    pfile = Path(file)
    file_list = pfile.parts
    return file_list[-3]

# this checks if the stem has the .wav extension and checks if it is in the sources.  It will return false if a weird file is fed into it.
def is_same_stem_no_ext(stem1, return_string = False):
    global standard_folders
    p =Path(stem1).suffix
    if p is not None:
        temp = stem1[:-4]
    else:
        temp = stem1
    if return_string:
        return temp 
    return temp in standard_folders

def combine_stem_files(root_dir, stems=standard_folders, output_name='mixture.wav'):
    """Combine all audio files in each stem folder into one file per stem."""

    stem_path = Path(root_dir) 
    
    audio_files = sorted([f for f in stem_path.iterdir() if f.suffix == '.wav'])
    if not audio_files:
        return
    combined = None
    for audio_file in audio_files:
        try:
            seg = AudioSegment.from_file(audio_file)
            if combined is None:
                combined = seg
            else:
                combined = combined.overlay(seg)
        except Exception as e:
            print(f"Error reading {audio_file}: {e}")
    if combined:
        out_file = stem_path / output_name
        combined.export(out_file, format='wav')
        print(f"Combined {len(audio_files)} files in {stem_path} into {out_file}")


def get_all_files(root_dir):
    """Return a list of all file paths under root_dir (recursively)."""
    all_files = {}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            all_files[filename] = {'file': os.path.join(dirpath, filename), 'dirnames': dirnames}
    return all_files

file_dict = {}

data_path=Path(r'C:\Users\justm\Desktop\dataset\moisesdb\moisesdb\moisesdb_v0.1')
output_path=Path(r'c:\Users\justm\Desktop\dataset\proper')
t = get_all_files(data_path)
last_dir_name = 'moisesdb_v0.1'
final_dict = {}

directory = Path(data_path)


def combine_audios(directory: Path, mixture=False):
    
    for item in directory.iterdir():
        dir_list = []
        if item.is_file():
            print(f"File: {item.name}")
        elif item.is_dir():
            for it in item.iterdir():
                if it.name in standard_folders:
                    itparts = it.parts
                    ind = itparts.index(last_dir_name)
                    
                    p = output_path
                    for ip in itparts[ind+1:]:
                        p = p / ip
                    
                    
                    if mixture:
                        final_out = p.parent / Path("mixture.wav")
                    else:
                        final_out = p 
                    combine_stem_files( it, final_out)


def replace_out(input_tuple):
    input = data_path / Path(input_tuple[0]) / Path(input_tuple[1])
    files = os.listdir(input)
    for f in files:
        try:
            if input_tuple[1] in f:
                final_in = input / Path(f)
                
                if Path(f).suffix == '.wav':
                    final_out = Path(output_path) / Path(input_tuple[0]) / f
                    
                else:
                    stem = input_tuple[0] + '.wav'
                    os.rename(final_in, Path(stem))   
                    final_out = Path(output_path)  / Path(input_tuple[0]) / Path(stem)
                shutil.move(final_in, final_out) 
        except:
            pass

def build_dir_tuples(root):
    directory = [d for d in Path(root).rglob('*') if d.is_dir()]
    for dir in directory:
        sub_dir = [d for d in Path(dir).rglob('*') if d.is_dir()]
        for s in sub_dir:
            files = os.listdir(s)
            if len(files) == 0:
                continue
            stem = s.parts[-1]
            for f in files:
                try:
                    if stem in f:
                        if '.wav' in f:
                            input_path = Path(s) / Path(f)
                            outp_path = Path(output_path) / Path(stem) / f
                            shutil.move(input_path, outp_path)
                            print('moved ',input_path, ' to ', outp_path)
                        else:
                            input_path = Path(s) / Path(f)
                            
                            renamed = input_path.name + '.wav'
                            outp_path = Path(output_path) / Path(stem) / Path(renamed)
                            os.rename(input_path,renamed)
                            print('renamed ', input_path)
                            input_path = Path(s) / Path(renamed)
                            shutil.move(input_path, outp_path)
                            print('rn move')
                except:
                    pass

def find_track_stems(root):
    base_num = len(Path(root).parts)
    rm_list = []
    for d in Path(root).rglob('*'):
        parts = d.parts
        if d.is_file():
            levels = len(parts)
            if levels - base_num > 2:
                if d.suffix == '.wav':
                    name = d.name[:-4]
                    if name != d.parts[-2]:
                        final = d.parts[-2] + '.wav'
                        try:
                            os.rename(d, final)
                        except:
                            print('found file, deleting weird one ', d)
                            os.remove(d)
                    else:
                        move_loc = d.parent.parent
                        shutil.move(d, move_loc)
        else:
            levels = len(d.parts)
            if levels - base_num > 1:
                files = os.listdir(d)
                if len(files) == 0:
                    print('removing dir ', d)
                    rm_list.append(d)

    return rm_list


def find_empty_dirs(root):
    empty_dirs = []
    for d in Path(root).rglob('*'):
        if d.is_dir() and not any(d.iterdir()):
            empty_dirs.append(d.parts[-2:])
    return empty_dirs
rm = find_track_stems(output_path)
[os.rmdir(r) for r in rm]
with ThreadPoolExecutor(max_workers=16) as execute:
    for d in Path(output_path).rglob('*'):
        execute.submit(combine_stem_files,d)
combine_audios(data_path)



#@forrename_directories_sequentially(data_path)  stems dir_paths, dir_names, files f.sos.walk(data_path)path = print(dir_names,dir_paths, files)taset\train",['vocals', 'guitar', 'bass', 'drums', 'other'],normalize=True, ext='.wav')
valid = wav.build_metadata(r"d:\dataset\dataset\valid",['vocals', 'guitar', 'bass', 'drums', 'other'], ext='.wav')
