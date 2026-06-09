$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$frontend = Join-Path $ProjectRoot "frontend"

Write-Host "Instaluje/aktualizuje zaleznosci frontendu..."
Push-Location $frontend
try {
    npm install
    Write-Host "Uruchamiam frontend: http://localhost:5173"
    npm run dev
}
finally {
    Pop-Location
}
