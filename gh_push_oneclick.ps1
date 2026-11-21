# 一键：gh 浏览器登录 -> 自动抓设备码 -> 建私有仓库 -> 上传 MVP
# 不回显、不落盘任何 token。用法见文末。
param(
  [string]$RepoName = "ai-factory-mvp",
  [switch]$Public
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Test-GhLogin {
  try { & gh auth status 2>&1 | Out-Null; return ($LASTEXITCODE -eq 0) } catch { return $false }
}

Write-Host "== Step 0/3  检查登录状态 ==" -ForegroundColor Cyan
if (Test-GhLogin) {
  Write-Host "已登录，跳过登录步骤。" -ForegroundColor Green
} else {
  Write-Host "未登录，启动浏览器设备码流程..." -ForegroundColor Yellow

  $tmpDir = Join-Path $env:TEMP ("ghlogin_" + [guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Path $tmpDir | Out-Null
  $out = Join-Path $tmpDir "out.txt"
  $err = Join-Path $tmpDir "err.txt"
  $inp = Join-Path $tmpDir "in.txt"
  Set-Content -Path $inp -Value "`n" -NoNewline

  # 启动 gh 登录：stdin 喂一个回车（让它自动打开浏览器），输出重定向到文件以便抓码
  $proc = Start-Process -FilePath "gh" -ArgumentList "auth login --web" `
    -RedirectStandardInput $inp -RedirectStandardOutput $out -RedirectStandardError $err `
    -NoNewWindow -PassThru

  Write-Host "== Step 1/3  正在获取设备码 ==" -ForegroundColor Cyan
  $code = $null
  for ($i = 0; $i -lt 80; $i++) {
    Start-Sleep -Milliseconds 500
    $txt = ""
    if (Test-Path $out) { $txt += (Get-Content $out -Raw -ErrorAction SilentlyContinue) }
    if (Test-Path $err) { $txt += (Get-Content $err -Raw -ErrorAction SilentlyContinue) }
    if ($txt -match '(?i)one-time code:\s*([A-Z0-9]{4}-[A-Z0-9]{4})') { $code = $matches[1]; break }
  }

  if (-not $code) {
    Write-Host "X 未能自动抓到设备码。请手动执行下面这条命令，把屏幕上的 code 复制出来：" -ForegroundColor Red
    Write-Host "   gh auth login --web" -ForegroundColor Yellow
    Write-Host "然后到 https://github.com/login/device 输入该 code 授权。" -ForegroundColor Yellow
    try { $proc | Stop-Process -Force } catch {}
    exit 1
  }

  Set-Clipboard -Value $code
  Write-Host "OK 设备码已复制到剪贴板：$code" -ForegroundColor Green
  Write-Host "OK 正在打开浏览器 https://github.com/login/device" -ForegroundColor Green
  Start-Process "https://github.com/login/device"
  Write-Host ""
  Write-Host ">>> 请在浏览器页面按 Ctrl+V 粘贴刚才的码，点 Continue，再点 Authorize github CLI" -ForegroundColor Yellow
  Write-Host ">>> 授权完成后，回到这里按【回车】" -ForegroundColor Yellow
  Read-Host | Out-Null

  # 等 gh 轮询完成
  $proc.WaitForExit()
  Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue

  if (-not (Test-GhLogin)) {
    Write-Host "X 登录仍未完成。请确认浏览器里已点 Authorize，然后重新运行本脚本。" -ForegroundColor Red
    exit 1
  }
  Write-Host "OK 登录成功。" -ForegroundColor Green
}

Write-Host "== Step 2/3  建仓库 ==" -ForegroundColor Cyan
git branch -M main | Out-Null
$vis = if ($Public) { "--public" } else { "--private" }
& gh repo create $RepoName $vis --source=. --remote=origin --push
if ($LASTEXITCODE -ne 0) {
  Write-Host "仓库名 $RepoName 可能已存在，尝试直接推送..." -ForegroundColor Yellow
  $login = (& gh api user --jq .login).Trim()
  git remote remove origin 2>$null
  git remote add origin "https://github.com/$login/$RepoName.git"
  git push -u origin main
  if ($LASTEXITCODE -ne 0) {
    Write-Host "X 仍失败。换名字重试：" -ForegroundColor Red
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\gh_push_oneclick.ps1 -RepoName ai-factory-mvp-2026" -ForegroundColor Yellow
    exit 1
  }
}

Write-Host "== Step 3/3  完成 ==" -ForegroundColor Cyan
$login = (& gh api user --jq .login).Trim()
Write-Host "OK 已上传：https://github.com/$login/$RepoName" -ForegroundColor Green
Write-Host "（私有仓库需登录后可见；想要公开仓库请加 -Public 参数重跑）" -ForegroundColor DarkGray
