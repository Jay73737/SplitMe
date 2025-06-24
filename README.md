# SplitMe

SplitMe is a Python tool for separating audio stems (vocals, drums, bass, guitar, piano, other) from media files using [Demucs](https://github.com/facebookresearch/demucs). It can also automatically download audio and videos using [yt_dlp](https://github.com/yt-dlp/yt-dlp) from various [web pages](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md), extract the audio, and perform stem separation.  

## Features

- Audio stem separation using Demucs (supports multiple models)
- Download videos/audio from URLs
- Search for videos on youtube through the api for download.
- Automatically converts and prepares audio files for separation
- Outputs cleanly separated stems into organized folders

## Requirements

######################################################## Beta Feature ######################################################################
Most of the requirements should be installed by the powershell install script included in the Repo. There are 2 separate powershell scripts in there (.ps1 files).  If you have an nVidia GPU with CUDA cores (2000 series +) and want to utilize them for stem separation, use the download_gpu.ps1 file.  Otherwise, use the download_nogpu.ps1 file.  

These scripts will download and install:
   - python 3.9.13
   - ffmpeg
   - Git
   - CUDA toolkit
######################################################### Beta Feature #####################################################################

## Installation

The above script is still in development.  To install this library you will need:
   - [python 3.9.13](https://www.python.org/downloads/release/python-3913/)
   - [ffmpeg](https://ffmpeg.org/download.html) 
   - [Git](https://git-scm.com/downloads)
   - [CUDA toolkit 12.1](https://developer.nvidia.com/cuda-12-1-0-download-archive)

Install python and add python to the global PATH variable.

Then you can go ahead and install Git and the CUDA toolkit normally.

Next would be getting ffmpeg downloaded.  Open the .zip file you download from ffmpeg and navigate to the bin directory inside and extract "ffmpeg.exe" and "ffprobe.exe" to a folder somewhere on your pc.  Copy the folder path, and add this to the system environment PATH variables and save it.

You may need to restart your PC after installing all of this.

The next step is cloning this repo onto your pc.  This can be done with the following command:
```powershell
git clone https://github.com/Jay73737/SplitMe.git
```
After this, you will need to install the requirements.txt file by changing your current directory to the SplitMe root folder (the only containing main.py and requirements.txt).  This can be done with:
```powershell
pip install -r requirements.txt
pip uninstall torch torchaudio yt_dlp soundfile demucs
pip install torch torchaudio yt_dlp soundfile demucs
```

You may want to run this in a venv in order to have a clean python environment to work with:
```powershell
python -m venv SplitMe
```



If you want to use the Youtube API to gather the links for downloading (if not you can just paste urls into the search box), follow these steps first:

   1. Activate your Youtube Data API key in Google by navigating [here](https://console.developers.google.com/) then clicking on the Library tab:![alt text](image.png).

   2. Activate the Youtube Data API v3: ![alt text](image-1.png)

   3. Go to Enabled APIs & services and click Create credentials, then API key:![alt text](image-3.png)

   4. Then click Show key and copy the API key value.

   5. You will be asked for this the first time you start the program.





3. Run main.py

```powershell
python main.py
```


## Credits

- Developed by Justin Hild
- Thanks to [Demucs](https://github.com/adefossez/demucs/tree/main) for creating the audio models and inspiring me to continue working on getting better quality data out.
- Thanks also to [yt_dlp]([https://github.com/username/projec](https://github.com/yt-dlp/yt-dlp)t) for making pulling in sources to test on much easier.
