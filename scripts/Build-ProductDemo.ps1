param(
    [string]$Python = '',
    [switch]$Preview,
    [switch]$Silent
)
$ErrorActionPreference = 'Stop'
$bidDemoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $Python) { $Python = Join-Path $bidDemoRoot 'server/venv/Scripts/python.exe' }
Push-Location $bidDemoRoot
try {
    if ($Preview) {
        & $Python scripts/product-demo/render.py --preview
        if ($LASTEXITCODE -ne 0) { throw 'Demo preview failed.' }
    } else {
        if (-not $Silent) {
            & powershell -NoProfile -File scripts/product-demo/narrate.ps1
            if ($LASTEXITCODE -ne 0) { throw 'Demo narration failed.' }
        }
        $bidDemoArguments = @('scripts/product-demo/render.py')
        if ($Silent) { $bidDemoArguments += '--silent' }
        & $Python @bidDemoArguments
        if ($LASTEXITCODE -ne 0) { throw 'Demo rendering failed.' }
        & $Python scripts/product-demo/check.py
        if ($LASTEXITCODE -ne 0) { throw 'Demo verification failed.' }
    }
} finally { Pop-Location }
