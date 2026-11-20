# README v0.0.1 changelog

Initial approved README. Source commit `a8c5656929be2fcb30d9d3818245aa7501b0bf59` in PR #62.

## Added

- A game overview and the current first-playable scope.
- Local setup with Git, Node.js 24.12.0 or later, Bun 1.4.4, and a WebGL 2 browser.
- A Breeze guest walkthrough covering Rowan, the Frost solo skirmish, First Spark, and the retained Florin and Spell Shard totals after reload.
- Recovery steps for unavailable 3D, failed saves, and missing guest wizards.
- Local validation, hosted checks, the Test Vault, and bug-report guidance.

## Verification

GitHub rendered the candidate and the two source copies matched. All seven validation jobs passed on PR merge checkout `b5841be444b729b2c1f402b3988f87d589e57625`. Chromium, Firefox, and WebKit each passed 14 scenarios. The public runner policy and Semgrep checks also passed.
