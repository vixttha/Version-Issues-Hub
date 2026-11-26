$ErrorActionPreference = 'Stop'
$env:GIT_CONFIG_NOSYSTEM = '1'
$root = Join-Path ([IO.Path]::GetTempPath()) ('vib54 [bytes] ' + [guid]::NewGuid())
[IO.Directory]::CreateDirectory($root) | Out-Null
$env:GIT_CONFIG_GLOBAL = Join-Path $root 'empty.gitconfig'
[IO.File]::WriteAllBytes($env:GIT_CONFIG_GLOBAL, [byte[]]@())
$repo = Join-Path $root 'repo [54]'
$count = 0
function Git-Checked {
    param([string[]]$Arguments)
    $result = & git -C $repo @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Git failed: $($Arguments -join ' ')" }
    return $result
}
try {
    & git init --bare --object-format=sha1 -q $repo
    if ($LASTEXITCODE -ne 0) { throw 'git init failed' }
    $utf8 = [Text.UTF8Encoding]::new($false)
    $corpus = [ordered]@{
        empty=''; lf="a\nb\n"; crlf="a\r\nb\r\n"; cr="a\rb\r"; mixed="a\r\nb\nc\r";
        nofinal='abc'; whitespace=" \t a \t\n "; unicode=('caf' + [char]0x00e9 + ' ' + [char]0x6c34 + ' ' + [char]::ConvertFromUtf32(0x1f642))
    }
    # Escape sequences above are literal in PowerShell; replace only synthetic escape tokens.
    function Probe([string]$name,[string]$value) {
        $value = $value.Replace('\r', [string][char]13).Replace('\n', [string][char]10).Replace('\t', [string][char]9)
        $bytes = $utf8.GetBytes($value)
        $file = Join-Path $root 'input [54].bin'
        [IO.File]::WriteAllBytes($file,$bytes)
        $header = $utf8.GetBytes("blob $($bytes.Length)" + [char]0)
        $expected = [Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($header + $bytes))).ToLowerInvariant()
        $oid = Git-Checked @('hash-object','-w','--no-filters',$file)
        if ($oid -cne $expected) { throw "Object mismatch $name" }
        # .NET process stream is independent of PowerShell text redirection.
        $info = [Diagnostics.ProcessStartInfo]::new('git')
        $info.UseShellExecute = $false
        $info.RedirectStandardOutput = $true
        foreach ($arg in @('-C',$repo,'cat-file','blob',$oid)) { $info.ArgumentList.Add($arg) }
        $proc = [Diagnostics.Process]::Start($info)
        $mem = [IO.MemoryStream]::new()
        try {
            $proc.StandardOutput.BaseStream.CopyTo($mem)
            $proc.WaitForExit()
            if ($proc.ExitCode -ne 0 -or [Convert]::ToHexString($mem.ToArray()) -cne [Convert]::ToHexString($bytes)) { throw "Byte mismatch $name" }
        } finally { $mem.Dispose(); $proc.Dispose() }
        Write-Host "PASS PS-$name $($bytes.Length) $oid"
    }
    foreach ($entry in $corpus.GetEnumerator()) { Probe $entry.Key $entry.Value; $count++ }
    foreach ($cfg in @('false','true','input')) {
        Git-Checked @('config','core.autocrlf',$cfg) | Out-Null
        Probe "autocrlf-$cfg" 'old guide\n'
        $count++
    }
    $file = Join-Path $root 'input [54].bin'
    $oid = Git-Checked @('hash-object','-w','--no-filters',$file)
    foreach ($mode in @('100644','100755','120000')) {
        Git-Checked @('read-tree','--empty') | Out-Null
        Git-Checked @('update-index','--add','--cacheinfo',"$mode,$oid,space [54].txt") | Out-Null
        $tree = Git-Checked @('write-tree')
        $row = Git-Checked @('ls-tree',$tree)
        if (($row -split ' ')[0] -cne $mode) { throw "Mode mismatch $mode" }
        Write-Host "PASS PS-mode-$mode"
        $count++
    }
    $bad = & git -C $repo cat-file -t invalid 2>$null
    if ($LASTEXITCODE -eq 0) { throw 'Expected nonzero Git status' }
    Write-Host 'PASS PS-exit-status'
    $count++
    if ($count -ne 15) { throw "Expected 15 checks, got $count" }
    Write-Host "VIB54_POWERSHELL_COUNT=$count"
} finally { Remove-Item -LiteralPath $root -Recurse -Force }
