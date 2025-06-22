# Requires PowerShell 5.0+
# Run as Administrator

# Function to check if a program is available
function Test-CommandExists {
    param ($cmd)
    return Get-Command $cmd -ErrorAction SilentlyContinue
}

# Ensure script is running from its own directory
Set-Location -Path $PSScriptRoot

Write-Host "Checking for Python 3.10.11..."
$pythonInstalled = $false
if (Test-CommandExists python) {
    $version = python --version 2>&1
    if ($version -like "*3.10.11*") {
        $pythonInstalled = $true
    }
}

if (-not $pythonInstalled) {
    Write-Host "Installing Python 3.10.11..."
    winget install --exact --id Python.Python.3.10 --version 3.10.11 --silent --accept-package-agreements --accept-source-agreements
    $env:Path += ";$env:LocalAppData\Programs\Python\Python310\Scripts;$env:LocalAppData\Programs\Python\Python310"
}

# Refresh PATH for current session
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Check for ffmpeg
Write-Host "Checking for FFmpeg..."
$ffmpegInstalled = Test-CommandExists ffmpeg

if (-not $ffmpegInstalled) {
    Write-Host "Installing FFmpeg..."
    $ffmpegZip = "$env:TEMP\ffmpeg.zip"
    $ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    Invoke-WebRequest -Uri $ffmpegUrl -OutFile $ffmpegZip
    Expand-Archive -Path $ffmpegZip -DestinationPath "$env:ProgramFiles\ffmpeg" -Force
    $ffmpegBin = Get-ChildItem "$env:ProgramFiles\ffmpeg" -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1 | Split-Path
    [Environment]::SetEnvironmentVariable("Path", $env:Path + ";$ffmpegBin", [System.EnvironmentVariableTarget]::Machine)
    Write-Host "FFmpeg installed and added to PATH."
}


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

# Install Python requirements if file exists
$requirementsPath = Join-Path $PSScriptRoot "requirements.txt"
if (Test-Path $requirementsPath) {
    Write-Host "Installing Python dependencies from requirements.txt..."
    python -m pip install --upgrade pip
    pip install -r $requirementsPath
} else {
    Write-Host "No requirements.txt file found. Skipping pip install."
}

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
