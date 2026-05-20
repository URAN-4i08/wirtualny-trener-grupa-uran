$ErrorActionPreference = "Stop"

$frontend = Join-Path $PSScriptRoot "frontend"

Write-Host "Instaluje/aktualizuje zaleznosci frontendu..."
Push-Location $frontend
try {
    npm ci
    Write-Host "Uruchamiam frontend: http://localhost:5173"
    npm run dev
}
finally {
    Pop-Location
}
