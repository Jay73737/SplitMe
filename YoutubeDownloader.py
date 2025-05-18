from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot
from googleapiclient.discovery import build
import os
import json

YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
class YoutubeDownloader(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(dict)
    def __init__(self, url, soundcloud=False):
        super().__init__()
        self.url = url
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'config.json')
        with open(file_path, 'r') as f:
            parser = json.load(f)
            api_key = parser['api_key']
            
            self.youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key)
            del api_key
        

    def run(self):
        results = self.search_youtube()
        self.finished.emit(results)
    
    def search_youtube(self):
        response = self.youtube.search().list(q=self.url,part='id,snippet',maxResults=10).execute()
        results = []
        items = response['items']
        for item in items:
            try:
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                url = f"https://www.youtube.com/watch?v={video_id}"
                description = item['snippet']['description']
                results.append({'title': title, 'url': url, 'description': description, 'thumbnail': item['snippet']['thumbnails']['default']['url']})
            except KeyError:
                self.error.emit(item)
        return results
           


