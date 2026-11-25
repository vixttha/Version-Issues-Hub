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
x=refs/heads/fixture-x; y=refs/heads/fixture-y
count=0
pass(){ printf 'PASS BA6-%s\n' "$1"; count=$((count+1)); }
txn(){ printf '%s\n' "$@" | git -C "$root" update-ref --stdin; }
reject(){ if txn "$@" >"$root/out" 2>"$root/err"; then return 1; fi; }
same(){ [[ $(git -C "$root" rev-parse "$1") == "$2" ]]; }
absent(){ ! git -C "$root" show-ref --verify --quiet "$1"; }
txn start "create $x $a" "create $y $a" prepare commit
same "$x" "$a"; same "$y" "$a"; pass create-both
txn start "update $x $b $a" "update $y $c $a" prepare abort
same "$x" "$a"; same "$y" "$a"; pass abort-both
reject start "update $x $b $a" "update $y $c $b" prepare commit
same "$x" "$a"; same "$y" "$a"; pass stale-second
reject start "update $x $b $c" "update $y $c $a" prepare commit
same "$x" "$a"; same "$y" "$a"; pass stale-first
reject start "update $x $b $a" "update $x $c $a" prepare commit
same "$x" "$a"; same "$y" "$a"; pass duplicate-target
reject start "update $x $b $a" "verify $y $c" prepare commit
same "$x" "$a"; same "$y" "$a"; pass wrong-verify
txn start "update $x $b $a" "verify $y $a" prepare commit
same "$x" "$b"; same "$y" "$a"; pass verify-then-write
reject start "delete $x $a" "update $y $c $a" prepare commit
same "$x" "$b"; same "$y" "$a"; pass stale-delete
txn start "delete $x $b" "update $y $c $a" prepare abort
same "$x" "$b"; same "$y" "$a"; pass abort-delete
txn start "delete $x $b" "update $y $c $a" prepare commit
absent "$x"; same "$y" "$c"; pass delete-and-update
reject start "create $x $a" "create $y $b" prepare commit
absent "$x"; same "$y" "$c"; pass occupied-create
txn start "create $x $a" "delete $y $c" prepare commit
same "$x" "$a"; absent "$y"; pass locks-released
[[ $count == 12 ]]
