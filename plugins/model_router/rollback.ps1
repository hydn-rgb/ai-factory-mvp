# Remove the model router from an OpenCode config (default: global).
# - Backs up the config before writing.
# - Does NOT delete code unless -DeletePluginDir is passed.
# - Then restart OpenCode. Removing the directory alone is also enough.
param(
  [string]$ConfigPath = "$env:USERPROFILE\.config\opencode\opencode.json",
  [string]$PluginPath = "D:/AI_Factory/plugins/model_router",
  [switch]$DeletePluginDir
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $ConfigPath)) { throw "config not found: $ConfigPath" }

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$backup = "$ConfigPath.bak-model-router-rollback-$stamp"
Copy-Item -LiteralPath $ConfigPath -Destination $backup -Force

$raw = [IO.File]::ReadAllText($ConfigPath, [Text.Encoding]::UTF8)
$cfg = $raw | ConvertFrom-Json
$norm = $PluginPath.Replace("\", "/").TrimEnd("/")
if ($cfg.PSObject.Properties["plugins"]) {
  $kept = @()
  foreach ($item in @($cfg.plugins)) {
    if ($item -is [string] -and $item.Replace("\", "/").TrimEnd("/") -eq $norm) { continue }
    $kept += $item
  }
  $cfg.plugins = $kept
}

$json = $cfg | ConvertTo-Json -Depth 30
[IO.File]::WriteAllText($ConfigPath, $json + [Environment]::NewLine, (New-Object Text.UTF8Encoding($false)))

if ($DeletePluginDir -and (Test-Path -LiteralPath $PluginPath)) {
  Remove-Item -LiteralPath $PluginPath -Recurse -Force
  Write-Output "deleted=$PluginPath"
}

Write-Output "OK removed"
Write-Output "config=$ConfigPath"
Write-Output "backup=$backup"
Write-Output "next: restart OpenCode"
