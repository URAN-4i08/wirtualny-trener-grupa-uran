$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Brak .venv. Tworze lokalne srodowisko Python..."
    $systemPython = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"
    if (-not (Test-Path $systemPython)) {
        throw "Nie znaleziono Pythona 3.11. Zainstaluj Python 3.11 i uruchom ponownie."
    }
    & $systemPython -m venv (Join-Path $PSScriptRoot ".venv")
}

Write-Host "Instaluje/aktualizuje zaleznosci backendu..."
& $python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")

Write-Host "Uruchamiam backend: http://localhost:8000"
& $python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
