#!/usr/bin/env bash
set -euo pipefail
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
root=$(mktemp -d)
trap 'rm -rf -- "$root"' EXIT
repo="$root/repo"
git init --bare --object-format=sha1 -q "$repo"
git -C "$repo" config core.ignorecase false
printf A > "$root/a.bin"
printf B > "$root/b.bin"
a=$(git -C "$repo" hash-object -w --no-filters "$root/a.bin")
b=$(git -C "$repo" hash-object -w --no-filters "$root/b.bin")
count=0
long=$(printf '%0180d' 0)
names=('space name.txt' 'bracket[54].txt' '-leading.txt' 'dollar$literal.txt' 'hash#name.txt' 'comma,name.txt' 'nested/deep.txt' $'caf\u00e9.txt' $'cafe\u0301.txt' "$long.txt")
for path in "${names[@]}"; do
  git -C "$repo" read-tree --empty
  git -C "$repo" update-index --add --cacheinfo "100644,$a,$path"
  tree=$(git -C "$repo" write-tree)
  [[ $(git -C "$repo" rev-parse "$tree:$path") == "$a" ]]
  printf 'PASS BA5-path-%s\n' "$count"; count=$((count+1))
done
git -C "$repo" read-tree --empty
git -C "$repo" update-index --add --cacheinfo "100644,$a,Case.txt"
git -C "$repo" update-index --add --cacheinfo "100644,$b,case.txt"
tree=$(git -C "$repo" write-tree)
[[ $(git -C "$repo" rev-parse "$tree:Case.txt") == "$a" && $(git -C "$repo" rev-parse "$tree:case.txt") == "$b" ]]
printf 'PASS BA5-case-tree\n'; count=$((count+1))
printf A > "$root/Case.txt"
[[ ! -e "$root/case.txt" && $(cat "$root/Case.txt") == A ]]
printf 'PASS BA5-case-filesystem\n'; count=$((count+1))
[[ $count == 12 ]]
