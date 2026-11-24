<#
.SYNOPSIS
  Compact Docker Desktop's WSL 2 virtual disk so Windows gets freed space back.

.DESCRIPTION
  Run AFTER cleaning up inside Docker (docker system df shows little data) and
  AFTER trimming the disk while Docker is running:

    wsl -d docker-desktop -- fstrim -v /mnt/docker-desktop-disk

  (check the mount path first with: wsl -d docker-desktop -- df -h)

  Then quit Docker Desktop and run this script from an ADMIN PowerShell.
  It runs 'wsl --shutdown', compacts the disk with Optimize-VHD (Hyper-V module,
  Windows Pro and up) or diskpart (any edition), and prints the size before/after.

.PARAMETER VhdPath
  Path to the virtual disk. The default is where Docker Desktop 4.x keeps its data
  disk; older versions used a different folder, so check if the default is missing.

.EXAMPLE
  .\scripts\shrink-docker-vhdx.ps1
.EXAMPLE
  .\scripts\shrink-docker-vhdx.ps1 -VhdPath 'E:\Docker\wsl\disk\docker_data.vhdx'
#>
[CmdletBinding()]
param(
    [string]$VhdPath = (Join-Path $env:LOCALAPPDATA 'Docker\wsl\disk\docker_data.vhdx')
)

$ErrorActionPreference = 'Stop'

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this from an administrator PowerShell.'
}

if (-not (Test-Path -LiteralPath $VhdPath)) {
    throw "Virtual disk not found: $VhdPath. Pass -VhdPath with the right location."
}

if (Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue) {
    throw 'Docker Desktop is still running. Quit it first (tray icon > Quit).'
}

Write-Output 'Shutting down WSL...'
wsl --shutdown

$before = (Get-Item -LiteralPath $VhdPath).Length
Write-Output ('Before: {0:N1} GB  {1}' -f ($before / 1GB), $VhdPath)

if (Get-Command Optimize-VHD -ErrorAction SilentlyContinue) {
    Write-Output 'Compacting with Optimize-VHD -Mode Full...'
    Optimize-VHD -Path $VhdPath -Mode Full
}
else {
    Write-Output 'Optimize-VHD not available; compacting with diskpart...'
    $script = Join-Path $env:TEMP 'compact-docker-vhdx.txt'
    @(
        "select vdisk file=`"$VhdPath`""
        'attach vdisk readonly'
        'compact vdisk'
        'detach vdisk'
    ) | Set-Content -LiteralPath $script -Encoding ascii
    try {
        diskpart /s $script
    }
    finally {
        Remove-Item -LiteralPath $script -ErrorAction SilentlyContinue
    }
}

$after = (Get-Item -LiteralPath $VhdPath).Length
Write-Output ('After:  {0:N1} GB  (freed {1:N1} GB)' -f ($after / 1GB), (($before - $after) / 1GB))
Write-Output 'If it barely shrank, start Docker, run fstrim (see above), quit Docker and run this again.'
