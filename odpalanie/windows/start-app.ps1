$ProjectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $ProjectRoot

Write-Host "=== Cyber Trener — uruchamianie backendu i frontendu ==="
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Frontend: http://localhost:5173"
Write-Host ""

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Py311 = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"
    if (-not (Test-Path $Py311)) {
        Write-Error "Nie znaleziono Python 3.11."
        exit 1
    }
    & $Py311 -m venv (Join-Path $ProjectRoot ".venv")
}

Write-Host "[1/2] Backend..."
& $Python -m pip install -q -r (Join-Path $ProjectRoot "requirements.txt")
$backend = Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -PassThru -NoNewWindow
Start-Sleep -Seconds 2

Write-Host "[2/2] Frontend..."
Set-Location (Join-Path $ProjectRoot "frontend")
npm install --silent
try {
    npm run dev
} finally {
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    }
}
