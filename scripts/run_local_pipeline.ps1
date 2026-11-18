# Runs every step that needs the local LLM (free, via Ollama). Safe to re-run: finished
# steps are skipped. Usage: .\scripts\run_local_pipeline.ps1 [-Model llama3.2:3b]
param([string]$Model = "llama3.2:3b")
$ErrorActionPreference = "Stop"
$py = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
$env:SMELLREP_MODEL = $Model

# Keep Windows from sleeping while this script runs (released automatically on exit).
Add-Type -Namespace Win32 -Name Power -MemberDefinition @"
[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);
"@
[void][Win32.Power]::SetThreadExecutionState([uint32]"0x80000001")

& $py "$PSScriptRoot\e_fixer.py" --model $Model --mode rewrite
& $py "$PSScriptRoot\e_fixer.py" --model $Model --mode oracle
& $py "$PSScriptRoot\c_trace_local.py" --model $Model --conditions clean smelly fixed_rewrite fixed_oracle --runs 1
& $py "$PSScriptRoot\e_fixer.py" --model $Model --mode blind
& $py "$PSScriptRoot\d_detector.py" --model $Model --run-llm
& $py "$PSScriptRoot\f_eval_local.py" --model $Model
