#!/usr/bin/env bash
set -euo pipefail
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_AUTHOR_NAME=fixture GIT_AUTHOR_EMAIL=fixture@example.invalid GIT_COMMITTER_NAME=fixture GIT_COMMITTER_EMAIL=fixture@example.invalid
root=$(mktemp -d)
trap 'rm -rf -- "$root"' EXIT
repo="$root/repo [54]"
git init --bare --object-format=sha1 -q "$repo"
count=0
pass(){ printf 'PASS BA2-%s\n' "$1"; count=$((count+1)); }
tree=$(git -C "$repo" mktree </dev/null)
a=$(git -C "$repo" commit-tree "$tree" -m a)
b=$(git -C "$repo" commit-tree "$tree" -p "$a" -m b)
c=$(git -C "$repo" commit-tree "$tree" -p "$a" -m c)
ref=refs/heads/fixture
zero=0000000000000000000000000000000000000000
git -C "$repo" update-ref "$ref" "$a" "$zero"
[[ $(git -C "$repo" rev-parse "$ref") == "$a" ]]; pass create
git -C "$repo" update-ref "$ref" "$b" "$a"
[[ $(git -C "$repo" rev-parse "$ref") == "$b" ]]; pass advance
if git -C "$repo" update-ref "$ref" "$c" "$a" 2>/dev/null; then exit 1; fi
[[ $(git -C "$repo" rev-parse "$ref") == "$b" ]]; pass stale-write
if git -C "$repo" update-ref -d "$ref" "$a" 2>/dev/null; then exit 1; fi
[[ $(git -C "$repo" rev-parse "$ref") == "$b" ]]; pass stale-delete
if git -C "$repo" update-ref "$ref" "$c" "$zero" 2>/dev/null; then exit 1; fi
[[ $(git -C "$repo" rev-parse "$ref") == "$b" ]]; pass occupied-create
git -C "$repo" update-ref -d "$ref" "$b"
if git -C "$repo" rev-parse --verify "$ref" >/dev/null 2>&1; then exit 1; fi; pass correct-delete
for invalid in 'refs/heads/a..b' 'refs/heads/a b' 'refs/heads/a.lock' 'refs/heads/a~b'; do
  if git check-ref-format "$invalid"; then exit 1; fi
  pass "invalid-ref-$count"
done
for arg in '' 'a b' 'a[b]' 'a"b' "a'b" '$HOME' '-x' 'a\b'; do
  result=$(python -c 'import sys; print(sys.argv[1].encode().hex())' "$arg")
  expect=$(printf '%s' "$arg" | od -An -tx1 | tr -d ' \n')
  [[ "$result" == "$expect" ]]; pass "argv-$count"
done
if (false | cat >/dev/null); then exit 1; fi; pass pipefail
[[ "$count" == 19 ]]
