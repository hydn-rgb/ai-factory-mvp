# GitHub 上传脚本：不伪造上传，不写入任何密钥/token
param([string]$Repo = "")

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# 1) 认证检查
& gh auth status 2>&1 | Out-String | Write-Host
if ($LASTEXITCODE -ne 0) {
    Write-Host "未登录 GitHub。请先执行：gh auth login" -ForegroundColor Red
    Write-Host "然后重新运行：powershell -ExecutionPolicy Bypass -File .\push.ps1 -Repo https://github.com/<账号>/ai-factory-mvp.git" -ForegroundColor Yellow
    exit 2
}

if (-not $Repo) {
    Write-Host "缺少 -Repo。示例：-Repo https://github.com/<账号>/ai-factory-mvp.git" -ForegroundColor Red
    exit 2
}

# 2) 仓库检查
if (-not (Test-Path ".git")) {
    git init
    git add -A
    git commit -m "AI Factory MVP: T0-T2 closed, factory_ops plugin, public-data probes (2026-11-21)"
} else {
    $dirty = git status --porcelain
    if ($dirty) {
        git add -A
        git commit -m "Update AI Factory MVP release"
    }
}

git branch -M main
$remote = & git remote get-url origin 2>$null
if (-not $remote) { git remote add origin $Repo }
git push -u origin main
Write-Host "PUSHED to $Repo" -ForegroundColor Green
