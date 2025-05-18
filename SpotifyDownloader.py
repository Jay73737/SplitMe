import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import configparser

config = configparser.ConfigParser()
config.read('config.ini')


client_id = config['spotify']['client_id']
client_secret = config['spotify']['client_secret']


auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)