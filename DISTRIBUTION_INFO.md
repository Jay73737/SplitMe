# 📦 SplitMe Distribution Information

## What This Package Contains

This is a **cleaned, end-user distribution** of SplitMe designed for easy use without development setup.

### ✅ Included Files

**Executables (Mac Only)**:
- `dist/SplitMe-Backend.app` - Mac backend application (34MB)
- `frontend/dist/mac-arm64/SplitMe - Stem Splitter.app` - Mac frontend GUI

**Launcher Scripts**:
- `SplitMe-Launcher.sh` - Mac launcher (ready to use)
- `SplitMe-Launcher-Windows.bat` - Windows info script (shows setup instructions)

**Configuration & Data**:
- `config/config.json` - Application settings
- `data/audio_cache/` - Temporary audio storage directory
- `assets/` - Application icons and UI elements

**Documentation**:
- `README.md` - Main user guide
- `WINDOWS_EASY_INSTALL.md` - Windows setup instructions
- `DISTRIBUTION_INFO.md` - This file

**Utilities**:
- `cleanup-dev-files.sh` - Optional cleanup script

### ❌ Removed Development Files

The following were removed to create this clean distribution:
- Source code: `src/`, `api/`, `frontend/src/`
- Python environment: `.venv/`, `requirements.txt`
- Build tools: `*.spec`, `build_app.py`, `package_app.*`
- Node.js files: `package.json`, `node_modules/`, `frontend/build/`
- Development docs: `Project_Structure.md`, setup scripts

## Platform Support

### ✅ Windows (Fully Supported - PowerShell)
- **Modern PowerShell launcher** with advanced error handling
- **One-click setup**: `SplitMe-Launcher-Windows.bat` → PowerShell launcher
- **Direct PowerShell**: `.\SplitMe-Launcher-Windows.ps1`
- **Advanced features**: Parameter support, health checks, job management
- **Automatic fallbacks**: API-only mode, dependency resolution
- **Real-time feedback**: Progress tracking, status updates

### ✅ Mac (Dual Mode)
- **Option 1**: Pre-built executables for instant use
- **Option 2**: Automatic source setup if executables missing
- Run `./SplitMe-Launcher.sh` - auto-detects best mode
- Compatible with macOS 10.14+

### ✅ Linux (Source Mode)
- **Auto-setup** with dependency management
- Run `./setup.sh` then `./SplitMe-Launcher.sh`
- Works on most modern Linux distributions

## File Sizes

- **Total Distribution**: ~200MB (mostly Mac executables)
- **Backend Executable**: ~34MB
- **Frontend App Bundle**: ~150MB+ (includes Electron framework)

## Getting Started

### Mac Users
```bash
# Navigate to the SplitMe folder
cd /path/to/SplitMe

# Launch the application
./SplitMe-Launcher.sh
```

### Windows Users
```cmd
# Run the info script for setup instructions
SplitMe-Launcher-Windows.bat
```

## Need the Full Source Version?

If you need:
- Windows executables
- Source code for customization
- Development environment
- Build tools

You'll need to download the complete source version of SplitMe that includes all development files and can be built for Windows.

## Support

This distribution is designed for end users who want to use SplitMe without development setup. For technical support or to report issues, refer to the project's main repository or documentation.

**Happy stem splitting! 🎵**