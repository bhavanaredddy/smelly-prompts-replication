# Runs every analysis step that needs no LLM (seconds to a few minutes, $0).
$ErrorActionPreference = "Stop"
$py = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
& $py "$PSScriptRoot\a_replicate.py"
& $py "$PSScriptRoot\b_compare_friend.py"
& $py "$PSScriptRoot\g_stats.py"
& $py "$PSScriptRoot\h_breakdown.py"
& $py "$PSScriptRoot\d_detector.py"
