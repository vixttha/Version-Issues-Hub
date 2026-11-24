# Controlled agent recovery benchmark — pilot 1

Date: 2026-11-24. Two new read-only Notion Agent Coordinator sessions, same harness, underlying model identity and token usage unverified. Same historical BART issue #69 task around 06:00 UTC. Control restricted to ordinary product issue/PR/Actions evidence. Intervention could also use exact VIB snapshot 7328361910cd8a705a49d0106cfbd315c1c53311. No product modifications. This measures recovery/reporting, not full coding productivity or use of all six tools.

## Preregistered scoring (8 binary items)

| Criterion | Expected | Control | VIB-assisted |
|---|---|---:|---:|
| Explicit development version | v0.0.3.3 | 0 | 0 |
| Exact candidate | 4e47aba6eec452865e1ec9e85ffab535c8ebb0d4 | 1 | 1 |
| Proposed merge | 0c99ccb2a6a81f91c06d5ec686d76ba995448013 | 1 | 1 |
| Candidate run | 45334949893 | 1 | 1 |
| Candidate job count | 10/10 | 1 | 1 |
| Actual merge | 392d8d7a1c262227cba3c08d5577af38c74b4e25 | 1 | 1 |
| Correct next action | Verify exact main push CI; then reconcile | 1 | 1 |
| Release authority | No package release | 1 | 1 |
| Total | 8 | 7 | 7 |

Both reported post-merge run 45337193197 (10/10); both omitted the requested explicit version string. Observed complete session event lists contained 9 control tool-use events and 15 VIB-assisted tool-use events (not token counts). VIB-assisted agent explicitly distinguished stale handoff from newer GitHub evidence. No accuracy improvement measured; the intervention used six more observed tool calls. With n=1 per arm, do not infer efficiency, latency, cost or population-level effect. No fabricated results.

Evidence: [issue](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/issues/69), [PR](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/pull/109), [candidate run](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/actions/runs/45334949893), [main run](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/actions/runs/45337193197), [VIB snapshot](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/7328361910cd8a705a49d0106cfbd315c1c53311). Private agent session records retained in Notion; do not publish private session URLs.

## Next evaluation design

Use equal model/effort/tool budgets and paired fresh sessions on representative bug fixes, feature implementation, interrupted handoffs, testing, documentation, brand consistency and evidence lookup. Include zero-tool control and all-six intervention, randomized task/arm order, preregistered scoring, hidden acceptance tests, exact source pins, no code reuse between arms, and human intervention counts. Run mechanical acceptance on public hosted runners. Report actual accepted-fix and regression rates, with confidence intervals where sample permits; disclose unknown token/time/cost. No mandatory eval service or agent provider.
