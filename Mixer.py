import soundfile as sf
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from StemSplitter import StemSplitterSingle

from pathlib import Path
class Mixer(QThread):

    '''Class used to perform --one-stem separation with demucs on each individual track.
        Idea: To run each stem through the --one-stem separation, then remove that stem from the overall mixture with soundfile,
              and repeat for each track in the mix (order the stems are removed could play a factor here). The idea is that maybe the stems
              could be read from the file more clearly with less interference.  If we combine + remove stem files from the mixture, it 
              is possible that the algorithms will pick up more of the desired instrument.  We can then keep remixing the stems, then
              rerunning the model for the same stem over the remaining mixture, and combining the outputs. Basically seeing if the model
              can pull any more data for that source.
               
        audio_input -> Demucs models --one-stem -> ('drums') + ('bass','vocals', 'other', 'guitar', 'piano') 
         vars: pass_per_source         pass 2   -> ('drums','drums pass 2') + ('bass','vocals','other','guitar', 'piano')  -> ('drums') + ('drums pass 2') + ... ('drums pass n < pass_per_source')
              (drums removed from mix) pass 3   -> (bass) + (vocals,other,guitar,piano) -> (bass) + (bass pass 2) + ... + (bass pass n)
                                        ...
                                    pass n-1     -> (guitar) + (other)
                                    pass n       -> (other) -> (run all of the tracks against other 1 last time and combine the results)
        input_dict = { 'source': Path(audio_source),
                        'model': model_name,
                        'instruments':{
                            'drums' : [drums_source_pass 1 file,
                                        drums_source_pass 2 file,
                                        ...
                                        drums_source_pass n file],
                            'mixture': [mixture source pass 1 file (minus drums),
                                        mixture source pass 2 file (minus drums p 1 + 2), ...],
                            'vocals': ...
                        }
                    }'''
    



    def __init__(self, input_dict, model, passes=2, sources={
                        'source': Path(),
                        'model': "",
                        'instruments':{
                            'drums' : [],
                            'mixture': [],
                            'vocals': [],
                            'guitar': [],
                            'other':[]
                        }                    
                                                                 }):
        super().__init__()
        self.input_dict = input_dict
        if 'instruments' not in self.input_dict:
            self.input_dict = sources
        self.model = model
        self.passes = passes
        self.instruments = input_dict['instruments'].keys()

    def run(self):
        original_source = sf.read(self.input_dict['source'])
        working_dict = {i: [] for i in self.instruments}
        ss = StemSplitterSingle(self.model, self.instruments, self.input_dict['source'])
        
        output_folder = ss.run()
        self.sources_split = output_folder.glob('*.wav')
        self.input_dict['instruments']['mixture'] = [original_source]
        for s in self.sources_split:
            tem = sf.read(s.absolute()).astype(np.float32)
            working_dict[s.stem] = [tem] 
            self.input_dict['instruments'][s.stem] = [tem]
        for i in self.sources_split[1:]:
            istem = str(Path(i).stem)
            if istem in self.instruments:
                working_dict[istem].append(sf.read(i.absolute()).astype(np.float32))
                working_dict['mixture'].append(sf.read(self.input_dict['source']).astype(np.float32))
                self.input_dict['instruments'][istem].append(working_dict[istem])
                sub_audio = working_dict['mixture'] - working_dict[istem]
                max_val = np.max(np.abs(sub_audio))
                if max_val > 1.0:
                    sub_audio /= max_val
                working_dict['mixture'].append( sub_audio)
                self.input_dict['instruments']['mixture'].append(sub_audio)


                

            
    def stem_pass(self,stem,  model, source,number_of_passes=2,pass_number=0):
        for n in number_of_passes - pass_number:
            t_ss = StemSplitterSingle(model, self.instruments, source)
            next_output = t_ss.run()
            

audio1, sr1 = sf.read(r'C:\Users\justm\Desktop\SplitIt\SplitMe\SplitMe\Eagles - Hotel California (Official Audio)\Eagles - Hotel California\guitar.wav')
audio2, sr2 = sf.read(r'C:\Users\justm\Desktop\SplitIt\other_average\guitar.wav')
other, sro = sf.read(r'C:\Users\justm\Desktop\SplitIt\SplitMe\SplitMe\Eagles - Hotel California (Official Audio)\Eagles - Hotel California\other.wav')
othermax_val = np.max(np.abs(other)) + .02
audio2 *= 2
other /= othermax_val
other -= audio2
average = (audio1 + audio2)/2.0
sf.write('otheravg.wav', other,sr1 )
sf.write('guitart2.wav', audio2, sr2)

