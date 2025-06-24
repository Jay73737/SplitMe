# Relaunch script as administrator
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(`
    [Security.Principal.WindowsBuiltInRole] "Administrator"))
{
    Start-Process powershell "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    Write-Host "restarting powershell "
    exit
}



Import-Module BitsTransfer
# Bypass script execution policy for this session
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# === Parameters ===
$pythonVersion = "3.9.13"
$pythonTag = "python-$pythonVersion-amd64"

$installerUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-amd64.exe"

$pythonInstallerPath = "$env:TEMP\$pythonTag.exe"
$pythonInstallDir = "$env:LocalAppData\Programs\Python\Python310"

$ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$scriptDirectory = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
Write-Host $scriptDirectory
$ffmpegDirectory = Join-Path -Path $scriptDirectory -ChildPath "ffmpeg"

$cudaVersion = "12.1.0"
$cudaInstallerPath = "$env:TEMP\cuda_installer.exe"
$cudaDownloadUrl = "https://developer.download.nvidia.com/compute/cuda/12.1.0/local_installers/cuda_12.1.0_531.14_windows.exe"
$minCudaVersion = [version]"12.1.0"

# === Helper function to check if command exists ===
function Test-CommandExists {
    param([string]$cmd)
    return $null -ne  (Get-Command $cmd -ErrorAction SilentlyContinue)
}

# === Check and Install Python if needed ===
if (Test-Path "$pythonInstallDir\python.exe") {
    Write-Host "Python already installed at $pythonInstallDir"
} else {
    Write-Host "Downloading Python $pythonVersion..."

    Start-BitsTransfer -Source $installerUrl -Destination $pythonInstallerPath

    Write-Host "Installing Python $pythonVersion..."
    Start-Process -FilePath $pythonInstallerPath -ArgumentList @(
        "/quiet",
        "InstallAllUsers=0",
        "PrependPath=1",
        "Include_pip=1",
        "Include_launcher=1",
        "TargetDir=$pythonInstallDir"
    ) -Wait

    Remove-Item $pythonInstallerPath
}

$pythonExe = "$pythonInstallDir\python.exe"
$pipExe = "$pythonInstallDir\Scripts\pip.exe"

if (!(Test-Path $pythonExe)) {
    Write-Error "Python installation failed!"
    exit 1
}

Write-Host "✅ Python installed at $pythonInstallDir"



# === Check and Install FFmpeg if needed ===
if (Test-Path (Join-Path $ffmpegDirectory "ffmpeg.exe")) {
    Write-Host "FFmpeg already installed in $ffmpegDirectory"
} else {
    Write-Host "Downloading ffmpeg binaries..."
    if (!(Test-Path $ffmpegDirectory)) {
        New-Item -ItemType Directory -Path $ffmpegDirectory | Out-Null
    }

    $zipFilePath = Join-Path -Path $ffmpegDirectory -ChildPath "ffmpeg.zip"
    Write-Host $zipFilePath
    Start-BitsTransfer -Source $ffmpegUrl -Destination $zipFilePath


    Write-Host "Extracting ffmpeg binaries..."
    Expand-Archive -Path $zipFilePath -DestinationPath $ffmpegDirectory -Force


    # Move ffmpeg.exe and ffprobe.exe to top-level
    $extractedFolder = Get-ChildItem -Path $ffmpegDirectory -Directory | Select-Object -First 1
    $extractedPath = $extractedFolder.FullName

    $ffmpegExe = Join-Path -Path $extractedPath -ChildPath "ffmpeg.exe"
    $ffprobeExe = Join-Path -Path $extractedPath -ChildPath "ffprobe.exe"

    if (Test-Path $ffmpegExe) { Move-Item $ffmpegExe -Destination $ffmpegDirectory -Force }
    if (Test-Path $ffprobeExe) { Move-Item $ffprobeExe -Destination $ffmpegDirectory -Force }

    # Cleanup extracted folders/files except ffmpeg.exe and ffprobe.exe
    Get-ChildItem -Path $ffmpegDirectory | Where-Object { $_.Name -notmatch "^(ffmpeg\.exe|ffprobe\.exe)$" } | Remove-Item -Recurse -Force

    Write-Host "Cleaned up the ffmpeg folder, retaining only ffmpeg.exe and ffprobe.exe."
    

    # Add ffmpeg directory to user PATH if not already present
    $oldPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not ($oldPath -split ";" | Where-Object { $_ -eq $ffmpegDirectory })) {
        $newPath = "$oldPath;$ffmpegDirectory"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Host "Added ffmpeg to user PATH."
    }
}

# === Create Desktop Shortcut to launch your Python script ===
$shortcutPath = "$env:USERPROFILE\Desktop\SplitIt.lnk"
$scriptPath = Join-Path $scriptDirectory "main.py"

$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonExe
$shortcut.Arguments = "`"$scriptPath`""
$shortcut.WorkingDirectory = Split-Path $scriptPath
$shortcut.IconLocation = "$scriptPath\icon.ico,0"
$shortcut.Save()

Write-Host "Created desktop shortcut: $shortcutPath"



$scriptPath = $PSScriptRoot
$repoUrl = "https://github.com/Jay73737/SplitMe.git"
$targetPath = Join-Path -Path $scriptPath -ChildPath $repoName



git clone $repoUrl $targetPath
# Install pip packages from requirements.txt if it exists
$requirementsFile = Join-Path $targetPath "requirements.txt"
if (Test-Path $requirementsFile) {
    & $pipExe install -r $requirementsFile
    & $pipExe install torch  torchaudio --index-url https://download.pytorch.org/whl/cu121
    Write-Host "✅ Python packages installed."
} else {
    Write-Host "requirements.txt not found, skipping pip install."
}
git clone https://github.com/adefossez/demucs.git $targetPath

Pause

