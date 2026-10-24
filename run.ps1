# Start SayBetter AI (Kili) at http://localhost:8000
# The virtual environment lives in a short path because Windows' 260-character
# path limit breaks pip inside deeply nested folders.
$venv = "$env:LOCALAPPDATA\SayBetter\venv"

function Find-Python {
    foreach ($v in "3.12", "3.13") {
        try {
            $exe = & py "-$v" -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
        } catch { }
    }
    $known = "$env:LOCALAPPDATA\Python\pythoncore-3.12-64\python.exe"
    if (Test-Path $known) { return $known }
    return $null
}

if (-not (Test-Path "$venv\Scripts\python.exe")) {
    $python = Find-Python
    if (-not $python) {
        try { py install 3.12 } catch { }
        $python = Find-Python
    }
    if (-not $python) {
        Write-Host "Python 3.12 is needed. Install it from https://www.python.org/downloads/ (tick 'Add python.exe to PATH'), then run this again." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "First run: setting up Python environment in $venv (downloads about 1.5 GB, 5-15 minutes)..." -ForegroundColor Cyan
    & $python -m venv $venv
    & "$venv\Scripts\python.exe" -m pip install --upgrade pip
    & "$venv\Scripts\python.exe" -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    & "$venv\Scripts\python.exe" -m pip install -r "$PSScriptRoot\backend\requirements.txt"
}
if (-not (Test-Path "$PSScriptRoot\backend\.env")) {
    Copy-Item "$PSScriptRoot\backend\.env.example" "$PSScriptRoot\backend\.env"
    Write-Host "Created backend\.env - add your Sarvam key there for full accuracy (the app still runs without it)." -ForegroundColor Yellow
}
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
# Open the browser as soon as the server answers.
Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile', '-Command',
    'for ($i = 0; $i -lt 600; $i++) { try { Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing -TimeoutSec 2 | Out-Null; Start-Process http://localhost:8000; break } catch { Start-Sleep 1 } }'
Write-Host "Starting SayBetter AI at http://localhost:8000 (close this window to stop it)" -ForegroundColor Cyan
Set-Location "$PSScriptRoot\backend"
& "$venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
