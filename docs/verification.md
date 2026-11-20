# Verification evidence for the Veraphify v0.0.9 preview

[Back to the README](../README.md)

## What the tests demonstrate

| Claim | Expected result | Evidence |
| --- | --- | --- |
| Feature lookup uses the requested version. | `feature:export` resolves to `src/feature.py:3` in `v1.0.0` and `src/feature.py:4` in `v1.1.0`. The source commits differ. | [Ubuntu walkthrough and Graphify job](https://github.com/vixttha/Veraphify/actions/runs/44644119066/job/135982253574) |
| Import keeps the earlier version intact. | The bytes of the `v1.0.0` archive entry match before and after importing `v1.1.0`. | [Walkthrough and assertions](https://github.com/vixttha/Veraphify/blob/66e822b56528c5f3e7b7730709d4b472ae2d5f1e/docs/adopter-walkthrough.md) |
| The retained handoff can be replayed independently. | The Ubuntu and Windows consumers verify the same handoff and replay both archives. | [Ubuntu replay](https://github.com/vixttha/Veraphify/actions/runs/44644119066/job/135983825591) · [Windows replay](https://github.com/vixttha/Veraphify/actions/runs/44644119066/job/135983825610) |

## Exact run and handoff

| Field | Value |
| --- | --- |
| Candidate source commit | [`66e822b56528c5f3e7b7730709d4b472ae2d5f1e`](https://github.com/vixttha/Veraphify/commit/66e822b56528c5f3e7b7730709d4b472ae2d5f1e) |
| Workflow | [`.github/workflows/test-vault.yml`](https://github.com/vixttha/Veraphify/blob/66e822b56528c5f3e7b7730709d4b472ae2d5f1e/.github/workflows/test-vault.yml) at the candidate commit |
| Event and attempt | `push`, [run `44644119066`, attempt `1`](https://github.com/vixttha/Veraphify/actions/runs/44644119066/attempts/1) |
| Artifact | [ID `14588062738`](https://github.com/vixttha/Veraphify/actions/runs/44644119066/artifacts/14588062738) |
| ZIP SHA-256 | `dc4177c9ec1b44c0c8883ef32aba74f1322b1acee2f12de0b3ea54d4c7fe51d8` |

The same checkout contains the [first-party MIT license](https://github.com/vixttha/Veraphify/blob/66e822b56528c5f3e7b7730709d4b472ae2d5f1e/LICENSE) and its [reuse and attribution guide](https://github.com/vixttha/Veraphify/blob/66e822b56528c5f3e7b7730709d4b472ae2d5f1e/docs/reuse.md).

## Repeat the walkthrough

1. Follow the [README quickstart](../README.md#quickstart) to check out the candidate.
2. Run the Bash block in the [walkthrough at that commit](https://github.com/vixttha/Veraphify/blob/66e822b56528c5f3e7b7730709d4b472ae2d5f1e/docs/adopter-walkthrough.md) on Linux x86-64 with Node.js 24, Git, and CPython 3.12 with `venv`. The guide pins the Graphify producer and builds fresh fixture commits in a temporary directory.
3. Check the two citations above and the expected `Project version is not archived` message for the missing fixture version.

The ZIP digest verifies the downloaded bytes while a copy is available. The rerun checks the same behavior with fresh fixture commits and can produce a different archive digest.

See the [release tracker](https://github.com/vixttha/Veraphify/issues/21#v009-release-evidence-rule) for product release acceptance.
