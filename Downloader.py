from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
import os
import sys
if getattr(sys, 'frozen', False):
    # we are running in a bundle
    frozen = 'ever so'
    bundle_dir = sys._MEIPASS
else:
    # we are running in a normal Python environment
    bundle_dir = os.path.dirname(os.path.abspath(__file__))




class DownloadThread(QThread):
    progress_signal = pyqtSignal(int) 
    finished_signal = pyqtSignal(bool, str, str) 


    def __init__(self, url, format_selected, quality_selected, save_path):
        super().__init__()
        self.quality_selected = quality_selected
        self.format_selected = format_selected
        self.url = url
        self.save_path = save_path
        self.service = None  
        self.downloaded_filename = ""
        self.ffmpeg_path = os.path.join(bundle_dir,'ffmpeg')
        os.environ["PATH"] += os.pathsep + self.ffmpeg_path

    def run(self):
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 1) or d.get('total_bytes_estimate', 1)
                progress_percent = int((downloaded / total) * 100)
                self.progress_signal.emit(progress_percent)
                self.downloaded_filename = d['filename']
            elif d['status'] == 'finished':
                self.progress_signal.emit(100)
                self.downloaded_filename = d['filename']

        quality_map = {"Low (64kbps)": "64", "Medium (128kbps)": "128", "High (192kbps)": "192"}
        bitrate = quality_map.get(self.quality_selected, "192")
        ffmpeg_dir = self.ffmpeg_path
        
        ydl_opts = {
            'ffmpeg_location': f'{ffmpeg_dir}',
            'format': 'bestaudio/best' if self.format_selected in ["mp3", "wav", "m4a", "aac", "flac", "opus"]
                    else f'bestvideo[ext={self.format_selected}]+bestaudio/best[ext={self.format_selected}]',
            'outtmpl': f"{self.save_path}\\%(title)s.%(ext)s",
            'progress_hooks': [progress_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.format_selected,
                'preferredquality': bitrate,
            }] if self.format_selected in ["mp3", "wav", "m4a", "aac", "flac", "opus"] else []
        }
    
    
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.downloaded_filename = self.downloaded_filename.replace(".webm", "." + self.format_selected)
            self.finished_signal.emit(True, "Download completed!", self.downloaded_filename)
        except Exception as e:
            self.finished_signal.emit(False, f"Download failed: {str(e)}", "")

    #def search_services(self, search):
