$ErrorActionPreference='Stop'
$env:GIT_CONFIG_NOSYSTEM='1'
$root=Join-Path ([IO.Path]::GetTempPath()) ('vib54-paths-'+[guid]::NewGuid())
[IO.Directory]::CreateDirectory($root)|Out-Null
$env:GIT_CONFIG_GLOBAL=Join-Path $root 'empty.gitconfig'
[IO.File]::WriteAllBytes($env:GIT_CONFIG_GLOBAL,[byte[]]@())
$repo=Join-Path $root 'repo'
function G([string[]]$a){$r=& git -C $repo @a; if($LASTEXITCODE -ne 0){throw "git failed: $a"}; $r}
$count=0
try{
    & git init --bare --object-format=sha1 -q $repo
    if($LASTEXITCODE -ne 0){throw 'init failed'}
    G @('config','core.ignorecase','false')|Out-Null
    $afile=Join-Path $root 'a.bin'; $bfile=Join-Path $root 'b.bin'
    [IO.File]::WriteAllBytes($afile,[byte[]]@(65))
    [IO.File]::WriteAllBytes($bfile,[byte[]]@(66))
    $a=G @('hash-object','-w','--no-filters',$afile)
    $b=G @('hash-object','-w','--no-filters',$bfile)
    $long=('0'*180)+'.txt'
    $names=@('space name.txt','bracket[54].txt','-leading.txt','dollar$literal.txt','hash#name.txt','comma,name.txt','nested/deep.txt',('caf'+[char]0xe9+'.txt'),('cafe'+[char]0x301+'.txt'),$long)
    foreach($path in $names){
        G @('read-tree','--empty')|Out-Null
        G @('update-index','--add','--cacheinfo',"100644,$a,$path")|Out-Null
        $tree=G @('write-tree')
        if((G @('rev-parse',("${tree}:$path"))) -cne $a){throw "Path mismatch $path"}
        Write-Host "PASS PS5-path-$count"; $count++
    }
    G @('read-tree','--empty')|Out-Null
    G @('update-index','--add','--cacheinfo',"100644,$a,Case.txt")|Out-Null
    G @('update-index','--add','--cacheinfo',"100644,$b,case.txt")|Out-Null
    $tree=G @('write-tree')
    if((G @('rev-parse',"${tree}:Case.txt")) -cne $a -or (G @('rev-parse',"${tree}:case.txt")) -cne $b){throw 'Git case collision'}
    Write-Host 'PASS PS5-case-tree'; $count++
    $upper=Join-Path $root 'Case.txt'; $lower=Join-Path $root 'case.txt'
    [IO.File]::WriteAllBytes($upper,[byte[]]@(65))
    if(-not [IO.File]::Exists($lower) -or [Convert]::ToHexString([IO.File]::ReadAllBytes($lower)) -cne '41'){throw 'Unexpected Windows filesystem case behavior'}
    Write-Host 'PASS PS5-case-filesystem'; $count++
    if($count -ne 12){throw "Wrong count $count"}
}finally{Remove-Item -LiteralPath $root -Recurse -Force}
