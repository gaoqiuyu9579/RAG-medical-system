[CmdletBinding(SupportsShouldProcess)]
param([switch]$Apply)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$projectPrefix = $projectRoot + [IO.Path]::DirectorySeparatorChar
$relativeTargets = @(
    'tmp', '.ruff_cache', 'backend/.venv', 'backend/.idea',
    'frontend/test-results', 'frontend/playwright-report', 'frontend/e2e-run.log',
    'output/video/audio', 'output/video/raw', 'output/video/segments'
)
$targets = @($relativeTargets | ForEach-Object { Join-Path $projectRoot $_ })
$artifacts = Join-Path $projectRoot '.test-artifacts'
if (Test-Path -LiteralPath $artifacts) {
    $targets += @(Get-ChildItem -LiteralPath $artifacts -Force |
        Where-Object { $_.Name -notlike 'docker-sync-*' } |
        ForEach-Object FullName)
}
foreach ($folder in @('backend', 'deploy', 'scripts', 'tests')) {
    $targets += @(Get-ChildItem -LiteralPath (Join-Path $projectRoot $folder) -Directory -Recurse -Force |
        Where-Object { $_.Name -eq '__pycache__' -and -not $_.FullName.Contains('\.venv\') } |
        ForEach-Object FullName)
}

Add-Type -AssemblyName Microsoft.VisualBasic
$results = @()
foreach ($candidate in ($targets | Sort-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $candidate)) { continue }
    $resolved = (Resolve-Path -LiteralPath $candidate).Path
    if (-not $resolved.StartsWith($projectPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing cleanup outside project: $resolved"
    }
    $item = Get-Item -LiteralPath $resolved -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Refusing cleanup of a reparse point: $resolved"
    }
    $relative = $resolved.Substring($projectPrefix.Length)
    if (Test-Path -LiteralPath (Join-Path $projectRoot '.git')) {
        $tracked = & git -C $projectRoot ls-files -- $relative
        if ($LASTEXITCODE -ne 0 -or $tracked) { throw "Refusing cleanup of tracked files: $relative" }
    }
    $files = @(if ($item.PSIsContainer) { Get-ChildItem -LiteralPath $resolved -Recurse -File -Force } else { $item })
    $bytes = ($files | Measure-Object Length -Sum).Sum
    $record = [pscustomobject]@{ path = $relative; files = $files.Count; bytes = $bytes; recycled = $false }
    if ($Apply -and $PSCmdlet.ShouldProcess($resolved, 'Move generated files to the Windows Recycle Bin')) {
        if ($item.PSIsContainer) {
            [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory(
                $resolved, [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,
                [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin,
                [Microsoft.VisualBasic.FileIO.UICancelOption]::ThrowException)
        }
        else {
            [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(
                $resolved, [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,
                [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin,
                [Microsoft.VisualBasic.FileIO.UICancelOption]::ThrowException)
        }
        $record.recycled = $true
    }
    $results += $record
}
if ($Apply -and (Test-Path -LiteralPath $artifacts) -and @(Get-ChildItem -LiteralPath $artifacts -Force).Count -eq 0) {
    $resolvedArtifacts = (Resolve-Path -LiteralPath $artifacts).Path
    if (-not $resolvedArtifacts.StartsWith($projectPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Refusing an unexpected artifact directory.'
    }
    if ($PSCmdlet.ShouldProcess($resolvedArtifacts, 'Recycle empty artifact directory')) {
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory(
            $resolvedArtifacts, [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,
            [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin)
    }
}
$report = Join-Path $projectRoot ('docs/verification/' + (Get-Date -Format 'yyyy-MM-dd') + '/cleanup.json')
if ($Apply) {
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($report)) -Force | Out-Null
    $previous = @(if (Test-Path -LiteralPath $report) { Get-Content -LiteralPath $report -Raw | ConvertFrom-Json })
    @($previous + $results) | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $report -Encoding utf8
}
[pscustomobject]@{
    mode = $(if ($Apply) { 'recycle' } else { 'preview; use -Apply to recycle' })
    targets = $results.Count
    files = ($results | Measure-Object files -Sum).Sum
    projectMB = [math]::Round(($results | Measure-Object bytes -Sum).Sum / 1MB, 2)
} | ConvertTo-Json -Compress
