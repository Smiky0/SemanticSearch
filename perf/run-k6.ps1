param(
  [Parameter(Mandatory = $true)][string]$Script,
  [string]$Name,
  [int]$TimeoutSec = 3600,
  [hashtable]$Env = @{},
  # Raw samples are ~100 MB per run and dominate wall-clock time and disk churn.
# Skip unless needed; the summary plus stdout are enough for reporting.
  [switch]$Raw
)

# Runs a k6 script inside the grafana/k6 container against the compose stack.
# Output is captured to perf/results/<name>-summary.json and a matching
# <name>-stdout.txt so runs can be compared after the fact.

$ErrorActionPreference = 'Stop'
# $PSScriptRoot is already the perf/ directory.
$root = $PSScriptRoot
$results = Join-Path $root 'results'
$scripts = Join-Path $root 'k6'
New-Item -ItemType Directory -Force -Path $results | Out-Null

# Docker Desktop on Windows mangles backslash paths in -v; always use posix.
$scriptsMount = ($scripts -replace '\\', '/')
$resultsMount = ($results -replace '\\', '/')

if (-not $Name) { $Name = [IO.Path]::GetFileNameWithoutExtension($Script) }
$summary = Join-Path $results "$Name-summary.json"
$stdout = Join-Path $results "$Name-stdout.txt"

$envArgs = @(
  '-e', "BASE_URL=http://backend:8000",
  '-e', "FRONTEND_URL=http://frontend"
)
foreach ($k in $Env.Keys) { $envArgs += @('-e', "$($k)=$($Env[$k])") }

Write-Host "=== k6 run: $Script (name=$Name) ===" -ForegroundColor Cyan

$k6Args = @('run', '--quiet', '--summary-export', "/results/$Name-summary.json")
if ($Raw) {
  $k6Args += @('--out', "json=/results/$Name-raw.json")
}
$k6Args += $envArgs + @($Script)

Write-Host "k6 args: $($k6Args -join ' | ')" -ForegroundColor DarkGray

$sw = [Diagnostics.Stopwatch]::StartNew()
# k6 logs to stderr, which PowerShell surfaces as NativeCommandError. Under
# 'Stop' the first log line would abort the run, so relax it for this call
# and rely on $LASTEXITCODE instead.
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'

# Name the container so the timeout path can kill it by name. $p.Id is the
# host PID of the docker CLI, which docker kill cannot resolve.
$container = "k6-$Name-$PID"

function Write-Utf8([string]$Path, [string]$Text) {
  [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding $false))
}

# Honour -TimeoutSec. Without this a hung run blocks the shell indefinitely.
$stdoutPath = "$stdout.part"
$p = Start-Process -FilePath 'docker' -ArgumentList (@('run', '--rm',
    '--name', $container,
    '--network', 'semantic-code-search_default',
    '-v', "${scriptsMount}:/scripts:ro",
    '-v', "${resultsMount}:/results",
    'grafana/k6:latest') + $k6Args) `
  -NoNewWindow -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError "$stdoutPath.err"

# Touching .Handle caches the process handle so .ExitCode is populated after
# the timed WaitForExit; without this it comes back null.
$null = $p.Handle

if (-not $p.WaitForExit($TimeoutSec * 1000)) {
  Write-Host "TIMEOUT after ${TimeoutSec}s - killing container $container" -ForegroundColor Red
  try { & docker kill $container 2>&1 | Out-Null } catch { }
  try { $p.Kill() } catch { }
  if (Test-Path $stdoutPath) { Write-Utf8 $stdout (Get-Content $stdoutPath -Raw) }
  Remove-Item $stdoutPath, "$stdoutPath.err" -ErrorAction SilentlyContinue
  Write-Host "partial stdout: $stdout" -ForegroundColor Red
  exit 124
}

# Second, unbounded wait lets .NET finish teardown so ExitCode is final.
$p.WaitForExit()
$code = $p.ExitCode
$errText = ''
if (Test-Path "$stdoutPath.err") { $errText = Get-Content "$stdoutPath.err" -Raw }

# k6 writes its logs to stderr. Surface them so a script error is never
# silently swallowed, but keep the result files clean of the noise.
if ($errText) {
  $errLines = @($errText -split "`r?`n" | Where-Object { $_.Trim() })
  # k6 can emit thousands of identical script-exception lines; keep the log readable.
  $shown = @($errLines | Select-Object -First 25)
  if ($errLines.Count -gt $shown.Count) { $shown += "... ($($errLines.Count - $shown.Count) more lines)" }
  Write-Host "--- k6 stderr ($($errLines.Count) lines) ---" -ForegroundColor DarkYellow
  $shown | ForEach-Object { Write-Host $_ }
  Write-Host "--- end k6 stderr ---" -ForegroundColor DarkYellow

  # A script exception never produces a request, so thresholds stay green while
  # the test is actually broken. Treat it as a failure instead.
  if ($errText -match 'level=error' -and $code -eq 0) {
    Write-Host "FAIL: k6 reported script errors but exited 0 - treating as failure" -ForegroundColor Red
    $code = 1
  }
}

if (Test-Path $stdoutPath) {
  $outText = Get-Content $stdoutPath -Raw
  if ($null -eq $outText) { $outText = '' }
  Write-Utf8 $stdout $outText
}
Remove-Item $stdoutPath, "$stdoutPath.err" -ErrorAction SilentlyContinue
$ErrorActionPreference = $prevEap
$sw.Stop()

Write-Host ""
Write-Host "=== $Name finished in $([math]::Round($sw.Elapsed.TotalSeconds,1))s (exit=$code) ===" -ForegroundColor Yellow
Write-Host "summary: $summary"
if ($code -ne 0) { Write-Host "NOTE: exit=$code - check the k6 stderr above and whether $summary exists" -ForegroundColor Red }
exit $code
