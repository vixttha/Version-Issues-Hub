param([string]$Before,[string]$After,[string]$Out)
$ErrorActionPreference='Stop'
$a=Get-Content -Raw -LiteralPath $Before | ConvertFrom-Json
$b=Get-Content -Raw -LiteralPath $After | ConvertFrom-Json
if ($a.source -ne 'b68796db12681fe4d43b562c8647deca38fa819c' -or $b.source -ne '041e187dc1d383082c1a4805e6d4743eec97e535') {throw 'wrong source'}
$beforeKeys=@($a.cases | ForEach-Object {"$($_.boundary)/$($_.case)"})
$afterKeys=@($b.cases | ForEach-Object {"$($_.boundary)/$($_.case)"})
if (Compare-Object $beforeKeys $afterKeys) {throw 'different case inventories'}
if (@($afterKeys | Sort-Object -Unique).Count -ne $afterKeys.Count) {throw 'duplicate cases'}
foreach ($row in $b.cases) {if (($row.outcome -cne $row.expected) -or ($row.pass -ne $true)) {throw "failed: $($row.boundary)/$($row.case)"}}
$bad=@($a.cases | Where-Object {$_.outcome -cne $_.expected})
if ($bad.Count -lt 8) {throw 'baseline negative controls not demonstrated'}
if ($b.counts.total -ne $afterKeys.Count -or $b.counts.failed -ne 0 -or $b.counts.passed -ne $afterKeys.Count) {throw 'inconsistent receipt'}
[IO.File]::WriteAllText($Out,("{0} matched strict assertions; {1} original failures" -f $afterKeys.Count,$bad.Count))
