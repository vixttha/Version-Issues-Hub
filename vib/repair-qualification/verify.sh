#!/usr/bin/env bash
set -euo pipefail
test "$(git -C before rev-parse HEAD)" = 'b68796db12681fe4d43b562c8647deca38fa819c'
test "$(git -C after rev-parse HEAD)" = 'ab03646daf4fee23e9857bd2ccbb4fd759891611'
test -z "$(git -C before status --porcelain)"
test -z "$(git -C after status --porcelain)"
(cd "$RUNNER_TEMP/itqs" && sha256sum before/report.json after/report.json > SHA256SUMS && sha256sum -c SHA256SUMS)
