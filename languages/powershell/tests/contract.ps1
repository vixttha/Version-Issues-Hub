param([Parameter(Mandatory)][string]$WorkDirectory)

$ErrorActionPreference = 'Stop'
$path = Join-Path $WorkDirectory 'path with [spaces].txt'
[System.IO.File]::WriteAllText($path, 'launcher-output')
$actual = Get-Content -LiteralPath $path -Raw
if ($actual -cne 'launcher-output') {
    throw "Unexpected contents at the literal output path"
}
