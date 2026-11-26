set -euo pipefail
cd "$GITHUB_WORKSPACE/candidate"
test "$(git rev-parse HEAD)" = "b68796db12681fe4d43b562c8647deca38fa819c"
test "$(git rev-parse 'HEAD^{tree}')" = "168b12ff613f470b664be1d0f491a2e9b101b97b"
git fsck --no-reflogs --connectivity-only
cd "$RUNNER_TEMP/independent-vib-audit"
sha256sum --binary api-boundaries.json historical-removals.json inferred-review.json candidate-graph.json > bash-sha256.txt
