from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
import os
import traceback
from pathlib import Path
from contextvars import ContextVar
import os


_ffmpeg_location = ContextVar('ffmpeg_location', default=None)


_ffmpeg_location.set('ffmpeg')

ffmpeg_path = os.path.abspath('ffmpeg')
os.environ["PATH"] += os.pathsep + ffmpeg_path

temp_file = "temp_audio.webm"


class DownloadThread(QThread):
  
    finished_signal = pyqtSignal(bool,  Path) 


    def __init__(self, url, save_path):
        super().__init__()
      
        
        self.url = url
        self.save_path = save_path
        self.service = None
        self.downloaded_filename = ""
        self.ffmpeg_path = os.path.abspath('ffmpeg')
        os.environ["PATH"] += os.pathsep + self.ffmpeg_path

    def run(self):  

        
        
        
        ydl_opts = {
            
            'format': 'bestaudio[ext=webm]',
            'outtmpl': f"{self.save_path}\\%(title)s.%(ext)s",
            'quiet':True,           
        }
    
        eval = None
        pth = None
        opth = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                out = ydl.download([self.url])
                eval = ydl.extract_info(self.url)
                
                
                
                pth = Path(self.save_path)/Path(eval['title'] ).with_suffix('.webm')
                opth = Path(pth).with_suffix('.wav')
                print('pth---------',pth.absolute())
                print('opth------------------',opth.absolute())
                
                
                self.finished_signal.emit(True,  opth)

        except Exception as e:
                traceback.print_exc()
                self.finished_signal.emit(False, Path())

