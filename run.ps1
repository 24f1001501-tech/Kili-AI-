# Start SayBetter AI at http://localhost:8000
# The virtual environment lives in a short path because Windows' 260-character
# path limit breaks pip inside deeply nested folders.
$venv = "$env:LOCALAPPDATA\SayBetter\venv"
if (-not (Test-Path "$venv\Scripts\python.exe")) {
    Write-Host "Creating Python 3.12 environment in $venv ..."
    py install 3.12
    & "$env:LOCALAPPDATA\Python\pythoncore-3.12-64\python.exe" -m venv $venv
    & "$venv\Scripts\python.exe" -m pip install --upgrade pip
    & "$venv\Scripts\python.exe" -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    & "$venv\Scripts\python.exe" -m pip install -r "$PSScriptRoot\backend\requirements.txt"
}
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
Set-Location "$PSScriptRoot\backend"
& "$venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
