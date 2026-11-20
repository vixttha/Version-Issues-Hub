# Migration audit

Lydite is the standalone home for the reusable Test Vault template. The first import preserves the owner-written README introduction and adds language folders beside the original copy-in starter.

## Findings

| Finding | Impact | Lydite change |
| --- | --- | --- |
| AlderVale's reusable `Test-Vault` and game-specific `AlderVale-Test-Vault` were easy to confuse. A second game branch, `AlderVale-test-Vault`, also exists. At review, it was 188 commits behind the capitalized game branch. | Choosing the wrong branch can give a stale language inventory or a different kind of evidence. | The starter and generic examples live in Lydite. The source case suites and their exact-run evidence remain available at the pinned game references below. |
| AlderVale's broad language inventory lists ideas, live suites, conditional runtimes, and configuration formats. Its pinned Linguist list covers 573 programming entries. | A language mention does not identify a runnable suite, and a line count does not establish a test count. | Each included language links its example, purpose, command, runner, and runtime in metadata. The inventory derives counts from those declarations and checks the files are present. |
| AlderVale's strongest cross-language work shares one observation and independently checks it. Its First Spark retention is tied to a particular Chromium run attempt. Haskell and Lua work had merged to the game Vault branch, while the Java asset-check PR was open at review. | A project receipt or draft PR is evidence about that checkout and scope. | Preserve the reusable receipt schema, verifier, and upgrade rehearsal. Use standalone examples for Lydite's own runner claims. |
| Blender-Agent imported the starter, then its Vault branch acquired a catalog and a draft two-scene geometry test. The branch push only produced a skipped catalog job. The thread later planned the first Blender run and opened a docs-only planning PR. | A committed fixture, a catalog hit, and a runner result answer different questions. The draft geometry case can record a failure while the smoke job continues. | Keep case design, runnable examples, and exact-checkout execution evidence visible. Count cases and primary test files separately. |
| The original starter is an adaptable catalog and receipt kit. Its adoption jobs sample Python, Go, and documentation-only projects, and its upgrade rehearsal combines Node.js and Python. | Adopting the starter still requires project-specific assertions and commands. | Keep the original onboarding route and add worked language examples with explicit purposes. |
| The destination started with the name and README and had no license file. The source template also leaves standalone redistribution terms open. | Downstream users need a clear reuse policy before a public template release. | License Lydite's template and examples under the [MIT License](../LICENSE) and document the notice to carry with copied material. |

## Import contents

- The original `starter/`, `versions/`, `Graphify HQ/`, adoption checks, and historical version-map tooling are copied from the source template. The archive manifest continues to point to the original source commits.
- The work from the AlderVale implementations informs the example language selection and the guide for independently checking shared observations. First Spark, game state, assets, emulators, and game CI have their own home and receipts.
- The Blender-Agent planning work supplies the evidence distinctions and case lifecycle in the Lydite documentation. The Blender two-scene fixture and issue acceptance criteria belong to Blender-Agent.
- The initial folders cover Python, JavaScript, TypeScript, Go, Rust, Ruby, C++, C#, F#, Java, Haskell, Lua, Bash, and PowerShell. Each includes a test example. Browser, emulator, and schema coverage can be added when an example supplies an actual browser, emulator, or schema check.

## Source records

| Source | Verified reference |
| --- | --- |
| Reusable AlderVale template | [`b009226`](https://github.com/vixttha/AlderVale-Pact-of-Ten/tree/b0092267fd64e3025cbfece18db6d4fb3b1c356c), [template verification](https://github.com/vixttha/AlderVale-Pact-of-Ten/actions/runs/44410872730) |
| AlderVale game-specific Vault | [`cba804a`](https://github.com/vixttha/AlderVale-Pact-of-Ten/tree/cba804a4aebcc034500a54669e77c2630f3ba565), [public validation](https://github.com/vixttha/AlderVale-Pact-of-Ten/actions/runs/44425552686), [cross-language rules](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/cba804a4aebcc034500a54669e77c2630f3ba565/docs/test-vault/aldervale/cross-language-rules.md) |
| AlderVale language additions | [First Spark evidence #134](https://github.com/vixttha/AlderVale-Pact-of-Ten/pull/134), [Haskell #131](https://github.com/vixttha/AlderVale-Pact-of-Ten/pull/131), [Lua #132](https://github.com/vixttha/AlderVale-Pact-of-Ten/pull/132), [Java #128](https://github.com/vixttha/AlderVale-Pact-of-Ten/pull/128) |
| Blender-Agent project Vault | [`9d29da0`](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/9d29da099785003ad2d3f97f34b9ff04dffb5a70), [skipped catalog run](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/actions/runs/44466137486), [planning draft #60](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/pull/60) |
| Lydite baseline | [Brand and README at `08806bf`](https://github.com/vixttha/Lydite-Test-Vault-Template/tree/08806bf515d13db6ebf88a649c932c07a1dfbbab) |
