# VIB language role review

All roles below are proposals for owner discussion, not approved implementation scope. The current upstream inventory has 14 language folders (13 Ubuntu examples and 1 Windows example). C is listed separately as a previously discussed possibility, absent from upstream. No requirement to use every language; keep VIB Python-only unless separately approved. Existing Python suites are the current mechanical baseline, not a new language selection.

| Language | Current template runtime | Proposed VIB testing role | Decision |
|---|---|---|---|
| Python | 3.12 / unittest | Core VIB CLI, ledger, install, recovery, receipts; existing native test suites | Pending owner review |
| Bash | Bash | Linux invocation, Git quoting, paths, exit codes | Pending owner review |
| PowerShell | PowerShell 7 | Windows invocation, paths, CRLF, exit codes | Pending owner review |
| JavaScript | Node.js 24 | Independent JSON and receipt consumer, fixture/API contracts | Pending owner review |
| TypeScript | Node.js 24 | Typed consumer contracts and schema-bound data | Pending owner review |
| Go | Go 1.25.5 | Concurrent client simulation and transport contract fixtures | Pending owner review |
| Rust | Stable rustc | Independent state/operation invariants and parser checks | Pending owner review |
| C++ | C++20 / g++ | Optional native consumer interoperability; no VIB runtime dependency | Pending owner review |
| C# | .NET 8 | Independent .NET JSON and consumer compatibility | Pending owner review |
| F# | .NET 8 | State-transition and invariant model experiments | Pending owner review |
| Java | Java 21 | Cross-runtime JSON and file interoperability | Pending owner review |
| Haskell | GHC | Pure state model and invariant exploration | Pending owner review |
| Lua | Lua 5.4 | Lightweight scripting consumer portability | Pending owner review |
| Ruby | Ruby | Independent script/JSON consumer compatibility | Pending owner review |
| C | Not supplied upstream | Proposed native portability coverage; not installed or qualified | Not installed; discuss |

## Selection criteria
Actual VIB risk covered; unique value over existing Python tests; repeatability; public-runner availability; maintenance and CI cost; evidence quality. First language and role allocation remain unselected.
