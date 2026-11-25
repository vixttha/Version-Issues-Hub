$ErrorActionPreference = 'Stop'
$env:GIT_CONFIG_NOSYSTEM='1'
$root=Join-Path ([IO.Path]::GetTempPath()) ('vib54 [faults] '+[guid]::NewGuid())
[IO.Directory]::CreateDirectory($root)|Out-Null
$env:GIT_CONFIG_GLOBAL=Join-Path $root 'empty.gitconfig'
[IO.File]::WriteAllBytes($env:GIT_CONFIG_GLOBAL,[byte[]]@())
$env:GIT_AUTHOR_NAME='fixture'; $env:GIT_AUTHOR_EMAIL='fixture@example.invalid'
$env:GIT_COMMITTER_NAME='fixture'; $env:GIT_COMMITTER_EMAIL='fixture@example.invalid'
$repo=Join-Path $root 'repo [54]'
$count=0
function Pass([string]$name){Write-Host "PASS PS2-$name"; $script:count++}
function G([string[]]$a){$r=& git -C $repo @a; if($LASTEXITCODE -ne 0){throw "git failed: $a"}; $r}
function Reject([string[]]$a){$null=& git -C $repo @a 2>$null; if($LASTEXITCODE -eq 0){throw "Unexpected success: $a"}}
function Same([string]$actual,[string]$expected){if($actual -cne $expected){throw "Mismatch: $actual vs $expected"}}
try {
    & git init --bare --object-format=sha1 -q $repo
    if($LASTEXITCODE -ne 0){throw 'init failed'}
    $empty=Join-Path $root 'empty-tree.bin'
    [IO.File]::WriteAllBytes($empty,[byte[]]@())
    $tree=G @('hash-object','-t','tree','-w','--no-filters',$empty)
    $a=G @('commit-tree',$tree,'-m','a')
    $b=G @('commit-tree',$tree,'-p',$a,'-m','b')
    $c=G @('commit-tree',$tree,'-p',$a,'-m','c')
    $ref='refs/heads/fixture'; $zero='0'*40
    G @('update-ref',$ref,$a,$zero)|Out-Null; Same (G @('rev-parse',$ref)) $a; Pass create
    G @('update-ref',$ref,$b,$a)|Out-Null; Same (G @('rev-parse',$ref)) $b; Pass advance
    Reject @('update-ref',$ref,$c,$a); Same (G @('rev-parse',$ref)) $b; Pass stale-write
    Reject @('update-ref','-d',$ref,$a); Same (G @('rev-parse',$ref)) $b; Pass stale-delete
    Reject @('update-ref',$ref,$c,$zero); Same (G @('rev-parse',$ref)) $b; Pass occupied-create
    G @('update-ref','-d',$ref,$b)|Out-Null; Reject @('rev-parse','--verify',$ref); Pass correct-delete
    foreach($invalid in @('refs/heads/a..b','refs/heads/a b','refs/heads/a.lock','refs/heads/a~b')){
        Reject @('check-ref-format',$invalid); Pass "invalid-ref-$count"
    }
    $PSNativeCommandArgumentPassing='Standard'
    foreach($arg in @('','a b','a[b]','a"b',"a'b",'$HOME','-x','a\b')){
        $actual=& python -c 'import sys; print(sys.argv[1].encode().hex())' $arg
        if($LASTEXITCODE -ne 0){throw "argv failed $count"}
        $expect=[Convert]::ToHexString([Text.Encoding]::UTF8.GetBytes($arg)).ToLowerInvariant()
        Same ([string]$actual) $expect; Pass "argv-$count"
    }
    $file=Join-Path $root 'lock [54].txt'
    [IO.File]::WriteAllText($file,'fixture')
    $handle=[IO.File]::Open($file,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    try{
        $blocked=$false
        try{[IO.File]::ReadAllBytes($file)|Out-Null}catch [IO.IOException]{$blocked=$true}
        if(-not $blocked){throw 'Exclusive lock unexpectedly bypassed'}
    }finally{$handle.Dispose()}
    Same ([IO.File]::ReadAllText($file)) 'fixture'; Pass exclusive-lock
    if($count -ne 19){throw "Wrong count $count"}
}finally{Remove-Item -LiteralPath $root -Recurse -Force}
