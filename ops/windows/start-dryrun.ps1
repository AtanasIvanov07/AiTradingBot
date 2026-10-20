# Start the H5 dry-run (paper trading) bot and its watchdog on this Windows PC, in the background.
# Learning-only path (PROJECT_PLAN.md amendment A1): config.json is dry-run, enforced by tests/test_repo.py.
# Each part starts only if it isn't already running, so this is safe to run again at any time.
# Usage, from the repo root:  powershell -ExecutionPolicy Bypass -File ops\windows\start-dryrun.ps1
# (Kept ASCII-only: Windows PowerShell 5.1 reads BOM-less scripts in the ANSI code page.)
$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repo

function Find-Running([string]$pattern) {
    Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -like $pattern -and $_.CommandLine -notlike "*drill*"
    }
}

$private = "user_data\config.private.json"
if (-not (Test-Path $private)) { throw "$private is missing: copy config.private.example.json first." }
New-Item -ItemType Directory -Force "user_data\logs" | Out-Null

$bot = Find-Running "*H5TrendVol*"
if ($bot) {
    Write-Output "Bot already running (PID $($bot.ProcessId -join ', '))."
} else {
    $arguments = @(
        "trade",
        "--userdir", "user_data",
        "--config", "user_data\config.json",
        "--config", $private,
        "--strategy", "H5TrendVol",
        "--db-url", "sqlite:///user_data/tradesv3.dryrun.sqlite",
        "--logfile", "user_data\logs\freqtrade.log"
    )
    $process = Start-Process -FilePath ".venv\Scripts\freqtrade.exe" -ArgumentList $arguments `
        -WorkingDirectory $repo -WindowStyle Hidden -PassThru
    Write-Output "Started dry-run bot, PID $($process.Id). Log: user_data\logs\freqtrade.log"
    Start-Sleep -Seconds 30  # let the bot's API come up before the watchdog's first check
}

# External watchdog (PROJECT_PLAN.md section 6.5): checks every 2 minutes and acts on the
# section 6.4 and 6.6 triggers, so detection plus action stays within Gate 3's 5-minute limit.
$watchdog = Find-Running "*aitradingbot.ops.watchdog*"
if ($watchdog) {
    Write-Output "Watchdog already running (PID $($watchdog.ProcessId -join ', '))."
} else {
    $wd = Start-Process -FilePath ".venv\Scripts\python.exe" `
        -ArgumentList @("-m", "aitradingbot.ops.watchdog", "--loop", "120") `
        -WorkingDirectory $repo -WindowStyle Hidden -PassThru
    Write-Output "Started watchdog, PID $($wd.Id). Log: user_data\logs\watchdog.log"
}
