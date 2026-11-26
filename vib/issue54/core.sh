#!/usr/bin/env bash
set -euo pipefail
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
root=$(mktemp -d)
trap 'rm -rf -- "$root"' EXIT
repo="$root/repo [54]"
git init --bare --object-format=sha1 -q "$repo"
count=0
probe() {
  local name=$1 data=$2 expected actual size file="$root/input [54].bin"
  printf '%s' "$data" > "$file"
  size=$(wc -c < "$file" | tr -d '[:space:]')
  expected=$( { printf 'blob %s\0' "$size"; cat "$file"; } | sha1sum | cut -d' ' -f1)
  actual=$(git -C "$repo" hash-object -w --no-filters "$file")
  [[ "$expected" == "$actual" ]]
  git -C "$repo" cat-file blob "$actual" > "$root/read.bin"
  cmp "$file" "$root/read.bin"
  [[ $(sha256sum "$file" | cut -d' ' -f1) == $(sha256sum "$root/read.bin" | cut -d' ' -f1) ]]
  printf 'PASS BA-%s %s %s\n' "$name" "$size" "$actual"
  count=$((count+1))
}
probe empty ''
probe lf $'a\nb\n'
probe crlf $'a\r\nb\r\n'
probe cr $'a\rb\r'
probe mixed $'a\r\nb\nc\r'
probe nofinal 'abc'
probe whitespace $' \t a \t\n '
probe unicode $'caf\u00e9 \u6c34 \U0001f642\n'
for cfg in false true input; do
  git -C "$repo" config core.autocrlf "$cfg"
  probe "autocrlf-$cfg" $'old guide\n'
done
oid=$(git -C "$repo" hash-object -w --stdin <<< 'fixture')
for mode in 100644 100755 120000; do
  git -C "$repo" read-tree --empty
  git -C "$repo" update-index --add --cacheinfo "$mode,$oid,space [54].txt"
  tree=$(git -C "$repo" write-tree)
  [[ $(git -C "$repo" ls-tree "$tree" | cut -d' ' -f1) == "$mode" ]]
  printf 'PASS BA-mode-%s\n' "$mode"
  count=$((count+1))
done
if git -C "$repo" cat-file blob invalid >"$root/stdout" 2>"$root/stderr"; then exit 1; fi
[[ ! -s "$root/stdout" && -s "$root/stderr" ]]
printf 'PASS BA-exit-streams\n'
count=$((count+1))
[[ "$count" == 15 ]]
printf 'VIB54_BASH_COUNT=%s\n' "$count"
