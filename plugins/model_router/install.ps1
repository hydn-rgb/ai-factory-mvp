# Install the model router into an OpenCode config (default: global).
# - Backs up the config before writing.
# - Uses the V2 "plugins" array. Never touches DSH/WorkBuddy configs.
param(
  [string]$ConfigPath = "$env:USERPROFILE\.config\opencode\opencode.json",
  [string]$PluginPath = "D:/AI_Factory/plugins/model_router"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $ConfigPath)) { throw "config not found: $ConfigPath" }

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$backup = "$ConfigPath.bak-model-router-$stamp"
Copy-Item -LiteralPath $ConfigPath -Destination $backup -Force

$raw = [IO.File]::ReadAllText($ConfigPath, [Text.Encoding]::UTF8)
$cfg = $raw | ConvertFrom-Json
if (-not $cfg.PSObject.Properties["plugins"]) {
  $cfg | Add-Member -NotePropertyName plugins -NotePropertyValue @()
}
$list = @($cfg.plugins)
$norm = $PluginPath.Replace("\", "/").TrimEnd("/")
$exists = $false
foreach ($item in $list) {
  if ($item -is [string] -and $item.Replace("\", "/").TrimEnd("/") -eq $norm) { $exists = $true }
}
if (-not $exists) { $list += $norm }
$cfg.plugins = $list

$json = $cfg | ConvertTo-Json -Depth 30
[IO.File]::WriteAllText($ConfigPath, $json + [Environment]::NewLine, (New-Object Text.UTF8Encoding($false)))

Write-Output "OK installed"
Write-Output "config=$ConfigPath"
Write-Output "plugin=$norm"
Write-Output "backup=$backup"
Write-Output "next: restart OpenCode (or run: opencode reload)"
