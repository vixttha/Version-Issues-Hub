$ErrorActionPreference='Stop'
$root=Join-Path ([IO.Path]::GetTempPath()) ('vib-advanced-'+[guid]::NewGuid())
[IO.Directory]::CreateDirectory($root)|Out-Null
$repo=Join-Path $root 'repo'
$env:GIT_CONFIG_NOSYSTEM='1'
$env:GIT_CONFIG_GLOBAL=Join-Path $root 'empty.config'
[IO.File]::WriteAllBytes($env:GIT_CONFIG_GLOBAL,[byte[]]@())
$env:GIT_AUTHOR_NAME='fixture';$env:GIT_AUTHOR_EMAIL='fixture@example.invalid'
$env:GIT_COMMITTER_NAME='fixture';$env:GIT_COMMITTER_EMAIL='fixture@example.invalid'
function G([string[]]$a){$r=& git -C $repo @a;if($LASTEXITCODE -ne 0){throw "git failed $a"};$r}
try{
    & git init -q -b main $repo
    if($LASTEXITCODE -ne 0){throw 'init'}
    $state=Join-Path $repo 'state'
    [IO.File]::WriteAllText($state,"original"+[char]10)
    G @('add','state');G @('commit','-qm','first')
    $first=G @('rev-parse','HEAD')
    [IO.File]::WriteAllText($state,"second"+[char]10)
    G @('commit','-qam','second')
    $second=G @('rev-parse','HEAD')
    $other=Join-Path $root 'other'
    G @('worktree','add','-q','--detach',$other,$first)
    if((Get-Content -LiteralPath (Join-Path $other 'state') -Raw).Trim() -cne 'original'){throw 'worktree'}
    Write-Host 'PASS PS12-worktree'
    [IO.File]::WriteAllText((Join-Path $other 'state'),'isolated')
    if((Get-Content -LiteralPath $state -Raw).Trim() -cne 'second' -or (G @('rev-parse','HEAD')) -cne $second){throw 'isolation'}
    Write-Host 'PASS PS12-isolation'
    $junction=Join-Path $root 'alias'
    New-Item -ItemType Junction -Path $junction -Target $repo|Out-Null
    if((Get-Content -LiteralPath (Join-Path $junction 'state') -Raw).Trim() -cne 'second'){throw 'junction'}
    [IO.Directory]::Delete($junction)
    if(!(Test-Path -LiteralPath $state)){throw 'junction removed target'}
    Write-Host 'PASS PS12-junction'
    $lock=[IO.File]::Open($state,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::None)
    try{
        $denied=$false
        try{[IO.File]::WriteAllText($state,'bad')}catch [IO.IOException]{$denied=$true}
        if(!$denied){throw 'lock was ignored'}
    }finally{$lock.Dispose()}
    if((Get-Content -LiteralPath $state -Raw).Trim() -cne 'second'){throw 'locked state changed'}
    Write-Host 'PASS PS12-lock'
    $vector=Join-Path $root 'vector'
    [IO.File]::WriteAllBytes($vector,[Convert]::FromHexString('68656c6c6f0a'))
    if((G @('hash-object','--no-filters',$vector)) -cne 'ce013625030ba8dba906f756967f9e9ca394464a'){throw 'git digest'}
    Write-Host 'PASS PS16-git'
    if((Get-FileHash -LiteralPath $vector -Algorithm SHA256).Hash.ToLowerInvariant() -cne '5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03'){throw 'sha'}
    Write-Host 'PASS PS16-digest'
    [IO.File]::WriteAllBytes($vector,[byte[]]@())
    if((G @('hash-object','--no-filters',$vector)) -cne 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391'){throw 'empty git'}
    Write-Host 'PASS PS16-empty-git'
    if((Get-FileHash -LiteralPath $vector -Algorithm SHA256).Hash.ToLowerInvariant() -cne 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'){throw 'empty sha'}
    Write-Host 'PASS PS16-empty-digest'
}finally{Remove-Item -LiteralPath $root -Recurse -Force}
