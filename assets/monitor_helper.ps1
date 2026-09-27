param(
    [Parameter(Mandatory = $true)][ValidateSet('Disable', 'Restore')][string]$Action,
    [Parameter(Mandatory = $true)][string]$InstanceId,
    [int]$ParentPid = 0,
    [string]$SignalPath,
    [string]$StatusPath
)

$ErrorActionPreference = 'Stop'
$disabledByThisRun = $false

function Write-Status([string]$message) {
    if ($StatusPath) {
        Set-Content -LiteralPath $StatusPath -Value $message -Encoding ascii
    }
}

try {
    if ($Action -eq 'Restore') {
        Enable-PnpDevice -InstanceId $InstanceId -Confirm:$false
        Write-Status 'restored'
        exit 0
    }

    if (-not $ParentPid -or -not $SignalPath -or -not $StatusPath) {
        throw 'Faltan los parámetros de seguimiento.'
    }
    $monitor = Get-PnpDevice -Class Monitor | Where-Object { $_.InstanceId -eq $InstanceId }
    if ($null -eq $monitor -or $monitor.Status -ne 'OK') {
        throw 'El monitor seleccionado no está activo.'
    }

    Disable-PnpDevice -InstanceId $InstanceId -Confirm:$false
    $disabledByThisRun = $true
    Write-Status 'disabled'

    while ((Test-Path -LiteralPath $SignalPath) -and
           (Get-Process -Id $ParentPid -ErrorAction SilentlyContinue)) {
        Start-Sleep -Seconds 2
    }
}
catch {
    Write-Status ('error: ' + $_.Exception.Message)
    exit 1
}
finally {
    if ($disabledByThisRun) {
        for ($attempt = 0; $attempt -lt 3; $attempt++) {
            try {
                Enable-PnpDevice -InstanceId $InstanceId -Confirm:$false
                Write-Status 'restored'
                break
            }
            catch {
                Start-Sleep -Seconds 2
            }
        }
    }
}
