set -euo pipefail
export LC_ALL=C
case "$1" in
publish)
  old=$(git -C "$2" rev-parse "refs/heads/$3")
  git -C "$2" merge-base --is-ancestor "$old" "$4" || exit 23
  git -C "$2" update-ref "refs/heads/$3" "$4" "$old"
  ;;
audit)
  folder=$2; branch=$3
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  git clone --bare --quiet "$folder/repo.bundle" "$tmp/repo"
  base=$(cat "$folder/base.txt"); final=$(cat "$folder/final.txt")
  [[ $(git -C "$tmp/repo" rev-parse refs/heads/main) == "$base" ]]
  [[ $(git -C "$tmp/repo" rev-parse "refs/heads/$branch") == "$final" ]]
  [[ $(git -C "$tmp/repo" show -s --format=%P "$final") == "$base" ]]
  git -C "$tmp/repo" cat-file blob "$final:ledger/issue-versions.json" > "$tmp/ledger"
  git -C "$tmp/repo" cat-file blob "$final:ledger/handoff.json" > "$tmp/handoff"
  cmp "$tmp/ledger" "$folder/ledger.json"
  cmp "$tmp/handoff" "$folder/handoff.json"
  git -C "$tmp/repo" fsck --strict --no-reflogs >/dev/null
  echo BASH_VERIFIED
  ;;
*) exit 9;;
esac
