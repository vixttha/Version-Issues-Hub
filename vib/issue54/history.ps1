$ErrorActionPreference='Stop'
$env:GIT_CONFIG_NOSYSTEM='1'
$root=Join-Path ([IO.Path]::GetTempPath()) ('vib54-history-'+[guid]::NewGuid())
[IO.Directory]::CreateDirectory($root)|Out-Null
$env:GIT_CONFIG_GLOBAL=Join-Path $root 'empty.gitconfig'
[IO.File]::WriteAllBytes($env:GIT_CONFIG_GLOBAL,[byte[]]@())
$env:GIT_AUTHOR_NAME='fixture'; $env:GIT_AUTHOR_EMAIL='fixture@example.invalid'
$env:GIT_COMMITTER_NAME='fixture'; $env:GIT_COMMITTER_EMAIL='fixture@example.invalid'
$repo=Join-Path $root 'repo [54]'
function G([string[]]$a){$r=& git -C $repo @a; if($LASTEXITCODE -ne 0){throw "git failed: $a"}; $r}
$count=0
function Check([string]$name,[string]$from,[string]$to,[int]$expected){
    & git -C $repo merge-base --is-ancestor $from $to
    if($LASTEXITCODE -ne $expected){throw "Unexpected ancestry: $name"}
    Write-Host "PASS PS4-$name"; $script:count++
}
try{
    & git init --bare --object-format=sha1 -q $repo
    if($LASTEXITCODE -ne 0){throw 'init failed'}
    $empty=Join-Path $root 'empty.bin'
    [IO.File]::WriteAllBytes($empty,[byte[]]@())
    $tree=G @('hash-object','-t','tree','-w','--no-filters',$empty)
    $a=G @('commit-tree',$tree,'-m','root')
    $b=G @('commit-tree',$tree,'-p',$a,'-m','left')
    $c=G @('commit-tree',$tree,'-p',$a,'-m','right')
    $d=G @('commit-tree',$tree,'-p',$b,'-p',$c,'-m','merge')
    $e=G @('commit-tree',$tree,'-m','unrelated')
    Check root-left $a $b 0
    Check root-right $a $c 0
    Check root-merge $a $d 0
    Check left-merge $b $d 0
    Check right-merge $c $d 0
    Check same $d $d 0
    Check left-right $b $c 1
    Check right-left $c $b 1
    Check merge-left $d $b 1
    Check unrelated-merge $e $d 1
    Check merge-unrelated $d $e 1
    Check left-root $b $a 1
    if((G @('show','-s','--format=%P',$d)) -cne "$b $c"){throw 'Wrong parents'}
    Write-Host 'PASS PS4-parent-order'; $count++
    if((G @('merge-base',$b,$c)) -cne $a){throw 'Wrong common base'}
    Write-Host 'PASS PS4-common-base'; $count++
    if($count -ne 14){throw "Wrong count $count"}
}finally{Remove-Item -LiteralPath $root -Recurse -Force}
