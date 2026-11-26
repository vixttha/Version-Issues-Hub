$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $env:RUNNER_TEMP 'independent-vib-audit')
$expected = @('api-boundaries.json','historical-removals.json','inferred-review.json','candidate-graph.json')
function Check-Manifest([string[]]$lines) {
  if ($lines.Count -ne $expected.Count) { throw 'Missing or extra evidence' }
  $seen = @()
  foreach ($line in $lines) {
    if ($line -cnotmatch '^([a-f0-9]{64}) \*([a-z-]+\.json)$') { throw 'Malformed evidence' }
    $hash=$Matches[1]; $name=$Matches[2]
    if ($name -cnotin $expected -or $name -cin $seen) { throw 'Unexpected or repeated evidence' }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $name).Hash.ToLowerInvariant() -cne $hash) { throw 'Digest mismatch' }
    $seen += $name
  }
}
$lines = @(Get-Content -LiteralPath 'bash-sha256.txt')
Check-Manifest $lines
foreach ($bad in @('omitted','duplicate','forged')) {
  $failed=$false
  try {
    switch ($bad) {
      'omitted' { Check-Manifest @($lines[0]) }
      'duplicate' { Check-Manifest @($lines[0],$lines[0],$lines[2],$lines[3]) }
      'forged' { Check-Manifest @(('0'*64+' *api-boundaries.json'),$lines[1],$lines[2],$lines[3]) }
    }
  } catch { $failed=$true }
  if (-not $failed) { throw "Accepted invalid $bad evidence" }
}
$g=Get-Content -Raw candidate-graph.json | ConvertFrom-Json
if ($g.receipt.source -cne 'b68796db12681fe4d43b562c8647deca38fa819c' -or $g.negative_probes -ne 4) { throw 'Wrong candidate qualification' }
Write-Output 'PowerShell verified four independent file digests and rejected three bad manifests'
