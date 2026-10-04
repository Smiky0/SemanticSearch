param(
  [string]$Name = "all"
)

# Renders a readable report from a k6 --summary-export JSON file.
#
# k6's summary JSON has no `type` discriminator, so the metric kind is inferred
# from the keys present:
#   trend  -> has med/p(95)/max   counter -> has count+rate   rate -> has passes/fails

function Is-Trend($v)   { return ($null -ne $v.med -or $null -ne $v.'p(95)' -or $null -ne $v.max) }
function Is-Rate($v)    { return ($null -ne $v.passes -and $null -ne $v.fails) }
function Is-Counter($v) { return ($null -ne $v.count -and $null -ne $v.rate) }

function Fmt($v) {
  if ($null -eq $v) { return '' }
  if ($v -is [string] -or $v -is [bool]) { return $v }
  return [math]::Round([double]$v, 1)
}

$resultsDir = Join-Path $PSScriptRoot 'results'
$files = if ($Name -eq 'all') {
  Get-ChildItem -Path $resultsDir -Filter '*-summary.json' | Sort-Object Name
} else {
  Get-ChildItem -Path $resultsDir -Filter "$Name-summary.json"
}

if (-not $files) { Write-Host "no summary files found in $resultsDir" -ForegroundColor Red; exit 1 }

foreach ($f in $files) {
  $j = Get-Content $f.FullName -Raw | ConvertFrom-Json
  $m = $j.metrics
  $title = $f.BaseName -replace '-summary$', ''

  Write-Host ""
  Write-Host ("=" * 76) -ForegroundColor Cyan
  Write-Host "  $title" -ForegroundColor Cyan
  Write-Host ("=" * 76) -ForegroundColor Cyan

  if ($m.http_reqs) {
    Write-Host ""
    Write-Host "THROUGHPUT"
    Write-Host ("  {0,-32} {1,14:N2} req/s" -f 'http_reqs', $m.http_reqs.rate)
    if ($m.iterations) { Write-Host ("  {0,-32} {1,14:N0}" -f 'iterations', $m.iterations.count) }
    if ($m.data_received) { Write-Host ("  {0,-32} {1,14:N2} MB" -f 'data received', ($m.data_received.rate / 1MB)) }
    if ($m.vus) { Write-Host ("  {0,-32} {1,14:N0}" -f 'vus max', $m.vus_max.max) }
  }

  Write-Host ""
  Write-Host "REQUESTS"
  $lat = $m.http_req_duration
  if ($lat) {
    Write-Host ("  {0,-32} {1,14:N1}" -f 'avg ms', (Fmt $lat.avg))
    Write-Host ("  {0,-32} {1,14:N1}" -f 'med ms', (Fmt $lat.med))
    Write-Host ("  {0,-32} {1,14:N1}" -f 'p(90) ms', (Fmt $lat.'p(90)'))
    Write-Host ("  {0,-32} {1,14:N1}" -f 'p(95) ms', (Fmt $lat.'p(95)'))
    Write-Host ("  {0,-32} {1,14:N1}" -f 'p(99) ms', (Fmt $lat.'p(99)'))
    Write-Host ("  {0,-32} {1,14:N1}" -f 'max ms', (Fmt $lat.max))
  }
  if ($m.http_req_failed) {
    $v = $m.http_req_failed
    # For http_req_failed, Rate semantics invert: `passes` counts requests that
    # FAILED (the metric is true on failure). value is the failure rate.
    $col = if ($v.value -eq 0) { 'Green' } else { 'Red' }
    Write-Host ("  {0,-32} {1,14:P2}  ({2} of {3} requests failed)" -f 'http_req_failed', $v.value, $v.passes, ($v.passes + $v.fails)) -ForegroundColor $col
  }

  $checks = $j.root_group.checks
  if ($checks -is [array]) { $checks = $checks[0] }
  if ($checks) {
    Write-Host ""
    Write-Host "CHECKS"
    foreach ($p in $checks.PSObject.Properties) {
      $c = $p.Value
      if ($null -eq $c.passes) { continue }
      $tot = $c.passes + $c.fails
      $col = if ($c.fails -eq 0) { 'Green' } else { 'Yellow' }
      Write-Host ("  {0,-44} {1,8} / {2,-8} {3}" -f $c.name, $c.passes, $tot, $(if ($c.fails) { "FAIL x$($c.fails)" } else { 'ok' })) -ForegroundColor $col
    }
  }

  $builtIn = @('http_reqs','http_req_duration','http_req_failed','http_req_blocked',
               'http_req_connecting','http_req_tls_handshaking','http_req_sending',
               'http_req_waiting','http_req_receiving','iterations','data_received',
               'data_sent','checks','vus','vus_max','vus_initiations',
               'iteration_duration','dropped_iterations')

  $others = $m.PSObject.Properties | Where-Object { $_.Name -notin $builtIn }

  if ($others) {
    Write-Host ""
    Write-Host "CUSTOM METRICS"
    foreach ($o in $others) {
      $v = $o.Value
      if (Is-Trend $v) {
        Write-Host ("  {0,-34} trend    avg={1,9:N1} med={2,9:N1} p95={3,9:N1} max={4,9:N1}" -f `
          $o.Name, (Fmt $v.avg), (Fmt $v.med), (Fmt $v.'p(95)'), (Fmt $v.max))
      } elseif (Is-Rate $v) {
        $col = if ($v.value -ge 0.99) { 'Green' } elseif ($v.value -ge 0.9) { 'Yellow' } else { 'Red' }
        Write-Host ("  {0,-34} rate     {1,9:P2}   ({2} ok / {3} bad)" -f $o.Name, $v.value, $v.passes, $v.fails) -ForegroundColor $col
      } elseif (Is-Counter $v) {
        Write-Host ("  {0,-34} counter  {1,9:N0}" -f $o.Name, $v.count)
      }
    }
  }

  $withThresholds = $m.PSObject.Properties | Where-Object { $null -ne $_.Value.thresholds }
  if ($withThresholds) {
    Write-Host ""
    Write-Host "THRESHOLDS"
    foreach ($t in $withThresholds) {
      foreach ($k in $t.Value.thresholds.PSObject.Properties) {
        # k6 records whether the threshold was CROSSED, so false == satisfied.
        $ok = -not [bool]$k.Value
        $col = if ($ok) { 'Green' } else { 'Red' }
        $tag = if ($ok) { 'PASS' } else { 'FAIL' }
        Write-Host ("  [{0}] {1,-32} {2}" -f $tag, $t.Name, $k.Name) -ForegroundColor $col
      }
    }
  }
}
