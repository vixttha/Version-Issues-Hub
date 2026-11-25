#!/usr/bin/env bash
set -euo pipefail
root=$(mktemp -d)
trap 'rm -rf -- "$root"' EXIT
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_AUTHOR_NAME=fixture GIT_AUTHOR_EMAIL=fixture@example.invalid GIT_COMMITTER_NAME=fixture GIT_COMMITTER_EMAIL=fixture@example.invalid
git init -q -b main "$root/repo"
printf 'original\n' > "$root/repo/state"
git -C "$root/repo" add state
git -C "$root/repo" commit -qm first
first=$(git -C "$root/repo" rev-parse HEAD)
printf 'second\n' > "$root/repo/state"
git -C "$root/repo" commit -qam second
second=$(git -C "$root/repo" rev-parse HEAD)
git -C "$root/repo" worktree add -q --detach "$root/other" "$first"
[[ $(cat "$root/other/state") == original && $(cat "$root/repo/state") == second ]]
echo 'PASS BA12-worktree'
printf 'isolated\n' > "$root/other/state"
[[ $(cat "$root/repo/state") == second && $(git -C "$root/repo" rev-parse HEAD) == "$second" ]]
echo 'PASS BA12-isolation'
git clone -q --depth 1 "file://$root/repo" "$root/shallow"
[[ $(git -C "$root/shallow" rev-parse --is-shallow-repository) == true ]]
if git -C "$root/shallow" merge-base --is-ancestor "$first" HEAD 2>/dev/null; then exit 1; fi
echo 'PASS BA12-shallow'
ln -s "$root/repo/state" "$root/alias"
[[ $(cat "$root/alias") == second ]]
rm "$root/alias"
[[ $(cat "$root/repo/state") == second ]]
echo 'PASS BA12-symlink'
printf 'hello\n' > "$root/vector"
[[ $(git -C "$root/repo" hash-object --no-filters "$root/vector") == ce013625030ba8dba906f756967f9e9ca394464a ]]
echo 'PASS BA16-git'
[[ $(sha256sum "$root/vector" | cut -d' ' -f1) == 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03 ]]
echo 'PASS BA16-digest'
: > "$root/empty"
[[ $(git -C "$root/repo" hash-object --no-filters "$root/empty") == e69de29bb2d1d6434b8b29ae775ad8c2e48c5391 ]]
echo 'PASS BA16-empty-git'
[[ $(sha256sum "$root/empty" | cut -d' ' -f1) == e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 ]]
echo 'PASS BA16-empty-digest'
