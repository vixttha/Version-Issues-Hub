#!/usr/bin/env bash
set -euo pipefail
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
root=$(mktemp -d)
trap 'rm -rf -- "$root"' EXIT
git init --object-format=sha1 -q "$root"
git -C "$root" config core.autocrlf false
printf 'lf.txt text eol=lf\ncrlf.txt text eol=crlf\nraw.txt -text\n' > "$root/.gitattributes"
count=0
for mode in lf crlf raw unset; do
  for sample in lf crlf mixed; do
    case "$sample" in
      lf) printf 'a\nb\n' > "$root/$mode.txt";;
      crlf) printf 'a\r\nb\r\n' > "$root/$mode.txt";;
      mixed) printf 'a\r\nb\n' > "$root/$mode.txt";;
    esac
    if [[ "$mode" == lf || "$mode" == crlf ]]; then
      printf 'a\nb\n' > "$root/expected.bin"
    else
      cp "$root/$mode.txt" "$root/expected.bin"
    fi
    actual=$(git -C "$root" hash-object -w --path="$mode.txt" "$root/$mode.txt")
    expected=$(git -C "$root" hash-object --no-filters "$root/expected.bin")
    [[ "$actual" == "$expected" ]]
    git -C "$root" cat-file blob "$actual" > "$root/read.bin"
    cmp "$root/read.bin" "$root/expected.bin"
    printf 'PASS BA3-%s-%s\n' "$mode" "$sample"
    count=$((count+1))
  done
done
[[ "$count" == 12 ]]
