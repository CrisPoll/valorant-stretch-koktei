$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    py -3 -m venv .venv
}
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudo instalar PyInstaller.' }

& $python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name ValorantStretchKoktei `
    --version-file version_info.txt `
    --add-data 'assets\monitor_helper.ps1;assets' `
    --distpath dist --workpath build `
    src\main.py
if ($LASTEXITCODE -ne 0) { throw 'No se pudo compilar la aplicación.' }
Write-Host "Listo: $PSScriptRoot\dist\ValorantStretchKoktei.exe"
