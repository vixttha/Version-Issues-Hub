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
Check ($row.acceptance.Count -eq $s.criteria.Count) 'criteria count'
for($i=0;$i -lt $s.criteria.Count;$i++){Check ($row.acceptance[$i] -ceq $s.criteria[$i]) 'criteria value'}
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
 {$_ -in @('compete-tree','compete-commit')} {Check (@($patch|Where-Object {$_.result -ceq 'conflict'}).Count -eq 1) 'early conflict'}

}
$recover=@($r.observations|Where-Object {$_.kind -ceq 'recovery-read'})
Check ($recover.Count -eq 1) 'recovery read'
$expectedRecoveryRef=if($s.fault -in @('before','tree-before','tree-after','commit-before','commit-after')){(Get-Content -LiteralPath (Join-Path $Root 'base.txt') -Raw).Trim()}else{$r.final}
Check ($recover[0].sha -ceq $expectedRecoveryRef) 'recovery revision'
if($s.fault -in @('tree-before','tree-after','commit-before','commit-after','compete-tree','compete-commit','stale','unexpected')){
  Check (@($r.observations|Where-Object {$_.kind -ceq $s.fault}).Count -eq 1) 'fault marker'
}
if($s.fault -eq 'stale'){
  $old=@($r.observations|Where-Object {$_.kind -ceq 'stale'})[0].sha
  $idx=[Array]::IndexOf([object[]]$r.observations,@($r.observations|Where-Object {$_.kind -ceq 'stale'})[0])
  Check ($r.observations[$idx+1].sha -ceq $old -and $r.observations[$idx+2].sha -ceq $old -and $r.observations[$idx+3].sha -ceq $r.final) 'stale readback sequence'
}
if($s.fault -eq 'unexpected'){Check (@($r.observations|Where-Object {$_.kind -ceq 'read-ref' -and $_.sha -ceq ('f'*40)}).Count -eq 1) 'unexpected readback'}
foreach($name in @('ledger.json','handoff.json','repo.bundle','base.txt','final.txt')){
  $hash=(Get-FileHash -LiteralPath (Join-Path $Root $name) -Algorithm SHA256).Hash.ToLowerInvariant()
  Check ($hash -ceq $r.hashes[$name]) ('digest '+$name)
}
Check ((Get-Content -LiteralPath (Join-Path $Root 'final.txt') -Raw).Trim() -ceq $r.final) 'final'
Write-Output POWERSHELL_VERIFIED
