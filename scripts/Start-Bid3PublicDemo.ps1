param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("api", "web", "build", "info", "tunnel")]
    [string]$Service
)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$privateDir = Join-Path $projectRoot ".local\public-demo"
$configPath = Join-Path $privateDir "access.json"
$guidePath = Join-Path $privateDir "선생님_접속안내.txt"
$tunnelLog = Join-Path $privateDir "quick-tunnel.log"
if (-not (Test-Path -LiteralPath $configPath)) {
    function New-DemoSecret {
        $bytes = New-Object byte[] 32
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
        return [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
    }
    New-Item -ItemType Directory -Path $privateDir -Force | Out-Null
    $sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $privateDir /inheritance:r /grant:r "*${sid}:(OI)(CI)F" "*S-1-5-18:(OI)(CI)F" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Could not protect the private demo configuration folder." }
    [ordered]@{
        origin = "https://pending.trycloudflare.com"
        transport = "cloudflare"
        password = (New-DemoSecret)
        signing_key = (New-DemoSecret)
        django_secret_key = (New-DemoSecret)
    } | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
}
$demo = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Service -eq "tunnel") {
    $cloudflared = Get-Command cloudflared.exe -ErrorAction Stop
    $demo | Add-Member -MemberType NoteProperty -Name transport -Value "cloudflare" -Force
    $demo | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
    "" | Set-Content -LiteralPath $tunnelLog -Encoding UTF8
    & $cloudflared.Source tunnel --no-autoupdate --protocol http2 --url http://127.0.0.1:3002 --logfile $tunnelLog
    if ($LASTEXITCODE -ne 0) { throw "Public demo tunnel exited with code $LASTEXITCODE." }
    return
}
if ($demo.transport -eq "cloudflare") {
    if (-not (Test-Path -LiteralPath $tunnelLog)) { throw "Start -Service tunnel first and wait for its HTTPS URL." }
    $tunnelUrls = [regex]::Matches((Get-Content -LiteralPath $tunnelLog -Raw -Encoding UTF8), 'https://[a-z0-9-]+\.trycloudflare\.com')
    if ($tunnelUrls.Count -eq 0) { throw "Wait for the tunnel HTTPS URL, then start the API and web." }
    $demo.origin = $tunnelUrls[$tunnelUrls.Count - 1].Value
    $demo | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
}
if ($demo.password.Length -lt 24 -or $demo.signing_key.Length -lt 32 -or $demo.django_secret_key.Length -lt 32 -or
    $demo.origin -notmatch '^https://([a-z0-9.-]+\.ts\.net:8443|[a-z0-9-]+\.trycloudflare\.com)$') { throw "Invalid private demo configuration." }
@"
AI비드 선생님용 접속 안내

웹 주소: $($demo.origin)/mainPage
초대 암호: $($demo.password)

1. 웹 주소를 열고 위 초대 암호를 입력합니다. Tailscale 설치는 필요 없습니다.
2. BID3 계정으로 로그인합니다. 새 계정은 회원가입으로 만들 수 있습니다.
3. 각 계정의 회사 자료와 제안서는 별도로 관리됩니다. 기존 사용자의 문서는 다른 계정에서 보이지 않습니다.
4. 개인 노트북의 공개용 웹/API, Ollama와 공유 터널이 실행 중이어야 합니다.
5. 초대 접속은 8시간 후 만료됩니다. 초대 암호는 초대한 분에게만 별도로 전달하세요.
6. Cloudflare 임시 연결을 다시 시작하면 주소가 바뀝니다. 최신 안내 파일을 전달하세요.

이 파일은 초대 암호를 포함합니다. Git이나 공개 포트폴리오에 넣지 마세요.
"@ | Set-Content -LiteralPath $guidePath -Encoding UTF8
if ($Service -eq "info") {
    Write-Host "Public demo URL: $($demo.origin)/mainPage"
    Write-Host "Private invitation guide: $guidePath"
    return
}
$port = if ($Service -eq "api") { 8002 } else { 3002 }
if ($Service -ne "build" -and @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue).Count -gt 0) {
    throw "Port $port is already in use. Check its owner; do not stop unrelated services."
}
$names = @("DJANGO_DEBUG", "DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS", "DJANGO_CORS_ALLOWED_ORIGINS",
    "NEXT_PUBLIC_API_MODE", "BID_API_BASE_URL", "BID3_DIST_DIR", "BID3_PUBLIC_DEMO", "BID3_DEMO_PASSWORD", "BID3_DEMO_SIGNING_KEY", "BID3_DEMO_ORIGIN")
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, "Process") }
Push-Location $projectRoot
try {
    if ($Service -eq "api") {
        $env:DJANGO_DEBUG = "false"
        $env:DJANGO_SECRET_KEY = $demo.django_secret_key
        $publicHost = ([Uri]$demo.origin).Host
        $env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,$publicHost"
        $env:DJANGO_CORS_ALLOWED_ORIGINS = $demo.origin
        Set-Location (Join-Path $projectRoot "server")
        & .\venv\Scripts\python.exe -m waitress --listen=127.0.0.1:8002 --threads=6 --max-request-body-size=50331648 --channel-timeout=900 config.wsgi:application
    } else {
        $env:NEXT_PUBLIC_API_MODE = "proxy"
        $env:BID_API_BASE_URL = "http://127.0.0.1:8002"
        $env:BID3_DIST_DIR = ".next-public-demo"
        $env:BID3_PUBLIC_DEMO = "1"
        $env:BID3_DEMO_PASSWORD = $demo.password
        $env:BID3_DEMO_SIGNING_KEY = $demo.signing_key
        $env:BID3_DEMO_ORIGIN = $demo.origin
        Set-Location (Join-Path $projectRoot "web")
        if ($Service -eq "build") { & npm.cmd run build }
        else {
            if (-not (Test-Path ".next-public-demo\BUILD_ID")) { throw "Build the demo first with -Service build." }
            & npm.cmd run start -- --hostname 127.0.0.1 --port 3002
        }
    }
    if ($LASTEXITCODE -ne 0) { throw "Public demo $Service exited with code $LASTEXITCODE." }
} finally {
    Pop-Location
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $previous[$name], "Process") }
}
