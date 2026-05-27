#Requires -Version 5.1
<#
.SYNOPSIS
    Uninstaller for the QUIRK sensor agent.

.DESCRIPTION
    Unregisters the "QUIRK Sensor Push" Scheduled Task and removes the installed
    files and directories under %LOCALAPPDATA%\Programs\QUIRK.

    When -KeepConfig is passed, only the binary bundle is removed; the sensor config
    directory ($InstallDir\config\) is preserved so a future reinstall can reuse the
    existing sensor identity without re-enrolling.

.PARAMETER KeepConfig
    When set, removes the onedir bundle but preserves the config directory
    ($InstallDir\config\) containing sensor.yaml.

.EXAMPLE
    .\uninstall.ps1

.EXAMPLE
    .\uninstall.ps1 -KeepConfig
#>

[CmdletBinding()]
param(
    [switch]$KeepConfig
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\QUIRK"
$BundleDir  = Join-Path $InstallDir "quirk"
$ConfigDir  = Join-Path $InstallDir "config"
$TaskName   = "QUIRK Sensor Push"

# ---------------------------------------------------------------------------
# Unregister the Scheduled Task (if it exists)
# ---------------------------------------------------------------------------

$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Unregistering Scheduled Task '$TaskName' ..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "  Task removed."
} else {
    Write-Host "Scheduled Task '$TaskName' not found — skipping."
}

# ---------------------------------------------------------------------------
# Remove installed files
# ---------------------------------------------------------------------------

if (-not (Test-Path $InstallDir -PathType Container)) {
    Write-Host "Install directory '$InstallDir' not found — nothing to remove."
    exit 0
}

if ($KeepConfig) {
    # Remove only the binary bundle; leave the config directory intact.
    Write-Host "Removing binary bundle: $BundleDir"
    if (Test-Path $BundleDir -PathType Container) {
        Remove-Item $BundleDir -Recurse -Force
        Write-Host "  Bundle removed."
    } else {
        Write-Host "  Bundle directory not found — skipping."
    }

    # Remove any loose files in $InstallDir that are not the config dir.
    Get-ChildItem -Path $InstallDir -Exclude "config" | ForEach-Object {
        Write-Host "  Removing: $($_.FullName)"
        Remove-Item $_.FullName -Recurse -Force
    }

    Write-Host "Config preserved at: $ConfigDir"
    Write-Host "Re-run without -KeepConfig to remove everything."
} else {
    # Full removal: remove the entire install directory tree.
    Write-Host "Removing install directory: $InstallDir"
    Remove-Item $InstallDir -Recurse -Force
    Write-Host "  Install directory removed."
}

Write-Host ""
Write-Host "=== QUIRK Sensor Uninstall Complete ==="
