$ErrorActionPreference = "Stop"
$installDir = "$env:LOCALAPPDATA\UloLM"
$exePath = "$installDir\ulolm.exe"
$downloadUrl = "https://github.com/Aqua-code750/ulolm/releases/download/v3.0.0/ulolm.exe"

Write-Host "Installing UloLM..." -ForegroundColor Cyan

# Create directory
if (-not (Test-Path -Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir | Out-Null
}

# Download the executable with retries
Write-Host "Downloading UloLM (v3.0.0) from GitHub..." -ForegroundColor Yellow

$retries = 5
$success = $false
$attempt = 1

while (-not $success -and $attempt -le $retries) {
    try {
        Write-Host "Download attempt $attempt of $retries..."
        Invoke-WebRequest -Uri $downloadUrl -OutFile $exePath -TimeoutSec 45
        $success = $true
    }
    catch {
        Write-Warning "Attempt $attempt failed: $_"
        if ($attempt -lt $retries) {
            $waitSec = [Math]::Pow(2, $attempt)
            Write-Host "Waiting $waitSec seconds before retrying..." -ForegroundColor Gray
            Start-Sleep -Seconds $waitSec
        }
        $attempt++
    }
}

if (-not $success) {
    Write-Error "Failed to download UloLM after $retries attempts."
    exit 1
}

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
