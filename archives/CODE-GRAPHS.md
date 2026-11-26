# Raw historical code graphs

Distinct from feature-evidence Veraphify candidate archives. Each version uses its immutable engineering fix source (operational .23 uses the actual release preflight revision), not a claim of historical candidate acceptance. Public Graphify AST extraction creates raw graph.json, receipt.json and index.json under archives/code-graphs after independent verification. This is an isolated review branch, not a new active canonical Worker or production merge. Native Veraphify feature-evidence import remains separate.

## v0.0.0.37 candidate archive

The exact unmerged #53 candidate is separate from immutable .1–.36 fix and cumulative graphs. Use `code-graph --archive archives --project vixttha/Version-Issues-Hub --version v0.0.0.37 --scope candidate --source SHA --graph-sha256 HASH` with the independently recorded pins in the candidate receipt. The raw graph and debug adjacency report are archived under `archives/candidate-code-graphs/v0.0.0.37/<source>/`. Inferred relationships are hypotheses, not runtime proof. Feature evidence uses two nodes for #53; neither node allocates another issue version.
