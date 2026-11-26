param([Parameter(Mandatory=$true)][string]$Root,[Parameter(Mandatory=$true)][string]$Contract,[Parameter(Mandatory=$true)][string]$Runner)
$ErrorActionPreference='Stop'
$c=Get-Content -Raw -LiteralPath $Contract | ConvertFrom-Json -AsHashtable
function Need($ok,[string]$message) {if(-not $ok){throw $message}}
function Canon($o) {ConvertTo-Json -InputObject $o -Depth 50 -Compress}
function Verify-Case($spec,$r,$dir) {
  Need ($r.source -ceq $c.source -and $r.scenario -ceq $spec.name -and $r.schema -eq 1 -and $r.run -ceq $env:GITHUB_RUN_ID -and $r.attempt -ceq $env:GITHUB_RUN_ATTEMPT -and $r.runner -ceq $Runner) 'identity'
  Need ($r.patches -eq $spec.patches -and $r.retries -eq $spec.retries -and $r.recovered -eq $spec.recovered) 'result counts'
  $pins=@(Get-Content -LiteralPath (Join-Path $dir 'pins.txt'))
  Need ($pins.Count -eq 3 -and $pins[0] -ceq $r.initial -and $pins[1] -ceq $r.final -and $pins[2] -ceq $r.main) 'pins'
  $history=@(Get-Content -LiteralPath (Join-Path $dir 'observed/history.txt'))
  Need ($history.Count -eq $spec.published.Count) 'commit count'
  if($history.Count -eq 0){Need ($r.initial -ceq $r.final) 'no-op ref'}else{Need ($history[-1] -ceq $r.final) 'final ref'}
  $ledger=Get-Content -Raw -LiteralPath (Join-Path $dir 'observed/0-ledger.json') | ConvertFrom-Json -AsHashtable
  $handoff=Get-Content -Raw -LiteralPath (Join-Path $dir 'observed/0-handoff.json') | ConvertFrom-Json -AsHashtable
  Need ($ledger.repository -ceq $c.repository -and $ledger.issues.Count -eq 2 -and $handoff.active.Count -eq 1 -and $handoff.active[0].issue -eq 247) 'initial fixture'
  for($i=0;$i -lt $history.Count;$i++){
    $issue=$spec.published[$i]
    $max=0
    foreach($old in $ledger.issues){$max=[Math]::Max($max,[int]($old.version.Split('.')[-1]))}
    $version='v1.0.6.'+($max+1)
    $after=Get-Content -Raw -LiteralPath (Join-Path $dir ("observed/"+($i+1)+"-ledger.json")) | ConvertFrom-Json -AsHashtable
    $h=Get-Content -Raw -LiteralPath (Join-Path $dir ("observed/"+($i+1)+"-handoff.json")) | ConvertFrom-Json -AsHashtable
    Need ($after.issues.Count -eq $ledger.issues.Count+1 -and $h.active.Count -eq $handoff.active.Count+1 -and $h.schema_version -eq 2 -and $after.repository -ceq $ledger.repository) 'delta shape'
    foreach($old in $ledger.issues){$matches=@($after.issues|Where-Object {$_.issue -eq $old.issue});Need ($matches.Count -eq 1 -and (Canon $matches[0]) -ceq (Canon $old)) 'prior ledger changed'}
    foreach($old in $handoff.active){$matches=@($h.active|Where-Object {$_.issue -eq $old.issue});Need ($matches.Count -eq 1 -and (Canon $matches[0]) -ceq (Canon $old)) 'prior active changed'}
    Need ((Canon $h.history) -ceq (Canon $handoff.history)) 'archive changed'
    $row=@($after.issues|Where-Object {$_.issue -eq $issue})
    $act=@($h.active|Where-Object {$_.issue -eq $issue})
    Need ($row.Count -eq 1 -and $act.Count -eq 1 -and $row[0].version -ceq $version -and $row[0].state -ceq 'in_progress' -and $row[0].acceptance.Count -eq 1 -and $row[0].acceptance[0] -ceq 'test') 'version allocation or intent'
    Need ($act[0].version -ceq $version -and $act[0].phase -ceq 'Worker' -and $act[0].next_action -ceq 'claim' -and $null -eq $act[0].candidate_sha -and $null -eq $act[0].pull_request -and $act[0].evidence.Count -eq 0) 'handoff scope'
    $ledger=$after;$handoff=$h
  }
}
$dirs=@(Get-ChildItem -Directory -LiteralPath $Root)
Need ($dirs.Count -eq $c.scenarios.Count) 'scenario coverage'
foreach($spec in $c.scenarios){
  $dir=Join-Path $Root $spec.name
  $r=Get-Content -Raw -LiteralPath (Join-Path $dir 'receipt.json') | ConvertFrom-Json -AsHashtable
  Verify-Case $spec $r $dir
  foreach($kind in @('wrong-source','wrong-count','wrong-attempt')){
    $bad=(Canon $r) | ConvertFrom-Json -AsHashtable
    switch($kind){'wrong-source'{$bad.source='0'*40};'wrong-count'{$bad.patches=-1};'wrong-attempt'{$bad.attempt='0'}}
    $rejected=$false
    try{Verify-Case $spec $bad $dir}catch{$rejected=$true}
    Need $rejected "accepted $kind"
  }
}
Write-Output "Verified $($c.scenarios.Count) frozen schedules and $($c.scenarios.Count*3) negative evidence cases for $Runner"
