param(
    [string]$OutputDirectory = '.local/product-demo/narration'
)
$ErrorActionPreference = 'Stop'
$bidDemoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$bidDemoStory = Get-Content -LiteralPath (Join-Path $bidDemoRoot 'web/features/product-demo/storyboard.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$bidDemoOutput = [IO.Path]::GetFullPath((Join-Path $bidDemoRoot $OutputDirectory))
New-Item -ItemType Directory -Force -Path $bidDemoOutput | Out-Null
Add-Type -AssemblyName System.Speech
$bidDemoSpeaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $bidDemoVoice = $bidDemoSpeaker.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'ko-KR' -and $_.Enabled } | Select-Object -First 1
    if (-not $bidDemoVoice) { throw 'Windows 한국어 음성이 필요합니다. 한국어 음성을 설치하거나 --silent 옵션으로 자막 영상을 제작하세요.' }
    $bidDemoSpeaker.SelectVoice($bidDemoVoice.VoiceInfo.Name)
    $bidDemoSpeaker.Rate = 2
    foreach ($bidDemoScene in $bidDemoStory.scenes) {
        $bidDemoWav = Join-Path $bidDemoOutput ($bidDemoScene.id + '.wav')
        $bidDemoSpeaker.SetOutputToWaveFile($bidDemoWav)
        $bidDemoSpeaker.Speak($bidDemoScene.narration)
        $bidDemoSpeaker.SetOutputToNull()
        Write-Output ('Narration: ' + $bidDemoScene.id)
    }
} finally { $bidDemoSpeaker.Dispose() }
