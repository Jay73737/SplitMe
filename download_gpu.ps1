
param(
  [switch] $Restarted
)
function Restart-Script {
    param(
      [string[]] $RemainingArgs
    )

    # Choose host exe    
    $exe = if (Get-Command pwsh -ErrorAction SilentlyContinue) { 'pwsh' } else { 'powershell.exe' }

    # Build argument list
    $baseArgs = @(
      '-NoExit';
      '-ExecutionPolicy'; 'Bypass';
      '-File'; "`"$PSCommandPath`"";
      
    )

    # Add the -Restarted flag and any other args
    $allArgs = $baseArgs + $RemainingArgs + '-Restarted'

    Write-Host "🔄 Restarting in fresh session..." -ForegroundColor Cyan
    Start-Process -FilePath $exe -ArgumentList $allArgs
    exit
}


Import-Module BitsTransfer
# Bypass script execution policy for this session
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# === Parameters ===
$pythonVersion = "3.9.13"


$installerUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-amd64.exe"
Get-Command pwsh, powershell.exe -ErrorAction SilentlyContinue | Select Name, Source


$pythonInstallDir = "$env:LocalAppData\Programs\Python\Python39"
$pythonInstallerPath = "$env:TEMP\$pythonTag.exe"
$ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$scriptDirectory = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
Write-Host $scriptDirectory
$ffmpegDirectory = Join-Path -Path $scriptDirectory -ChildPath "ffmpeg"

$cudaVersion = "12.1.0"
$cudaInstallerPath = "$env:TEMP\cuda_installer.exe"
$cudaDownloadUrl = "https://developer.download.nvidia.com/compute/cuda/12.1.0/local_installers/cuda_12.1.0_531.14_windows.exe"
$minCudaVersion = [version]"12.1.0"
function Test-CommandExists {
    param([string]$cmd)
    return $null -ne  (Get-Command $cmd -ErrorAction SilentlyContinue)
}
if (-not $Restarted) {
# === Check and Install Python if needed ===
    if (Test-Path "$pythonInstallDir\python.exe") {
        Write-Host "Python already installed at $pythonInstallDir"
    } else {
        Write-Host "Downloading Python $pythonVersion...`n pythonInstallerPath=$pythonInstallerPath`n cudaInstallerPath=$cudaInstallerPath`n ffmpegDirectory=$ffmpegDirectory`n scriptDirectory=$scriptDirectory"

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
        Restart-Script -RemainingArgs @() 
        
    }
}else{


Write-Host "✅ Continued execution after restart!"



$pythonExe = "$pythonInstallDir\python.exe"
Write-Host $pythonExe
$pipExe = "$pythonInstallDir\Scripts\pip.exe"

if (-not (Test-CommandExists 'python')) {
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


if (Test-CommandExists "nvcc") {
    try {
    $nvccOutput = nvcc --version
    $versionLine = $nvccOutput | Select-String "release"
    $installedVersionStr = ($versionLine -split "V")[-1].Trim()

    
        $installedVersion = [version]$installedVersionStr
    } catch {
        Write-Warning "Failed to parse CUDA version from '$installedVersionStr'"
        $installedVersion = [version]"0.0.0"
    }

    if ($installedVersion -eq $minCudaVersion) {
        Write-Host "✅ CUDA version $installedVersion is OK (== $minCudaVersion)"
    } else {
        Write-Host "❌ CUDA version $installedVersion is too old (< $minCudaVersion), installing CUDA $cudaVersion"
        winget uninstall --id NVIDIA.CUDA --exact
        # Download and install CUDA Toolkit
        Start-BitsTransfer -Source $cudaDownloadUrl -Destination $cudaInstallerPath 
        
        Start-Process -FilePath $cudaInstallerPath -ArgumentList "-s", "-loglevel=error" -Wait
        
        Write-Host "✅ CUDA Toolkit $cudaVersion removed."

        # Add CUDA bin folder to PATH
        $cudaBin = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v$cudaVersion\bin"
        $oldPath = [Environment]::GetEnvironmentVariable("Path", "User")
        if (-not ($oldPath -split ";" | Where-Object { $_ -eq $cudaBin })) {
            $newPath = "$oldPath;$cudaBin"
            [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
            Write-Host "Added CUDA bin directory to user PATH."
        }
        $cudaBin = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v$cudaVersion\bin"
    $oldPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not ($oldPath -split ";" | Where-Object { $_ -eq $cudaBin })) {
        $newPath = "$oldPath;$cudaBin"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Host "Added CUDA bin directory to user PATH."
    }
    
    }
    Write-Host "nvcc not found. Installing CUDA Toolkit $cudaVersion..."
    Start-BitsTransfer -Source $cudaDownloadUrl -Destination $cudaInstallerPath
    Start-Process -FilePath $cudaInstallerPath -ArgumentList "-s", "-loglevel=error" -Wait
    
    Write-Host "✅ CUDA Toolkit $cudaVersion installed."
} else {
    Write-Host "nvcc not found. Installing CUDA Toolkit $cudaVersion..."
    Start-BitsTransfer -Source $cudaDownloadUrl -Destination $cudaInstallerPath 
    Start-Process -FilePath $cudaInstallerPath -ArgumentList "-s", "-loglevel=error" -Wait
    
    Write-Host "✅ CUDA Toolkit $cudaVersion installed."

    $cudaBin = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v$cudaVersion\bin"
    $oldPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not ($oldPath -split ";" | Where-Object { $_ -eq $cudaBin })) {
        $newPath = "$oldPath;$cudaBin"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Host "Added CUDA bin directory to user PATH."
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

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Warning "Git not found. Attempting to install with winget..."

    winget install --id Git.Git -e --source winget --silent --accept-package-agreements --accept-source-agreements


   
    Start-Sleep -Seconds 5

    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Host "Git successfully installed."
    } else {
        Write-Error "Git installation failed."
        exit 1
    }
} else {
    Write-Host "Git is already installed."
}

# Check for Git
Write-Host "Checking for Git..."
if (-not (Test-CommandExists git)) {
    Write-Host "Installing Git..."
    winget install --id Git.Git --silent --accept-package-agreements --accept-source-agreements
} else {
    Write-Host "Git is already installed."
}



# Clone Git repos
Write-Host "Cloning Git repositories..."
$repos = @(
    "https://github.com/Jay73737/SplitMe.git"
    
)

foreach ($repo in $repos) {
    $repoName = ($repo -split "/")[-1] -replace ".git", ""
    $targetPath = Join-Path $PSScriptRoot $repoName

    if (-not (Test-Path $targetPath)) {
        git clone $repo $targetPath
    } else {
        Write-Host "$repoName already exists. Skipping clone."
    }
}

$scriptPath = $PSScriptRoot
$repoUrl = "https://github.com/Jay73737/SplitMe.git"
$targetPath = Join-Path -Path $scriptPath -ChildPath $repoName



git clone $repoUrl $targetPath
# Install pip packages from requirements.txt if it exists
$requirementsFile = Join-Path $targetPath "requirements.txt"
if (Test-Path $requirementsFile) {
    & $pipExe install -r $requirementsFile
    & $pipExe install torch==2.6.0  torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu118
    Write-Host "✅ Python packages installed."
} else {
    Write-Host "requirements.txt not found, skipping pip install."
}
git clone https://github.com/adefossez/demucs.git $targetPath

Pause


pip uninstall torch torchaudio
pip install torch==2.1.0  torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

# Create shortcut to run main.py
Write-Host "Creating Python shortcut for main.py..."
$WScriptShell = New-Object -ComObject WScript.Shell
$shortcutPath = "$PSScriptRoot\RunMain.lnk"
$pythonPath = (Get-Command python).Source
$mainPy = Join-Path $PSScriptRoot "\SplitMe\main.py"
$shortcut = $WScriptShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonPath
$shortcut.Arguments = "`"$mainPy`""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.WindowStyle = 1
$shortcut.Save()
Write-Host "`nSetup complete!"
}