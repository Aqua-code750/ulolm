# Install required packages
pip install -r requirements.txt

# Run PyInstaller
Write-Host "Building UloLM Executable..."
pyinstaller --name ulolm --onefile --console --clean main.py

Write-Host "Build Complete! Executable is located in the dist/ folder."
