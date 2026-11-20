# Test case and evidence templates

Copy these sections into the relevant GitHub issue or PR. Keep one canonical issue per bug and reuse case IDs across implementations of the same expected behavior.

## Case

| Field | Fill in |
|---|---|
| Case ID and topic | Example `G13-001`, quests and rewards |
| User impact | What the player can’t do or what state becomes inconsistent |
| Expected behavior | State the observable result and where the requirement comes from |
| Test layer and tool | Unit, browser, server, emulator, fixture reader, or manual |
| Fixture and setup | Synthetic save, deterministic seed, role, browser, or emulator |
| Action and assertions | Exact steps, expected values, and what persists after retry or reload |
| Implementation and command | Repository path or scenario title and command |
| Related evidence | Canonical GitHub issue, PR, test file, and existing case links |
| Current state | Proposed, implemented, CI verified, or owner verified |

## Run receipt

| Field | Fill in |
|---|---|
| Case IDs | Exact cases executed |
| Revisions | Tested checkout SHA, PR base SHA, PR head SHA, and resulting merged SHA when available |
| Run and attempt | Actions run URL, attempt number, and job URL |
| Environment | Runner OS/image, runtime version, browser or emulator version |
| Result | Passed, failed, skipped, or blocked, with observed count or assertion |
| Known-bad check | Revision or safe fixture and what failed |
| Repair check | Fixed checkout and what passed |
| Retry history | Prior attempt results and any nondeterminism observed |
| Coverage limits | Unexercised roles, paths, platforms, or real-device checks |

## Owner playthrough

Record the pinned build and device. Note one observed result per step: title, wizard creation, realm entry, solo duel, return to campus, reload, and persisted quest and reward state. Link any unexpected behavior to its GitHub issue and record the owner’s acceptance decision separately from the CI receipt.
