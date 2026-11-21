# 启动本机 DS 桥接服务（只监听 127.0.0.1:8791）
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$node = "node"
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Write-Error "未找到 node；请先安装 Node 或把它加入 PATH。"
  exit 2
}
Write-Host "DS bridge -> http://127.0.0.1:8791"
& $node "$here\bridge.js"
