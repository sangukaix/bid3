param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("api", "web")]
    [string]$Service,
    [string]$Address = "127.0.0.1"
)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$parsedAddress = $null
if (-not [System.Net.IPAddress]::TryParse($Address, [ref]$parsedAddress) -or
    $parsedAddress.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork -or
    $Address -eq "0.0.0.0") {
    throw "Use the laptop's IPv4 address, for example 192.168.50.92, or 127.0.0.1."
}
$bindAddress = if ([System.Net.IPAddress]::IsLoopback($parsedAddress)) { "127.0.0.1" } else { "0.0.0.0" }
$port = if ($Service -eq "api") { 8000 } else { 3000 }
$listening = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
if ($listening.Count -gt 0) {
    throw "Port $port is already in use. Stop the existing BID3 service first."
}
$names = @("DJANGO_ALLOWED_HOSTS", "DJANGO_CORS_ALLOWED_ORIGINS", "NEXT_PUBLIC_API_MODE", "BID_API_BASE_URL")
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, "Process") }
Push-Location $projectRoot
try {
    if ($Service -eq "api") {
        $python = Join-Path $projectRoot "server\venv\Scripts\python.exe"
        if (-not (Test-Path -LiteralPath $python)) { throw "Python environment missing. Follow README setup first." }
        $env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,$Address"
        $env:DJANGO_CORS_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000,http://${Address}:3000"
        Write-Host "BID3 API: http://${Address}:8000  (Ctrl+C to stop)"
        & $python "server\manage.py" runserver "${bindAddress}:8000" --noreload
        if ($LASTEXITCODE -ne 0) { throw "API process exited with code $LASTEXITCODE." }
    } else {
        Set-Location (Join-Path $projectRoot "web")
        if (-not (Test-Path "node_modules\next")) { throw "Run npm.cmd ci in web first." }
        $env:NEXT_PUBLIC_API_MODE = "proxy"
        $env:BID_API_BASE_URL = "http://127.0.0.1:8000"
        Write-Host "Building BID3 with same-origin API proxy ..."
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw "Web build failed. Server was not started." }
        Write-Host "BID3 web: http://${Address}:3000  (Ctrl+C to stop)"
        & npm.cmd run start -- --hostname $bindAddress --port 3000
        if ($LASTEXITCODE -ne 0) { throw "Web process exited with code $LASTEXITCODE." }
    }
} finally {
    Pop-Location
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $previous[$name], "Process") }
}
