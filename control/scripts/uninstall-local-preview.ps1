# Owner-run optional cache removal. Does not touch a server, registry or business data.
[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='High')]
param([switch]$RemoveProfile, [switch]$DeviceRevoked)
$ErrorActionPreference = 'Stop'
Write-Output 'Portable uninstall: revoke the paired device on your server, close the app, then remove the extracted application folder.'
if (-not $RemoveProfile) { Write-Output 'No files removed. Optional profile cleanup requires -RemoveProfile -DeviceRevoked.'; exit 0 }
if (-not $DeviceRevoked) { throw 'Confirm server-side device revocation first. This script cannot verify or perform revocation.' }
if (Get-Process -Name 'OpenBot-Control-Local-x64' -ErrorAction SilentlyContinue) { throw 'Close the local control app before removing its cache.' }
$root = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'OpenBotControlLocal'
if (Test-Path -LiteralPath $root) {
  $item = Get-Item -LiteralPath $root -Force
  if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Refusing a reparse-point profile.' }
  $links = Get-ChildItem -LiteralPath $root -Force -Recurse | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }
  if ($links) { throw 'Refusing recursive removal containing a reparse point.' }
  if ($PSCmdlet.ShouldProcess($root, 'Remove only the local OpenBot Control cache')) { Remove-Item -LiteralPath $root -Recurse -Force }
}
Write-Output 'No server database, provider credentials or Windows installation setting was changed. Physical erasure is not certified.'
