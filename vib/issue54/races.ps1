$ErrorActionPreference='Stop'
$env:GIT_CONFIG_NOSYSTEM='1'
$root=Join-Path ([IO.Path]::GetTempPath()) ('vib54-race-'+[guid]::NewGuid())
[IO.Directory]::CreateDirectory($root)|Out-Null
$env:GIT_CONFIG_GLOBAL=Join-Path $root 'empty.gitconfig'
[IO.File]::WriteAllBytes($env:GIT_CONFIG_GLOBAL,[byte[]]@())
$env:GIT_AUTHOR_NAME='fixture';$env:GIT_AUTHOR_EMAIL='fixture@example.invalid'
$env:GIT_COMMITTER_NAME='fixture';$env:GIT_COMMITTER_EMAIL='fixture@example.invalid'
$repo=Join-Path $root 'repo [54]'
function G([string[]]$a){$r=& git -C $repo @a; if($LASTEXITCODE -ne 0){throw "git failed: $a"}; $r}
function Start-Git([string[]]$argsList){
    $i=[Diagnostics.ProcessStartInfo]::new('git')
    $i.UseShellExecute=$false;$i.RedirectStandardOutput=$true;$i.RedirectStandardError=$true
    foreach($arg in (@('-C',$repo)+$argsList)){$i.ArgumentList.Add($arg)}
    [Diagnostics.Process]::Start($i)
}
function Finish-Git($p){
    try{
        $null=$p.StandardOutput.ReadToEnd();$null=$p.StandardError.ReadToEnd()
        $p.WaitForExit();$p.ExitCode
    }finally{$p.Dispose()}
}
function Pass([string]$name){Write-Host "PASS PS7-$name";$script:count++}
$count=0
try{
    & git init --bare --object-format=sha1 -q $repo
    if($LASTEXITCODE -ne 0){throw 'init failed'}
    $empty=Join-Path $root 'empty.bin';[IO.File]::WriteAllBytes($empty,[byte[]]@())
    $tree=G @('hash-object','-t','tree','-w','--no-filters',$empty)
    $a=G @('commit-tree',$tree,'-m','root')
    $b=G @('commit-tree',$tree,'-p',$a,'-m','left')
    $c=G @('commit-tree',$tree,'-p',$a,'-m','right')
    $ref='refs/heads/fixture'
    foreach($round in 1..4){
        G @('update-ref',$ref,$a)|Out-Null
        $l=Start-Git @('update-ref',$ref,$b,$a)
        $r=Start-Git @('update-ref',$ref,$c,$a)
        $lc=Finish-Git $l;$rc=Finish-Git $r
        $actual=G @('rev-parse',$ref)
        if($lc -eq 0){if($rc -eq 0 -or $actual -cne $b){throw 'Race left'}}
        else{if($rc -ne 0 -or $actual -cne $c){throw 'Race right'}}
        Pass "race-$round"
    }
    G @('update-ref',$ref,$a)|Out-Null
    $lock=Join-Path $repo "$ref.lock"
    [IO.File]::WriteAllBytes($lock,[byte[]]@())
    $rc=Finish-Git (Start-Git @('update-ref',$ref,$b,$a))
    if($rc -eq 0 -or (G @('rev-parse',$ref)) -cne $a){throw 'Locked ref mutated'}
    Pass locked-ref
    Remove-Item -LiteralPath $lock
    G @('update-ref',$ref,$b,$a)|Out-Null
    if((G @('rev-parse',$ref)) -cne $b){throw 'Lock recovery failed'}
    Pass recovered-lock
    $zero='0'*40
    G @('update-ref','refs/heads/archive',$b,$zero)|Out-Null
    G @('update-ref','-d',$ref,$b)|Out-Null
    G @('update-ref',$ref,(G @('rev-parse','refs/heads/archive')),$zero)|Out-Null
    if((G @('rev-parse',$ref)) -cne $b){throw 'Restore failed'}
    Pass archive-restore
    G @('fsck','--full','--no-reflogs')|Out-Null
    Pass object-integrity
    if($count -ne 8){throw "Wrong count $count"}
}finally{Remove-Item -LiteralPath $root -Recurse -Force}
