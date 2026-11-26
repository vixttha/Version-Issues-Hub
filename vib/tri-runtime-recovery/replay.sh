#!/usr/bin/env bash
# Independent Git verification; no product imports and no external remote.
set -euo pipefail
root="$1"
for dir in "$root"/*/; do
  [[ -f "$dir/receipt.json" && -f "$dir/objects.bundle" && -f "$dir/pins.txt" ]] || exit 20
  (
    cd "$dir"
    mapfile -t pins < pins.txt
    [[ ${#pins[@]} == 3 ]] || exit 21
    for sha in "${pins[@]}"; do [[ "$sha" =~ ^[0-9a-f]{40}$ ]] || exit 22; done
    initial="${pins[0]}"; final="${pins[1]}"; main="${pins[2]}"
    [[ ! -e audit.git && ! -e observed ]] || exit 23
    git clone --bare --quiet objects.bundle audit.git
    git -C audit.git fsck --no-reflogs --connectivity-only
    [[ "$(git -C audit.git rev-parse refs/heads/Version-Issues-Hub)" == "$final" ]]
    [[ "$(git -C audit.git rev-parse refs/heads/main)" == "$main" ]]
    git -C audit.git merge-base --is-ancestor "$initial" "$final"
    mkdir observed
    git -C audit.git rev-list --reverse "$initial..$final" > observed/history.txt
    parent="$initial"; i=0
    snapshot() {
      git -C audit.git cat-file blob "$1:ledger/issue-versions.json" > "observed/$2-ledger.json"
      git -C audit.git cat-file blob "$1:ledger/handoff.json" > "observed/$2-handoff.json"
    }
    snapshot "$initial" 0
    while IFS= read -r sha; do
      [[ "$(git -C audit.git show -s --format=%P "$sha")" == "$parent" ]]
      [[ "$(git -C audit.git diff --name-only "$parent" "$sha" | LC_ALL=C sort)" == $'ledger/handoff.json\nledger/issue-versions.json' ]]
      i=$((i+1)); snapshot "$sha" "$i"; parent="$sha"
    done < observed/history.txt
    [[ "$parent" == "$final" ]]
    rm -rf audit.git
  )
done
