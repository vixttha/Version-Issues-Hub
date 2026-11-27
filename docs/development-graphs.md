# Development graph snapshots — VIB local pilot

Upstream [Veraphify #88](https://github.com/vixttha/Veraphify/issues/88). Separate from historical fix, cumulative, candidate (.37 legacy), and engineering archives. No finalized/production status is inferred from structural graph evidence.

## Refresh workflow
1. Read the current active canonical issue/version and exact Worker branch head, tree, Worker record's installed SHA. Confirm the mapping and that the canonical pin is active at that revision. Do not run project code.
2. Update only `development-graph-request.json` on Veraphify by a reviewed non-force revision lease. The request identifies the snapshot to generate, not a guarantee that it is the live branch head forever.
3. Public runner extracts with Graphify 0.9.109 (pinned dependency lock). Ubuntu and Windows validate native lookup, wrong project/version/source/hash, tampered bytes and false finality before append. Retention is a non-force update on the same archive branch; a contention failure requires fresh readback and a new request or exact replay.
4. Read durable `archives/development-code-graphs/VERSION/FULL_SOURCE_SHA/receipt.json` and graph after successful publication. Older snapshots are immutable. Same source replay verifies retained bytes instead of replacing them. To find snapshots, list the version directory; no moving latest pointer is an authority. Compare the observed live Worker head to the requested/retained source to measure freshness.
5. Final acceptance and final archive promotion are separate, explicitly authorized operations; never copy a draft receipt into final scope. No product write, installed-state change, extra Worker, schedule or release.

## Retrieval
```sh
node veraphifiy.mjs code-graph --archive archives --project vixttha/Version-Issues-Hub --version v0.0.0.43 --scope development --source FULL_SHA --graph-sha256 INDEPENDENT_DIGEST
```
Use code-verify for receipt-only. Capture graph digest from a trusted run separately. Raw graph edges are structural hypotheses, not runtime proof. Archive grows with each requested revision; no silent pruning. Keep private source out of public storage. Initial request pins issue #96 at 0147d51eb7965034848ea623be55676149a74895; production integration remains unresolved.
