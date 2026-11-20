# README v0.0.4 changelog

## Changes since v0.0.3

- Add the Bazaar quick link and a short signed-in-player guide for buying, listing, and cancelling gear listings.
- Explain that Bazaar purchases and sale proceeds use the realm Bazaar wallet, while Academy shops use wizard Florins.
- Explain where purchased gear appears in Tailor, replacing equipped gear before listing, and live wallet updates for connected sellers.

## Source, acceptance, and validation

The owner accepted the public README v0.0.4 draft for archival on 2026-11-18. The archived README is copied byte for byte from `workspace/v0.0.4/DRAFT.md` at commit `58fd11f7483aeaa0d44b79d3142337eb239aabd2` (Git blob `5a985415260e0859a6e52a368c19043ae6160d30`).

The Workmark v1, Breeze campus capture, and First Spark duel capture reuse the exact Git blobs from the approved v0.0.3 archive. No new gameplay images were produced.

The Bazaar player-facing wording was checked against game `main` at `38ba3e66f62e3607e23a5ed8d82fe625e770a1a5`. [PR #103](https://github.com/vixttha/AlderVale-Pact-of-Ten/pull/103) merged with all seven [post-merge game jobs](https://github.com/vixttha/AlderVale-Pact-of-Ten/actions/runs/44250371588) passing, including authenticated emulator coverage for buyer item receipt and seller wallet updates. The [draft README HQ validation](https://github.com/vixttha/AlderVale-Pact-of-Ten/actions/runs/44252451108) passed on public hosted Ubuntu; the rendered desktop/mobile review of the pinned draft confirmed all three images loaded and the Bazaar jump link worked.

Archival into `readme-hq` does not publish the game README to `main`. A separate publication PR and its checks are required.
