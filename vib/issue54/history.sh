#!/usr/bin/env bash
set -euo pipefail
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_AUTHOR_NAME=fixture GIT_AUTHOR_EMAIL=fixture@example.invalid GIT_COMMITTER_NAME=fixture GIT_COMMITTER_EMAIL=fixture@example.invalid
root=$(mktemp -d)
trap 'rm -rf -- "$root"' EXIT
git init --bare --object-format=sha1 -q "$root"
tree=$(git -C "$root" mktree </dev/null)
a=$(git -C "$root" commit-tree "$tree" -m root)
b=$(git -C "$root" commit-tree "$tree" -p "$a" -m left)
c=$(git -C "$root" commit-tree "$tree" -p "$a" -m right)
d=$(git -C "$root" commit-tree "$tree" -p "$b" -p "$c" -m merge)
e=$(git -C "$root" commit-tree "$tree" -m unrelated)
count=0
check(){
  local name=$1 from=$2 to=$3 expected=$4 rc=0
  git -C "$root" merge-base --is-ancestor "$from" "$to" || rc=$?
  [[ $rc == "$expected" ]]
  printf 'PASS BA4-%s\n' "$name"; count=$((count+1))
}
check root-left "$a" "$b" 0
check root-right "$a" "$c" 0
check root-merge "$a" "$d" 0
check left-merge "$b" "$d" 0
check right-merge "$c" "$d" 0
check same "$d" "$d" 0
check left-right "$b" "$c" 1
check right-left "$c" "$b" 1
check merge-left "$d" "$b" 1
check unrelated-merge "$e" "$d" 1
check merge-unrelated "$d" "$e" 1
check left-root "$b" "$a" 1
[[ $(git -C "$root" show -s --format=%P "$d") == "$b $c" ]]
printf 'PASS BA4-parent-order\n'; count=$((count+1))
[[ $(git -C "$root" merge-base "$b" "$c") == "$a" ]]
printf 'PASS BA4-common-base\n'; count=$((count+1))
[[ $count == 14 ]]
