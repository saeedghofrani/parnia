# Start Parnia locally. Run .\start-studio.ps1 -Https for encrypted localhost.
param([switch]$Https)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$parniaPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $parniaPython)) {
    Write-Host 'First run: python -m venv .venv'
    Write-Host 'Then: .\.venv\Scripts\python.exe -m pip install -r requirements-web.txt'
    exit 1
}
if ($Https) {
    & $parniaPython server.py --https
} else {
    & $parniaPython server.py
}
exit $LASTEXITCODE
