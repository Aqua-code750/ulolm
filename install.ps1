$ErrorActionPreference = "Stop"
$installDir = "$env:LOCALAPPDATA\UloLM"
$exePath = "$installDir\ulolm.exe"
$downloadUrl = "https://github.com/Aqua-code750/ulolm/releases/download/v1.0.0/ulolm.exe"

Write-Host "Installing UloLM..." -ForegroundColor Cyan

# Create directory
if (-not (Test-Path -Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir | Out-Null
}

# Download the executable
Write-Host "Downloading UloLM (v1.0.0) from GitHub..."
Invoke-WebRequest -Uri $downloadUrl -OutFile $exePath

# Update PATH
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notmatch [regex]::Escape($installDir)) {
    Write-Host "Adding UloLM to your system PATH..."
    [Environment]::SetEnvironmentVariable("PATH", "$userPath;$installDir", "User")
    # Update current session so they don't have to restart terminal
    $env:PATH = "$env:PATH;$installDir"
}

Write-Host "UloLM installed successfully! 🚀" -ForegroundColor Green
Write-Host "You can now run 'ulolm' from any terminal!" -ForegroundColor Yellow
