# 🎵 SplitMe - AI Audio Stem Separation

**Transform any song into separate instrument tracks instantly!**

SplitMe uses advanced AI (Facebook's Demucs) to split songs into individual tracks like vocals, drums, bass, and other instruments. Perfect for remixers, producers, musicians, and music enthusiasts.

## ✨ Features

- **AI-Powered Separation**: Split songs into vocals, drums, bass, piano, guitar, and more
- **Multiple AI Models**: Choose from different Demucs models for best results
- **YouTube Integration**: Download and process audio from YouTube and other sites
- **Batch Processing**: Process multiple songs at once
- **High Quality Output**: Maintains audio quality during separation
- **Cross-Platform**: Works on Windows, Mac, and Linux

## 🚀 Quick Start

### 🪟 For Windows Users

**Super Easy - One Click Setup:**

1. **Double-click**: `SplitMe-Launcher-Windows.bat`
2. **That's it!** The modern PowerShell launcher will automatically:
   - Check system requirements and Python installation
   - Create and manage Python virtual environments
   - Install all dependencies with progress tracking
   - Handle Node.js detection for GUI vs API-only mode
   - Start both backend and frontend with proper error handling
   - Provide real-time status updates and health checks

**Advanced Options:**
- **PowerShell directly**: `.\SplitMe-Launcher-Windows.ps1`
- **API-only mode**: `.\SplitMe-Launcher-Windows.ps1 -ApiOnly`
- **Verbose output**: `.\SplitMe-Launcher-Windows.ps1 -Verbose`
- **System check**: `setup.bat` or `.\setup-windows.ps1`

**First time setup** may take a few minutes to download dependencies.

### 🍎 For Mac Users

**Two options available:**

**Option 1: Pre-built Executables (Fastest)**
```bash
# Just run the launcher - uses optimized Mac binaries
./SplitMe-Launcher.sh
```

**Option 2: From Source (Auto-setup)**
If executables aren't available, the launcher automatically falls back to source mode and will:
- Set up Python environment
- Install dependencies  
- Start from source code

### 🐧 For Linux Users

```bash
# Make setup script executable and run
chmod +x setup.sh
./setup.sh

# Then launch the application
./SplitMe-Launcher.sh
```

## 📋 Requirements

**The launchers handle everything automatically, but if you want to install manually:**

**Essential:**
- Python 3.9+ 
- pip (comes with Python)

**For GUI (optional):**
- Node.js 16+ (for the Electron frontend)

**Without Node.js**, SplitMe runs in API-only mode with a web interface at `http://localhost:8000`

## 🎯 How to Use

1. **Launch the Application**: Use the launcher scripts above
2. **Add Audio Sources**:
   - Drag and drop audio files
   - Paste YouTube URLs
   - Use the YouTube search feature
3. **Choose AI Model**: Select the separation model that works best for your music
4. **Start Separation**: Click process and wait for the AI to work its magic
5. **Download Results**: Get your separated tracks organized in folders

## 📁 What You Get

After processing, you'll receive separate audio files for:

- 🎤 **Vocals** - Clean vocal track
- 🥁 **Drums** - Drum track only  
- 🎸 **Bass** - Bass line isolated
- 🎹 **Other** - Remaining instruments (piano, guitar, etc.)

## ⚙️ Configuration

- **Config File**: `config/config.json` - Stores app settings
- **Audio Cache**: `data/audio_cache/` - Temporary storage for downloads
- **Output**: Separated tracks saved to your chosen output directory

## 🤖 YouTube API (Optional)

For YouTube search functionality, you'll need a Google YouTube Data API v3 key:

1. Go to [Google Cloud Console](https://console.developers.google.com/)
2. Enable YouTube Data API v3
3. Create an API key
4. Enter the key when prompted in the app

**Note**: You can still download from YouTube URLs without an API key - the search feature just won't work.

## 🛠️ Troubleshooting

### Windows Issues

**"Python not found"**:
- Install Python from [python.org](https://www.python.org/downloads/)
- Make sure to check "Add Python to PATH" during installation
- Restart Command Prompt after installation

**"Permission denied" or antivirus warnings**:
- Run Command Prompt as Administrator
- Add SplitMe folder to antivirus exclusions
- Some antivirus software flags Python installations

### Mac Issues

**"Cannot be opened" security warning**:
- Right-click the launcher script → Open
- Or run: `xattr -d com.apple.quarantine SplitMe-Launcher.sh`

**Permission denied**:
- Make script executable: `chmod +x SplitMe-Launcher.sh`

### General Issues

**App Won't Start**:
- Check that Python 3.9+ is installed
- Ensure internet connection for first-time dependency download
- Try running setup scripts first

**Poor Separation Quality**:
- Use higher quality input audio (320kbps or lossless)
- Try different AI models for different music types
- Some heavily mixed songs are harder to separate

**YouTube Downloads Fail**:
- Check your internet connection
- Some videos may be restricted or private
- Try a different URL or video

## 📋 System Requirements

- **Windows**: Windows 10+ 
- **Mac**: macOS 10.14+
- **Linux**: Most modern distributions
- **RAM**: 4GB minimum, 8GB+ recommended for larger files
- **Storage**: 2GB free space for models and temporary files
- **Internet**: Required for initial setup, YouTube downloads, and AI model downloads

## 📦 What's Included

This distribution includes:

✅ **Complete Source Code**: All Python and JavaScript source files
✅ **Cross-Platform Launchers**: Auto-setup scripts for Windows, Mac, and Linux  
✅ **Mac Executables**: Pre-built optimized binaries for Mac users
✅ **Auto-Setup**: Automatic virtual environment and dependency management
✅ **Fallback Modes**: API-only mode if GUI dependencies aren't available

## 🔧 Advanced Usage

### Backend Binary (PyInstaller)

```bash
# Install build dependencies (first run)
pip install pyinstaller

# Build the backend bundle (outputs to dist/backend/)
python scripts/build_backend.py --clean
```

### API-Only Mode

```bash
# Just the backend API server
python main.py

# Or directly:
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000
```

### 📦 Packaging Desktop Releases

We now ship a scripted workflow to produce installers with the bundled Python backend and Electron UI.

1. **Install build tooling** (once per machine):
   ```bash
   pip install pyinstaller
   npm install --prefix frontend
   ```

2. **Build everything in one go** from the project root:
   ```bash
   python scripts/package_app.py --platform mac
   # use --platform win or linux when building on those OSes
   ```

   The script will:
   - package the FastAPI backend with PyInstaller into `dist/backend/SplitMeBackend`
   - run `npm run dist(:platform)` to create installers with Electron Builder
   - write distributables to `release/`

3. **Backend only** (optional):
   ```bash
   python scripts/build_backend.py --clean
   ```

4. **Frontend only** (optional):
   ```bash
   npm run dist:mac   # or dist:win / dist:linux
   ```

> ℹ️  Build artifacts live in `dist/backend/` and the Electron outputs land in `release/`. These folders are ignored in git by default.

## 🎉 Ready to Split Some Stems?

**Windows users**: Double-click `SplitMe-Launcher-Windows.bat`  
**Mac users**: Run `./SplitMe-Launcher.sh`  
**Linux users**: Run `./setup.sh` then `./SplitMe-Launcher.sh`

Turn any song into a karaoke version, extract that perfect drum loop, or isolate vocals for remixing!

**Happy stem splitting! 🎵**
