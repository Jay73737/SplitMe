from PyQt6.QtCore import QThread, pyqtSignal
from googleapiclient.discovery import build
import sys
from pathlib import Path
from pathlib import Path
import json
import os
import traceback
from GUIComponents import APIKeyWindow
from contextvars import ContextVar
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
_ffmpeg_location = ContextVar('ffmpeg_location', default=None)


_ffmpeg_location.set('ffmpeg')
_ffmpeg_location = ContextVar('ffmpeg_location', default=None)


_ffmpeg_location.set('ffmpeg')


class YoutubeDownloader(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal( str)
    def __init__(self, url, soundcloud=False):
        super().__init__()
        self.url = url
        
        file_path = Path(__file__).parent / 'config.json'
        with open(file_path, 'r') as f:
            parser = json.load(f)
            try:
                self.api_key = parser['user']['api_key']
            except:
                api_window = APIKeyWindow(self)
                api_window.finished.connect(self.return_api)
                api_window.exec()
            self.youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=self.api_key)
            
        
    def return_api(self, key):
        self.api_key = key

    def run(self):
        results = self.search_youtube()
        self.finished.emit(results)
    
    def search_youtube(self):
        response = self.youtube.search().list(q=self.url,part='id,snippet',maxResults=10).execute()
        results = []
        returns = []
        returns = []
        items = response['items']
        for item in items:
            try:
                
                if item['id']['kind'] == 'youtube#playlist':
                    
                    
                    url = f"https://www.youtube.com/playlist?list={item['id']['playlistId']}"
                elif item['id']['kind'] == 'youtube#video':
                    
                    video_id = item['id']['videoId']
                    url = f"https://www.youtube.com/watch?v={video_id}"    
                else:
                    continue

                title = item['snippet']['title']
                
                description = item['snippet']['description']
                results.append({'title': title, 'url': url, 'description': description, 'thumbnail': item['snippet']['thumbnails']['default']['url']})
                returns.append((self.url, results[-1]))

                returns.append((self.url, results[-1]))

            except KeyError:
                
                self.error.emit(traceback.format_exc() + f"\n\nError: {str(item)}")
        return returns
        return returns



