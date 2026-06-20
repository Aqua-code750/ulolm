$ErrorActionPreference = "Stop"

$installDir = "$env:LOCALAPPDATA\UloLM"
$exePath = "$installDir\ulolm.exe"
$downloadUrl = "https://github.com/Aqua-code750/ulolm/releases/latest/download/ulolm.exe"

Write-Host "Installing UloLM..." -ForegroundColor Cyan

# 1. Create installation directory
if (-not (Test-Path -Path $installDir)) {
    Write-Host "Creating directory at $installDir..."
    New-Item -ItemType Directory -Path $installDir | Out-Null
}

# 2. Download the executable
Write-Host "Downloading latest UloLM release from GitHub..."
Invoke-WebRequest -Uri $downloadUrl -OutFile $exePath
Write-Host "Download complete." -ForegroundColor Green

# 3. Add to user's PATH environment variable
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$installDir*") {
    Write-Host "Adding UloLM to your system PATH..."
    
    # Remove trailing semicolon if exists, then append the new path
    if ($userPath.EndsWith(";")) {
        $newPath = "$userPath$installDir"
    } else {
        $newPath = "$userPath;$installDir"
    }
    
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
    
    # Update current session PATH so they can use it immediately
    $env:PATH = "$env:PATH;$installDir"
}

Write-Host ""
Write-Host "✅ UloLM has been installed successfully!" -ForegroundColor Green
Write-Host "You can now run 'ulolm' from anywhere in your terminal." -ForegroundColor Yellow
Write-Host "(Note: If the command isn't recognized right away, just close and reopen your terminal.)"
