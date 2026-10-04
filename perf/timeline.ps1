param(
  [Parameter(Mandatory = $true)][string]$File,
  [int]$BucketSec = 10
)

# Buckets http_req_duration samples over wall-clock time.
# Latency percentiles alone cannot distinguish "slow all the time" from
# "fast most of the time, dead some of the time". A time series makes an
# outage window obvious even when p95 looks healthy.

$path = Join-Path (Join-Path $PSScriptRoot 'results') $File
if (-not (Test-Path $path)) { Write-Host "no such file: $path" -ForegroundColor Red; exit 1 }

$pts = New-Object System.Collections.Generic.List[object]
$minT = [double]::MaxValue
foreach ($chunk in (Get-Content $path -ReadCount 5000)) {
  foreach ($line in $chunk) {
    if (-not $line) { continue }
    try { $s = $line | ConvertFrom-Json -ErrorAction Stop } catch { continue }
    if ($s.type -ne 'Point' -or $s.metric -ne 'http_req_duration') { continue }
    if (-not $s.data.tags) { continue }
    # k6 v2 emits an RFC3339 string in data.time; older builds emit epoch seconds.
    $t = 0.0
    if ($s.data.time -is [string]) {
      $t = ([datetimeoffset]::Parse($s.data.time)).ToUnixTimeMilliseconds() / 1000.0
    } else {
      $t = [double]$s.data.time
    }
    if ($t -lt $minT) { $minT = $t }
    $pts.Add([pscustomobject]@{ T = $t; V = [double]$s.data.value; Ep = $s.data.tags.endpoint; OK = $s.data.tags.expected_response })
  }
}

if ($pts.Count -eq 0) { Write-Host "no http_req_duration points tagged in $File" -ForegroundColor Red; exit 1 }

$buckets = @{}
foreach ($p in $pts) {
  $b = [math]::Floor(($p.T - $minT) / $BucketSec) * $BucketSec
  if (-not $buckets.ContainsKey($b)) {
    $buckets[$b] = [pscustomobject]@{
      Offset = $b; N = 0; Failed = 0
      Vals = [System.Collections.Generic.List[double]]::new()
    }
  }
  $buckets[$b].N++
  if ($p.OK -eq 'false' -or $p.OK -eq $false) { $buckets[$b].Failed++ }
  $buckets[$b].Vals.Add($p.V)
}

$bar = '#'
$out = foreach ($k in ($buckets.Keys | Sort-Object)) {
  $b = $buckets[$k]
  $s = $b.Vals.ToArray() | Sort-Object
  $med = $s[[math]::Floor($s.Count / 2)]
  $p95 = $s[[math]::Min($s.Count - 1, [math]::Ceiling(0.95 * $s.Count) - 1)]
  $avg = ($s | Measure-Object -Average).Average
  [pscustomobject]@{
    't+s'    = $b.Offset
    'n'      = $b.N
    'fail'   = $b.Failed
    'avg ms' = [math]::Round($avg, 1)
    'med ms' = [math]::Round($med, 1)
    'p95 ms' = [math]::Round($p95, 1)
    'max ms' = [math]::Round($s[-1], 1)
  }
}

$out | Format-Table -AutoSize
