from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
import os
import traceback
from pathlib import Path
from contextvars import ContextVar

import re
_ffmpeg_location = ContextVar('ffmpeg_location', default=None)

eval = None
_ffmpeg_location.set('ffmpeg')

ffmpeg_path = os.path.abspath('ffmpeg')
os.environ["PATH"] += os.pathsep + ffmpeg_path
#url = 'https://www.youtube.com/watch?v=x4SsfuOolkU'


def sanitize_folder_name(name: str) -> str:
    # Remove invalid characters for Windows paths
    return re.sub(r'[<>:"|?*]', '', name)
class DownloadThread(QThread):
  
    finished_signal = pyqtSignal(bool,  Path) 


    def __init__(self, url, save_path):
        super().__init__()
      
        self.out_path = Path()
        self.url = url
        self.save_path = save_path
        self.service = None
        self.downloaded_filename = ""
        self.ffmpeg_path = os.path.abspath('ffmpeg')
        os.environ["PATH"] += os.pathsep + self.ffmpeg_path

    def run(self):   
        
        ydl_opts = {
            'ffmpeg_location':fr'{self.ffmpeg_path}',
            'format': 'bestaudio/best[ext=webm]',
            'outtmpl': f"{self.save_path}\\tempfile.tmp",
            
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                
            }]
                }
        eval = None
        pth = None
        opth = None
        dl_path = Path()
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                #temp = ydl.evaluate_outtmpl(ydl_opts['outtmpl'])
                import shutil
                ydl.download([self.url])
                eval = ydl.extract_info(self.url)     
                dl_path = Path(rf"{self.save_path}\tempfile.tmp.wav")
                self.out_path = Path(dl_path).parent / Path(sanitize_folder_name(str(eval['title']))) / sanitize_folder_name(str(eval['title'] + '.wav'))
                Path(dl_path).with_stem(sanitize_folder_name(eval['title'])).absolute()
                if not self.out_path.exists():
                    if not self.out_path.parent.exists():
                        os.makedirs(self.out_path.parent)
                    shutil.move(str(dl_path),str(self.out_path) )
                else:
                    #
                    print('file already existed - ', dl_path.absolute())
                    Path(dl_path).unlink()

                print('self.out_path 77777777777777777 ' + str(self.out_path))
                self.finished_signal.emit(True,  self.out_path)
        except Exception as e:
            traceback.print_exc()               
            if not os.path.exists(self.out_path):
                stem_name = Path(self.out_path).stem
                real_location = self.out_path.parent / Path(stem_name)/Path(stem_name).with_suffix('.wav')
                if not Path(real_location.parent).exists():
                    os.makedirs(real_location.parent)
                if real_location.exists():
                    self.out_path.unlink()    
                else:
                    shutil.move(self.out_path,real_location)
            print(self.out_path, '---------------')
            self.finished_signal.emit(False, Path())



