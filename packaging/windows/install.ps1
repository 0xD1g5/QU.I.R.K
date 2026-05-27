#Requires -Version 5.1
<#
.SYNOPSIS
    Per-user installer for the QUIRK sensor agent.

.DESCRIPTION
    Installs the QUIRK sensor bundle under %LOCALAPPDATA%\Programs\QUIRK (no admin
    elevation required), enrolls the sensor against a QUIRK console using the provided
    enrollment token, tightens the written sensor config ACL to the current user, and
    registers a daily Windows Scheduled Task that runs 'quirk.exe sensor push' on cadence.

    The enrollment token is accepted as a parameter but is NEVER echoed to the console or
    written to any log file.  Only the persistent push credential (console_api_token)
    written inside the sensor config is retained on disk, and that file is ACL-restricted
    to the current user immediately after enroll.

.PARAMETER ConsoleUrl
    Base URL of the QUIRK console (e.g. https://quirk.example.com).

.PARAMETER EnrollmentToken
    Per-sensor opaque Bearer enrollment token provisioned by 'quirk console enroll'.
    This value is passed to 'quirk.exe sensor enroll --api-token' and is never echoed.

.PARAMETER Segment
    Network segment label written into the sensor config.  Defaults to "windows".

.PARAMETER Time
    Daily trigger time for the Scheduled Task in HH:MM format.  Defaults to "03:00".

.PARAMETER AllowInternalConsole
    When set, passes --allow-internal-console to sensor enroll so the sensor can reach
    a console on a private/RFC1918 network (on-prem/lab).

.EXAMPLE
    .\install.ps1 -ConsoleUrl https://quirk.example.com -EnrollmentToken <token>

.EXAMPLE
    .\install.ps1 -ConsoleUrl https://10.0.0.5 -EnrollmentToken <token> -AllowInternalConsole -Time 02:00
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ConsoleUrl,

    [Parameter(Mandatory = $true)]
    [string]$EnrollmentToken,

    [string]$Segment = "windows",

    [string]$Time = "03:00",

    [switch]$AllowInternalConsole
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Resolve install root and paths
# ---------------------------------------------------------------------------

$InstallDir  = Join-Path $env:LOCALAPPDATA "Programs\QUIRK"
$BundleDir   = Join-Path $InstallDir "quirk"       # quirk\quirk.exe + _internal\
$ExePath     = Join-Path $BundleDir "quirk.exe"
$ConfigDir   = Join-Path $InstallDir "config"
$ConfigPath  = Join-Path $ConfigDir "sensor.yaml"
$TaskName    = "QUIRK Sensor Push"

# ---------------------------------------------------------------------------
# Locate the bundled quirk\ directory relative to this script
#
# Expected zip layout (unpacked by the operator before running install.ps1):
#   <unpack-root>\
#     quirk\          <- onedir bundle (quirk.exe + _internal\)
#     install.ps1
#     uninstall.ps1
#     sensor.sample.yaml
#
# $PSScriptRoot resolves to the directory containing install.ps1.
# ---------------------------------------------------------------------------

$SourceBundle = Join-Path $PSScriptRoot "quirk"

if (-not (Test-Path $SourceBundle -PathType Container)) {
    Write-Error ("Bundle directory not found at '$SourceBundle'. " +
        "Unpack the full quirk-windows-*.zip before running install.ps1.")
    exit 1
}

if (-not (Test-Path (Join-Path $SourceBundle "quirk.exe") -PathType Leaf)) {
    Write-Error "quirk.exe not found inside '$SourceBundle'. The bundle may be corrupt."
    exit 1
}

# ---------------------------------------------------------------------------
# Create install directories
# ---------------------------------------------------------------------------

Write-Host "Installing QUIRK sensor to: $InstallDir"

if (-not (Test-Path $InstallDir -PathType Container)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

if (-not (Test-Path $ConfigDir -PathType Container)) {
    New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
}

# ---------------------------------------------------------------------------
# Copy the onedir bundle (quirk\ -> $InstallDir\quirk\)
# ---------------------------------------------------------------------------

Write-Host "Copying bundle from '$SourceBundle' -> '$BundleDir' ..."
if (Test-Path $BundleDir) {
    Remove-Item $BundleDir -Recurse -Force
}
Copy-Item -Path $SourceBundle -Destination $BundleDir -Recurse -Force

# ---------------------------------------------------------------------------
# Enroll the sensor
# Runs: quirk.exe sensor enroll <ConsoleUrl>
#           --segment <Segment>
#           --api-token <EnrollmentToken>
#           --config <ConfigPath>
#           [--allow-internal-console]
#
# T-118-CFG: $EnrollmentToken must never appear in Write-Host / Write-Output /
# any log stream.  It is passed only as a direct argument to the subprocess.
# ---------------------------------------------------------------------------

Write-Host "Enrolling sensor against $ConsoleUrl ..."

$EnrollArgs = @(
    "sensor", "enroll", $ConsoleUrl,
    "--segment", $Segment,
    "--api-token", $EnrollmentToken,
    "--config", $ConfigPath
)

if ($AllowInternalConsole) {
    $EnrollArgs += "--allow-internal-console"
}

& $ExePath @EnrollArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "Sensor enroll failed (exit $LASTEXITCODE). Check the console URL and token."
    exit 1
}

# ---------------------------------------------------------------------------
# Tighten ACL on the written sensor config (T-118-CFG)
# Remove inherited permissions; grant only current user Read+Write.
# ---------------------------------------------------------------------------

if (Test-Path $ConfigPath) {
    Write-Host "Tightening config ACL: $ConfigPath"
    icacls $ConfigPath /inheritance:r /grant:r "${env:USERNAME}:(R,W)" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "icacls tighten failed (exit $LASTEXITCODE) — sensor config may be readable by others."
    }
}

# ---------------------------------------------------------------------------
# Register the Scheduled Task
# Action : quirk.exe sensor push --config <ConfigPath>
# Trigger: daily at $Time
# Context: current user (RunLevel Limited — no admin elevation)
# ---------------------------------------------------------------------------

Write-Host "Registering Scheduled Task '$TaskName' (daily at $Time, current user) ..."

$Action = New-ScheduledTaskAction `
    -Execute $ExePath `
    -Argument "sensor push --config `"$ConfigPath`""

$Trigger = New-ScheduledTaskTrigger -Daily -At $Time

# Register-ScheduledTask defaults to the current-user security principal when no
# -Principal is provided and the shell is not elevated.  -RunLevel Limited ensures
# the task does NOT request admin elevation at runtime (per CONTEXT D-04).
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $Action `
    -Trigger  $Trigger `
    -RunLevel Limited `
    -Force | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Error "Register-ScheduledTask failed (exit $LASTEXITCODE)."
    exit 1
}

# ---------------------------------------------------------------------------
# Success summary — token deliberately omitted from output
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "=== QUIRK Sensor Install Complete ==="
Write-Host "  Install dir : $InstallDir"
Write-Host "  Executable  : $ExePath"
Write-Host "  Config      : $ConfigPath"
Write-Host "  Task name   : $TaskName"
Write-Host "  Cadence     : daily at $Time (current user, no admin required)"
Write-Host ""
Write-Host "Run 'Get-ScheduledTask -TaskName `"$TaskName`"' to confirm the task."
Write-Host "Run uninstall.ps1 to remove the task and installed files."
