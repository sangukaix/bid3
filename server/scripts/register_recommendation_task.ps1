$serverPath = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $serverPath "venv\Scripts\python.exe"
$managePath = Join-Path $serverPath "manage.py"

if (-not (Test-Path $pythonPath)) {
    throw "가상환경을 찾을 수 없습니다: $pythonPath"
}

$taskCommand = "& '$pythonPath' '$managePath' match_recommendations"
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -Command `"$taskCommand`"" `
    -WorkingDirectory $serverPath
$trigger = New-ScheduledTaskTrigger -Daily -At "18:10"

Register-ScheduledTask `
    -TaskName "Bid2-Recommendation-Match" `
    -Action $action `
    -Trigger $trigger `
    -Description "회사 조건과 나라장터 공고를 매일 한 번 비교합니다." `
    -Force

Write-Host "Bid2-Recommendation-Match 예약 작업을 등록했습니다. (매일 18:10)"
