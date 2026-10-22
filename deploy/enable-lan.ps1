param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8080,
    [string]$InterfaceAlias = 'WLAN'
)

$ErrorActionPreference = 'Stop'
$ruleName = "SmartMedical-LAN-$Port"

try {
    if (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue) {
        Set-NetFirewallRule -Name $ruleName -Enabled True -Direction Inbound `
            -Action Allow -Protocol TCP -LocalPort $Port -Profile Any `
            -RemoteAddress LocalSubnet -InterfaceAlias $InterfaceAlias
    } else {
        New-NetFirewallRule -Name $ruleName -DisplayName "SmartMedical LAN $Port" `
            -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port `
            -Profile Any -RemoteAddress LocalSubnet -InterfaceAlias $InterfaceAlias | Out-Null
    }
    Write-Output "Enabled LAN access on $InterfaceAlias port $Port"
    exit 0
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}
