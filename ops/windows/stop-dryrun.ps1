# Stop the H5 dry-run bot and its watchdog on this Windows PC. The bot's state lives in
# user_data\tradesv3.dryrun.sqlite, so a later start resumes the same paper positions.
# Usage, from the repo root:  powershell -ExecutionPolicy Bypass -File ops\windows\stop-dryrun.ps1
# freqtrade.exe is only a launcher: the bot runs in python.exe children, so this stops every process
# whose command line names the strategy or the watchdog (not the drill bot), not just the launcher.
$targets = Get-CimInstance Win32_Process | Where-Object {
    ($_.CommandLine -like "*H5TrendVol*" -or $_.CommandLine -like "*aitradingbot.ops.watchdog*") -and
    $_.CommandLine -notlike "*drill*"
}
if (-not $targets) {
    Write-Output "No H5 dry-run bot or watchdog is running."
    exit 0
}
foreach ($target in $targets) {
    Stop-Process -Id $target.ProcessId -Force -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Stopped PID $($target.ProcessId) ($($target.Name))."
}
