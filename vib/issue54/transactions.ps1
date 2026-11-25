$ErrorActionPreference='Stop'
$env:GIT_CONFIG_NOSYSTEM='1'
$root=Join-Path ([IO.Path]::GetTempPath()) ('vib54-txn-'+[guid]::NewGuid())
[IO.Directory]::CreateDirectory($root)|Out-Null
$env:GIT_CONFIG_GLOBAL=Join-Path $root 'empty.gitconfig'
[IO.File]::WriteAllBytes($env:GIT_CONFIG_GLOBAL,[byte[]]@())
$env:GIT_AUTHOR_NAME='fixture'; $env:GIT_AUTHOR_EMAIL='fixture@example.invalid'
$env:GIT_COMMITTER_NAME='fixture'; $env:GIT_COMMITTER_EMAIL='fixture@example.invalid'
$repo=Join-Path $root 'repo [54]'
function G([string[]]$a){$r=& git -C $repo @a; if($LASTEXITCODE -ne 0){throw "git failed: $a"}; $r}
function Txn([string[]]$lines,[bool]$success=$true){
    $info=[Diagnostics.ProcessStartInfo]::new('git')
    $info.UseShellExecute=$false; $info.RedirectStandardInput=$true
    $info.RedirectStandardOutput=$true; $info.RedirectStandardError=$true
    foreach($arg in @('-C',$repo,'update-ref','--stdin')){$info.ArgumentList.Add($arg)}
    $p=[Diagnostics.Process]::Start($info)
    try{
        $raw=[Text.Encoding]::ASCII.GetBytes(($lines -join [char]10)+[char]10)
        $p.StandardInput.BaseStream.Write($raw,0,$raw.Length)
        $p.StandardInput.Close()
        $stdout=$p.StandardOutput.ReadToEnd(); $stderr=$p.StandardError.ReadToEnd()
        $p.WaitForExit()
        if(($p.ExitCode -eq 0) -ne $success){throw "Transaction unexpected result: $stdout $stderr"}
    }finally{$p.Dispose()}
}
function Same([string]$ref,[string]$sha){if((G @('rev-parse',$ref)) -cne $sha){throw "Wrong ref $ref"}}
function Absent([string]$ref){& git -C $repo show-ref --verify --quiet $ref; if($LASTEXITCODE -ne 1){throw "Expected absent ref $ref"}}
function Pass([string]$name){Write-Host "PASS PS6-$name"; $script:count++}
$count=0
try{
    & git init --bare --object-format=sha1 -q $repo
    if($LASTEXITCODE -ne 0){throw 'init failed'}
    $empty=Join-Path $root 'empty.bin'; [IO.File]::WriteAllBytes($empty,[byte[]]@())
    $tree=G @('hash-object','-t','tree','-w','--no-filters',$empty)
    $a=G @('commit-tree',$tree,'-m','root')
    $b=G @('commit-tree',$tree,'-p',$a,'-m','left')
    $c=G @('commit-tree',$tree,'-p',$a,'-m','right')
    $x='refs/heads/fixture-x'; $y='refs/heads/fixture-y'
    Txn @('start',"create $x $a","create $y $a",'prepare','commit')
    Same $x $a; Same $y $a; Pass create-both
    Txn @('start',"update $x $b $a","update $y $c $a",'prepare','abort')
    Same $x $a; Same $y $a; Pass abort-both
    Txn @('start',"update $x $b $a","update $y $c $b",'prepare','commit') $false
    Same $x $a; Same $y $a; Pass stale-second
    Txn @('start',"update $x $b $c","update $y $c $a",'prepare','commit') $false
    Same $x $a; Same $y $a; Pass stale-first
    Txn @('start',"update $x $b $a","update $x $c $a",'prepare','commit') $false
    Same $x $a; Same $y $a; Pass duplicate-target
    Txn @('start',"update $x $b $a","verify $y $c",'prepare','commit') $false
    Same $x $a; Same $y $a; Pass wrong-verify
    Txn @('start',"update $x $b $a","verify $y $a",'prepare','commit')
    Same $x $b; Same $y $a; Pass verify-then-write
    Txn @('start',"delete $x $a","update $y $c $a",'prepare','commit') $false
    Same $x $b; Same $y $a; Pass stale-delete
    Txn @('start',"delete $x $b","update $y $c $a",'prepare','abort')
    Same $x $b; Same $y $a; Pass abort-delete
    Txn @('start',"delete $x $b","update $y $c $a",'prepare','commit')
    Absent $x; Same $y $c; Pass delete-and-update
    Txn @('start',"create $x $a","create $y $b",'prepare','commit') $false
    Absent $x; Same $y $c; Pass occupied-create
    Txn @('start',"create $x $a","delete $y $c",'prepare','commit')
    Same $x $a; Absent $y; Pass locks-released
    if($count -ne 12){throw "Wrong count $count"}
}finally{Remove-Item -LiteralPath $root -Recurse -Force}
