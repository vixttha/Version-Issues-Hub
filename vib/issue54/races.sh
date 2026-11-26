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
ref=refs/heads/fixture
count=0
pass(){ printf 'PASS BA7-%s\n' "$1"; count=$((count+1)); }
for round in 1 2 3 4; do
  git -C "$root" update-ref "$ref" "$a"
  git -C "$root" update-ref "$ref" "$b" "$a" >"$root/left" 2>&1 & l=$!
  git -C "$root" update-ref "$ref" "$c" "$a" >"$root/right" 2>&1 & r=$!
  lc=0; rc=0; wait "$l" || lc=$?; wait "$r" || rc=$?
  actual=$(git -C "$root" rev-parse "$ref")
  if [[ $lc == 0 ]]; then [[ $rc != 0 && $actual == "$b" ]]; else [[ $rc == 0 && $actual == "$c" ]]; fi
  pass "race-$round"
done
git -C "$root" update-ref "$ref" "$a"
: > "$root/$ref.lock"
if git -C "$root" update-ref "$ref" "$b" "$a" 2>/dev/null; then exit 1; fi
[[ $(git -C "$root" rev-parse "$ref") == "$a" ]]
pass locked-ref
rm -- "$root/$ref.lock"
git -C "$root" update-ref "$ref" "$b" "$a"
[[ $(git -C "$root" rev-parse "$ref") == "$b" ]]
pass recovered-lock
git -C "$root" update-ref refs/heads/archive "$b" "$(printf '%040d' 0)"
git -C "$root" update-ref -d "$ref" "$b"
git -C "$root" update-ref "$ref" "$(git -C "$root" rev-parse refs/heads/archive)" "$(printf '%040d' 0)"
[[ $(git -C "$root" rev-parse "$ref") == "$b" ]]
pass archive-restore
git -C "$root" fsck --full --no-reflogs >"$root/fsck" 2>&1
pass object-integrity
[[ $count == 8 ]]
