$ErrorActionPreference='Stop'
$env:GIT_CONFIG_NOSYSTEM='1'
$root=Join-Path ([IO.Path]::GetTempPath()) ('vib54-attrs-'+[guid]::NewGuid())
[IO.Directory]::CreateDirectory($root)|Out-Null
$env:GIT_CONFIG_GLOBAL=Join-Path $root 'empty.gitconfig'
[IO.File]::WriteAllBytes($env:GIT_CONFIG_GLOBAL,[byte[]]@())
function G([string[]]$a){$r=& git -C $root @a; if($LASTEXITCODE -ne 0){throw "git failed: $a"}; $r}
$count=0
try{
    G @('init','--object-format=sha1','-q')|Out-Null
    G @('config','core.autocrlf','false')|Out-Null
    $utf8=[Text.UTF8Encoding]::new($false)
    $lf=[char]10; $cr=[char]13
    [IO.File]::WriteAllBytes((Join-Path $root '.gitattributes'),$utf8.GetBytes("lf.txt text eol=lf${lf}crlf.txt text eol=crlf${lf}raw.txt -text${lf}"))
    $samples=[ordered]@{lf="a${lf}b${lf}";crlf="a${cr}${lf}b${cr}${lf}";mixed="a${cr}${lf}b${lf}"}
    foreach($mode in @('lf','crlf','raw','unset')){
        foreach($sample in $samples.Keys){
            $file=Join-Path $root "$mode.txt"
            $bytes=$utf8.GetBytes($samples[$sample])
            [IO.File]::WriteAllBytes($file,$bytes)
            $expectedBytes=if($mode -in @('lf','crlf')){$utf8.GetBytes("a${lf}b${lf}")}else{$bytes}
            $expectedBytes=[byte[]]$expectedBytes
            $header=$utf8.GetBytes("blob $($expectedBytes.Length)"+[char]0)
            $expected=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($header+$expectedBytes))).ToLowerInvariant()
            $actual=G @('hash-object','-w',"--path=$mode.txt",$file)
            if($actual -cne $expected){throw "Git filter mismatch $mode $sample"}
            Write-Host "PASS PS3-$mode-$sample"
            $count++
        }
    }
    if($count -ne 12){throw "Wrong count $count"}
}finally{Remove-Item -LiteralPath $root -Recurse -Force}
