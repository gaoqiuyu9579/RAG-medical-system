param(
    [ValidateSet('start', 'stop', 'status', 'logs')]
    [string]$Action = 'start',
    [switch]$Demo
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
# ASCII output keeps this entry point compatible with Windows PowerShell 5.1.
$composeArgs = @('compose')
$demoEnvironment = @{
    DOCKER_HTTP_PORT = '8081'
    DOCKER_SEED_DEMO_DATA = '1'
    DOCKER_ADMIN_USERNAME = 'admin'
    DOCKER_ADMIN_PASSWORD = 'Admin123456'
}
$previousEnvironment = @{}

Push-Location -LiteralPath $PSScriptRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker is not installed. Install and open Docker Desktop first.'
    }
    if (-not (Test-Path -LiteralPath '.env')) {
        Copy-Item -LiteralPath '.env.example' -Destination '.env'
        Write-Host 'Created .env from .env.example.'
    }
    if ($Demo) {
        $composeArgs += @('--project-name', 'smart-medical-demo')
        foreach ($key in $demoEnvironment.Keys) {
            $previousEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
            [Environment]::SetEnvironmentVariable($key, $demoEnvironment[$key], 'Process')
        }
    }
    $serverVersion = & docker info --format '{{.ServerVersion}}' 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'Open Docker Desktop and wait for the Linux engine to be ready, then retry.'
    }
    switch ($Action) {
        'start' { & docker @composeArgs up -d --build --wait --wait-timeout 240 }
        'stop' { & docker @composeArgs down }
        'status' { & docker @composeArgs ps -a }
        'logs' { & docker @composeArgs logs --tail=100 app }
    }
    if ($LASTEXITCODE -ne 0) { throw "Docker action failed: $Action" }
    if ($Action -eq 'start') {
        $binding = & docker @composeArgs port app 5000
        if ($LASTEXITCODE -ne 0) { throw 'Cannot find the published application port.' }
        $bindingText = ($binding | Select-Object -First 1).Trim()
        if ($bindingText -match ':(\d+)$') {
            Write-Host "Ready: http://localhost:$($Matches[1])" -ForegroundColor Green
        }
        if ($Demo) { Write-Host 'Demo login: admin / Admin123456 (synthetic data, separate volumes).' }
        Write-Host 'Stop with: .\start.ps1 stop (add -Demo for the demo deployment).'
    }
}
finally {
    foreach ($key in $previousEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($key, $previousEnvironment[$key], 'Process')
    }
    Pop-Location
}
