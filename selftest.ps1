# AI Factory MVP 单命令自检（离线；不联网、不碰密钥、不改状态）
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "C:\Program Files\python\python.exe") { $py = "C:\Program Files\python\python.exe" } else { $py = "python" }
$fail = 0

function Run-Check([string]$name, [string[]]$pyArgs, [switch]$ExpectFailAllowed) {
    Write-Host "== $name"
    & $py -X utf8 @pyArgs
    $code = $LASTEXITCODE
    if ($code -ne 0 -and -not $ExpectFailAllowed) {
        Write-Host "FAIL $name (exit=$code)" -ForegroundColor Red
        $script:fail++
    } elseif ($code -ne 0 -and $ExpectFailAllowed) {
        Write-Host "NOTE $name exit=$code (回执含 UNVERIFIED/拒绝项，按设计非零)" -ForegroundColor Yellow
    }
}

Run-Check "check_card (21/21)" @("ops/bus/check_card.py")
Run-Check "check_handoff" @("ops/bus/check_handoff.py")
Run-Check "status" @("ops/bus/status.py")
Run-Check "audit self-test" @("ops/bus/audit.py", "--self-test")
Run-Check "next_round self-test" @("ops/bus/next_round.py", "--self-test")
Run-Check "source_ledger self-test" @("ops/probes/source_ledger.py", "--self-test")
Run-Check "watch self-test" @("ops/context/watch.py", "--self-test")
Run-Check "audit receipts (只读)" @("ops/bus/audit.py", "--json") -ExpectFailAllowed

if (Get-Command node -ErrorAction SilentlyContinue) {
    Write-Host "== node --check factory_ops"
    node --check "plugins/factory_ops/index.js"
    if ($LASTEXITCODE -ne 0) { Write-Host "FAIL node --check" -ForegroundColor Red; $fail++ }
} else {
    Write-Host "SKIP node --check (未找到 node)" -ForegroundColor Yellow
}

# T0/T1/T2 必须三份 ACCEPT(PASS)
$json = & $py -X utf8 -c "import json,sys; sys.path.insert(0,'ops/bus'); import audit; s=audit.load_state('ops/bus'); from pathlib import Path; print(json.dumps({t:audit.audit_receipt(Path('ops/bus/out')/(t+'.json'),s,'ops/bus')['verdict'] for t in ('T0','T1','T2')}))"
$verdicts = $json | ConvertFrom-Json
foreach ($t in @('T0','T1','T2')) {
    if ($verdicts.$t -ne 'ACCEPT') { Write-Host "FAIL $t verdict=$($verdicts.$t)" -ForegroundColor Red; $fail++ }
}

if ($fail -gt 0) { Write-Host "SELFTEST FAIL ($fail)" -ForegroundColor Red; exit 1 }
Write-Host "SELFTEST PASS" -ForegroundColor Green
