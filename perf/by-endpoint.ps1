param(
  [Parameter(Mandatory = $true)][string]$File
)

# Aggregates a k6 --out json= raw sample file by `endpoint` tag.
# Averages hide the story: a 5ms /health and a 900ms /api/graph/{id} blend into
# one meaningless number. This breaks the run down per endpoint so the slow
# path can be identified.

$path = Join-Path (Join-Path $PSScriptRoot 'results') $File
if (-not (Test-Path $path)) { Write-Host "no such file: $path" -ForegroundColor Red; exit 1 }

$rows = @{}
Get-Content $path -ReadCount 5000 | ForEach-Object {
  foreach ($line in $_) {
    if (-not $line) { continue }
    try { $s = $line | ConvertFrom-Json -ErrorAction Stop } catch { continue }
    if ($s.type -ne 'Point' -or $s.metric -ne 'http_req_duration') { continue }
    if (-not $s.data.tags) { continue }
    $ep = $s.data.tags.endpoint
    if (-not $ep) { $ep = '(untagged)' }
    if (-not $rows.ContainsKey($ep)) {
      $rows[$ep] = [pscustomobject]@{
        Endpoint = $ep; Samples = [System.Collections.Generic.List[double]]::new()
        Failed = 0; Total = 0
      }
    }
    $rows[$ep].Samples.Add([double]$s.data.value)
  }
}

function Percentile($sorted, $p) {
  if ($sorted.Count -eq 0) { return 0 }
  $idx = [math]::Min($sorted.Count - 1, [math]::Max(0, [math]::Ceiling($p * $sorted.Count) - 1))
  return $sorted[$idx]
}

$out = foreach ($k in $rows.Keys) {
  $r = $rows[$k]
  $sorted = $r.Samples.ToArray() | Sort-Object
  [pscustomobject]@{
    Endpoint  = $k
    N         = $sorted.Count
    'Avg ms'  = [math]::Round((($sorted | Measure-Object -Average).Average), 1)
    'Min ms'  = [math]::Round($sorted[0], 1)
    'Med ms'  = [math]::Round((Percentile $sorted 0.50), 1)
    'p90 ms'  = [math]::Round((Percentile $sorted 0.90), 1)
    'p95 ms'  = [math]::Round((Percentile $sorted 0.95), 1)
    'p99 ms'  = [math]::Round((Percentile $sorted 0.99), 1)
    'Max ms'  = [math]::Round($sorted[-1], 1)
  }
}

$out | Sort-Object 'Avg ms' -Descending | Format-Table -AutoSize
