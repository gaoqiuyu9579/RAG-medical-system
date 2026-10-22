param([string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$chapters = Get-Content -LiteralPath (Join-Path $ProjectRoot 'docs/video_storyboard.json') -Raw -Encoding utf8 | ConvertFrom-Json
$audioDirectory = Join-Path $ProjectRoot 'output/video/audio'
New-Item -ItemType Directory -Path $audioDirectory -Force | Out-Null
$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $voice.SelectVoice('Microsoft Huihui Desktop')
    $voice.Rate = 0
    foreach ($chapter in $chapters) {
        $audioPath = Join-Path $audioDirectory ($chapter.id + '.wav')
        $voice.SetOutputToWaveFile($audioPath)
        $voice.Speak($chapter.narration)
        $voice.SetOutputToNull()
        Write-Output ('Narration generated: ' + $chapter.id)
    }
} finally {
    $voice.Dispose()
}
