# Languages and test formats

Use TypeScript and JavaScript for AlderVale’s runtime. Use Python for the catalog validator and independent tooling checks. Ruby, C#, Go, and Rust are the first candidates for additional independent checks because each has a distinct job. The remaining entries show where a language becomes useful when a fixture, external consumer, or shipped runtime warrants it.

| Language or format | Test tools | A concrete case | Availability |
|---|---|---|---|
| TypeScript | Vitest | Combat, progression, save migrations, shared catalog contracts | Existing gameplay CI |
| JavaScript (ESM) | Node test runner and Playwright | Built-server smoke, guest browser flows, offline HUD and reconnect | Existing gameplay CI |
| Python | unittest or pytest | Vault catalog validation, independent replay comparison and asset provenance | Template validator and separate PR #87 policy candidate |
| Ruby | Minitest or RSpec | Verify localized catalog references and user-visible error fixtures | Planned |
| C# | .NET test runner with xUnit or NUnit | Independent save reader and fixture tests for creature selection or trade receipts | Planned |
| Go | go test | Independent local HTTP/WebSocket client and bounded reconnect runs | Planned |
| Rust | cargo test and proptest | Check GLB boundaries, chunk lengths, and deterministic asset parser results | Planned |
| Java | JUnit | Compare demo-emulator client readback against typed fixture expectations | Java 21 is already the emulator runtime |
| Kotlin | kotlin.test or JUnit | Verify Android/JVM client save and event parity when a client exists | Conditional on client |
| Scala | ScalaTest | Check deterministic progression and shared event decoding on JVM fixtures | Optional reference model |
| Clojure | clojure.test | Replay immutable quest and match states against the TypeScript implementation | Optional reference model |
| Groovy | Spock | Table-test JVM adapter versions and supported event conversions | Conditional on JVM integration |
| F# | FsCheck with a .NET test runner | Check additive rewards, save normalization and multiset conservation | Optional reference model |
| Visual Basic .NET | MSTest | Read public export fixtures and verify a supported legacy consumer | Conditional on consumer |
| C | CTest or Unity | Check native GLB header bounds and little-endian decoding | Conditional on native asset path |
| C++ | Catch2 or CTest | Compare movement and collision against a fixed reference trajectory | Optional reference model |
| Zig | zig test | Check exact byte lengths and endian rules for a future binary reader | Conditional on binary reader |
| Nim | unittest | Read an exported asset index and compare normalized fixtures | Conditional on consumer |
| D | dub test | Check an asset exporter or binary adapter against representative fixtures | Conditional on adapter |
| Swift | Swift Testing or XCTest | Verify save decoding and touch journeys in an Apple client on macOS | Conditional on Apple client |
| Objective-C | XCTest | Verify compatibility of any supported legacy Apple wrapper | Conditional on Apple wrapper |
| Objective-C++ | XCTest | Verify native rendering bridge and asset loading on an Apple target | Conditional on native bridge |
| Dart | dart test or Flutter integration_test | Verify persistence, orientation, and touch in a Flutter client | Conditional on Flutter client |
| PHP | PHPUnit | Verify public catalog export consumption and version handling | Conditional on consumer |
| Perl | Test::More | Verify stable export delimiters, encodings, and legacy ingest | Conditional on legacy integration |
| Raku | Test | Verify text import and Unicode round trips for a Raku consumer | Conditional on consumer |
| Elixir | ExUnit | Compare presence state transitions for a future BEAM adapter | Conditional on BEAM adapter |
| Erlang | EUnit or Common Test | Verify message-ordering behavior within a supported BEAM process | Conditional on BEAM component |
| Gleam | Gleeunit | Decode typed event fixtures for a Gleam client or adapter | Conditional on client |
| Haskell | QuickCheck or Hspec | Implement an independent reference model for small deterministic duels | Optional reference model |
| OCaml | QCheck or Alcotest | Compare quest progression and reward idempotence with fixed replays | Optional reference model |
| Standard ML | Language-native assertions | Compare a small deterministic state-transition oracle with fixtures | Optional reference model |
| Elm | elm-test | Verify supported player-view rendering and state transitions in an Elm client | Conditional on Elm client |
| Lua | busted | Test duration and stacking rules against a small independent table model | Optional reference model |
| Luau | Luau test harness | Verify compatible event and save fixtures for a Luau integration | Conditional on integration |
| GDScript | Godot headless tests | Verify asset import and animation state in a Godot port | Conditional on port |
| Haxe | utest | Compare event and save parity in a Haxe target | Conditional on target |
| R | testthat | Analyze fixed-run deck balance and report variance with sample counts | Optional analysis |
| Julia | Julia Test | Numerical cross-check of a seeded combat distribution | Optional analysis |
| Octave | Built-in test support | Compare approved numeric baselines in a reproducible fixture | Optional analysis |
| MATLAB | MATLAB Unit Test | Compare externally supplied numeric baselines where approved access exists | Conditional on already-authorized tool access |
| Fortran | fpm test | Cross-check an explicitly specified progression or probability formula | Optional reference model |
| COBOL | GnuCOBOL fixture driver | Verify a declared legacy record import contract | Conditional on legacy integration |
| Ada | AUnit | Check a future typed binary format or strict import contract | Conditional on format or integration |
| Pascal | FPCUnit | Verify a supported desktop export or file reader | Conditional on consumer |
| Delphi | DUnitX | Verify an existing Delphi integration with approved tooling | Conditional on integration and tooling |
| Racket | rackunit | Express quest and reward rules as a small independent oracle | Optional reference model |
| Common Lisp | FiveAM | Compare fixed rule outcomes against a fixture table | Optional reference model |
| Scheme | SRFI-64 | Check ordered effects and idempotence in a rules model | Optional reference model |
| Prolog | PlUnit | Check allowable quest transitions and contradictory eligibility rules | Optional reference model |
| Bash / POSIX shell | ShellCheck or Bats | Check Unix startup, reproducible build commands, cleanup and rollback | Shell steps in existing CI |
| PowerShell | Pester | Check Windows path quoting, startup, cleanup and rollback | Windows runner available |
| SQL | SQLite fixtures or pgTAP | Model ledger conservation and test migrations for a real relational adapter | Model only for current Firestore gameplay |
| Firestore Rules | Firebase Emulator Suite | Verify permitted access and supported document invariants | Existing gameplay CI |
| HTML/CSS | Playwright and axe-core | Verify semantic names, keyboard focus, responsive layout and zoom | Browser checks in existing gameplay CI |
| GLSL | WebGL compile and render fixtures | Check shader compilation and recovery at a stated WebGL boundary | Conditional on shipped shader |
| WGSL | WebGPU compilation fixtures | Check shader portability for a future WebGPU renderer | Conditional on shipped WebGPU renderer |
| WebAssembly text / assembly | Runtime-specific fixture runner | Verify output parity for an actual shipped native or WASM routine | Conditional on shipped routine |
| YAML | Workflow policy checker and syntax linting | Check standard runner declarations, action pins, and permissions | Existing policy CI |
| JSON / JSON Schema | Schema validator | Check portable case fixtures, save contracts and exact-run receipts | Fixture format |
| Gherkin | Cucumber bindings | Describe guest onboarding and acceptance in player language | Optional acceptance format |
| OpenAPI / AsyncAPI | Contract validation | Check documented HTTP routes and live event examples against fixtures | Conditional on versioned interface specification |
| TLA+ / PlusCal | TLC | Explore reward-once and settlement state transitions in a bounded model | Optional formal model |
| Alloy | Alloy Analyzer | Check state invariants for small trade and account models | Optional formal model |
| SMT-LIB | SMT solver | Check conflicting eligibility or progression constraints in a fixed model | Optional formal model |
| CUE / Dhall / Rego / Jsonnet | Language-native checkers | Validate workflow and environment contracts if the repo adopts that format | Conditional on adopted configuration format |

Pin the version of tools you install in CI, use lockfiles where available, and start with synthetic fixtures that other languages can read. A Python parser, a Ruby catalog check, and a C# fixture reader can share one documented JSON fixture format. Give each suite a clear outcome, a bounded runtime, and a command that can run from a clean checkout. Use the approved runner labels and verify availability, licensing, and cost before adopting a new toolchain.
