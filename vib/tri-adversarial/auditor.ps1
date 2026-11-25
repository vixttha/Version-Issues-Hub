param([string]$Root,[string]$Contract,[string]$Id)
$ErrorActionPreference='Stop'
function Check($ok,[string]$why){if(!$ok){throw $why}}
$c=Get-Content -LiteralPath $Contract -Raw -Encoding utf8|ConvertFrom-Json -AsHashtable
$s=@($c.scenarios|Where-Object {$_.id -ceq $Id})
Check ($s.Count -eq 1) 'scenario'
$s=$s[0]
$r=Get-Content -LiteralPath (Join-Path $Root 'receipt.json') -Raw -Encoding utf8|ConvertFrom-Json -AsHashtable
$l=Get-Content -LiteralPath (Join-Path $Root 'ledger.json') -Raw -Encoding utf8|ConvertFrom-Json -AsHashtable
$h=Get-Content -LiteralPath (Join-Path $Root 'handoff.json') -Raw -Encoding utf8|ConvertFrom-Json -AsHashtable
Check ($r.id -ceq $Id -and $r.product -ceq $c.product) 'identity'
Check ($r.recovery -ceq $s.recovery) 'recovery'
Check ($l.schema_version -is [long] -and $l.schema_version -eq 1 -and $l.repository -ceq 'example/adopter' -and $l.Count -eq 3) 'ledger schema'
Check ($l.issues.Count -eq 1) 'singleton'
$row=$l.issues[0]
Check ($row.issue -eq $s.winner -and $row.version -ceq 'v1.0.6.1' -and $row.state -ceq 'in_progress' -and $row.Count -eq 4) 'allocation'
Check ($row.acceptance.Count -eq 1 -and $row.acceptance[0] -ceq 'preserve state') 'criteria'
Check ($h.Count -eq 3 -and $h.history.Count -eq 0 -and $h.schema_version -eq 1) 'handoff schema'
$a=$h.active
Check ($a.Count -eq 8 -and $a.issue -eq $s.winner -and $a.version -ceq $row.version -and $a.phase -ceq 'Worker' -and $a.next_action -ceq 'repair' -and $null -eq $a.fix_sha -and $null -eq $a.candidate_sha -and $null -eq $a.pull_request -and $a.evidence.Count -eq 0) 'handoff'
$patch=@($r.events|Where-Object {$_.method -ceq 'PATCH'})
Check ($patch.Count -eq $s.patches) 'patch count'
$pub=@($patch|Where-Object {$_.result -ceq 'published' -or $_.result -ceq 'lost-after'})
Check ($pub.Count -eq 1) 'unique publication'
Check ($pub[0].sha -ceq $r.final) 'published SHA'
foreach($event in $patch){Check ($event.force -is [bool] -and !$event.force) 'force'}
switch($s.fault){
 'before' {Check ($patch[0].result -ceq 'lost-before' -and $patch[1].result -ceq 'published') 'before sequence'}
 'after' {Check ($patch[0].result -ceq 'lost-after') 'after sequence'}
 'compete' {Check (@($patch|Where-Object {$_.result -ceq 'conflict'}).Count -eq 1) 'conflict'}
}
foreach($name in @('ledger.json','handoff.json','repo.bundle','base.txt','final.txt')){
  $hash=(Get-FileHash -LiteralPath (Join-Path $Root $name) -Algorithm SHA256).Hash.ToLowerInvariant()
  Check ($hash -ceq $r.hashes[$name]) ('digest '+$name)
}
Check ((Get-Content -LiteralPath (Join-Path $Root 'final.txt') -Raw).Trim() -ceq $r.final) 'final'
Write-Output POWERSHELL_VERIFIED
