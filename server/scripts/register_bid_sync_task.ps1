$serverPath = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $serverPath "venv\Scripts\python.exe"
$managePath = Join-Path $serverPath "manage.py"

if (-not (Test-Path $pythonPath)) {
    throw "가상환경을 찾을 수 없습니다: $pythonPath"
}

$taskCommand = "& '$pythonPath' '$managePath' sync_bids"

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -Command `"$taskCommand`"" `
    -WorkingDirectory $serverPath

$triggers = 8..18 | ForEach-Object {
    New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($_))
}

Register-ScheduledTask `
    -TaskName "Bid2-G2B-Sync" `
    -Action $action `
    -Trigger $triggers `
    -Description "나라장터 공고를 매일 08시부터 18시까지 매시간 수집합니다." `
    -Force

Write-Host "Bid2-G2B-Sync 예약 작업을 등록했습니다. (매일 08:00~18:00, 총 11회)"
