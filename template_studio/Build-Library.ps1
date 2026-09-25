param([string]$Revision = 'final-v4', [string]$TemplateId = '')
$ErrorActionPreference = 'Stop'
$runtimeRoot = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies'
$env:BID3_ARTIFACT_RUNTIME = Join-Path $runtimeRoot 'node\node_modules'
$env:BID3_ARTIFACT_PYTHON = Join-Path $runtimeRoot 'python\python.exe'
$env:BID3_PRESENTATION_SKILL = Join-Path $env:USERPROFILE '.codex\plugins\cache\openai-primary-runtime\presentations\26.909.12148\skills\presentations'
$env:BID3_TEMPLATE_REVISION = $Revision
& (Join-Path $runtimeRoot 'node\bin\node.exe') (Join-Path $PSScriptRoot 'build.mjs') $TemplateId
if ($LASTEXITCODE -ne 0) { throw 'PPTX library build failed.' }
