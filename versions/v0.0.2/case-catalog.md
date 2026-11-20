# AlderVale test ideas

Each row is a proposed test scenario. Use the [case and evidence template](case-and-receipt.md) to connect a case to existing coverage or implement it. Match existing tests by fixture and assertion before writing a new one. G13-001 keeps the existing First Spark case ID. The rows describe desired behavior and require an approved decision wherever game rules are still open.

P0 covers the first-playable path, data integrity, or CI evidence needed to review a change. P1 covers broader behavior or integrations. P2 covers exploratory, analytical, or conditional work. Priority here orders test coverage, while GitHub Issues tracks the priority and disposition of individual bugs.

## Gameplay

| Case | Area | Priority | Suggested implementation | Expected outcome |
|---|---|---|---|---|
| G01-001 | Boot and onboarding | P0 | TypeScript + Playwright | Fresh guest reaches playable campus after title and wizard creation. |
| G01-002 | Boot and onboarding | P0 | TypeScript + Playwright | Interrupted enrollment resumes with one wizard and one save. |
| G02-001 | Realms and wizard slots | P0 | TypeScript + JavaScript | Switch realm and reload with the selected wizard preserved. |
| G02-002 | Realms and wizard slots | P0 | TypeScript + JavaScript | Fill each supported slot and verify one realm never displays another realm’s wizard. |
| G03-001 | Identity and lineage | P1 | TypeScript + Playwright | Each supported lineage starts with its documented defaults. |
| G03-002 | Identity and lineage | P1 | TypeScript + Playwright | Legacy appearance data loads with valid defaults and remains editable. |
| G04-001 | Progression and unlocks | P0 | TypeScript + Python | XP one below, exactly at, and above an unlock threshold resolves correctly. |
| G04-002 | Progression and unlocks | P0 | TypeScript + Python | A multi-level payout grants each reached unlock exactly once. |
| G05-001 | Spell catalog and deck editor | P0 | TypeScript + Playwright | Every approved element and level gets a legal starter deck. |
| G05-002 | Spell catalog and deck editor | P0 | TypeScript + Playwright | Save, cancel, and reload preserve the intended deck across size boundaries. |
| G06-001 | Combat math and turn order | P0 | TypeScript + Haskell | Replay the same seed and turn actions to the same final state. |
| G06-002 | Combat math and turn order | P0 | TypeScript + Haskell | Resolve simultaneous final damage once according to the approved draw rule. |
| G07-001 | PvP and perspectives | P1 | TypeScript + Go | Both players observe the same turn number and winner after reconnect. |
| G07-002 | PvP and perspectives | P1 | TypeScript + Go | A private invite is visible only to its participants in normal client views. |
| G08-001 | Co-op and spectating | P1 | TypeScript + Go | Two fixture teammates complete a turn with consistent state. |
| G08-002 | Co-op and spectating | P1 | TypeScript + Go | A spectator sees only fields explicitly allowed by the public view contract. |
| G09-001 | Solo combat and trials | P0 | JavaScript + Playwright | Guest wins a controlled solo duel and returns to campus. |
| G09-002 | Solo combat and trials | P0 | JavaScript + Playwright | Loss and flee show distinct feedback and return the player to usable controls. |
| G10-001 | Statuses and enchantments | P1 | TypeScript + Lua | Duration and stacking follow the rule for cast, resolve, and expiration. |
| G10-002 | Statuses and enchantments | P1 | TypeScript + Lua | A dispelled effect leaves no stale modifier in the next turn. |
| G11-001 | Creatures and bonding | P1 | TypeScript + C# | Changing the selected creature updates the next supported encounter. |
| G11-002 | Creatures and bonding | P1 | TypeScript + C# | Bond progress updates only for actions specified by the approved participation rule. |
| G12-001 | Breeding and hatching | P1 | TypeScript + Firestore Rules | Multiple permitted hatch results survive reload as distinct entries. |
| G12-002 | Breeding and hatching | P1 | TypeScript + Firestore Rules | A retried hatch save preserves its original result and charges once. |
| G13-001 | Quests and Term track | P0 | TypeScript + Playwright | First Spark pays the catalog amount once and survives reload. |
| G13-002 | Quests and Term track | P0 | TypeScript + Playwright | Harmony and Rare Trial follow approved completion and payout rules for each supported path. |
| G14-001 | Currency and rewards | P0 | TypeScript + Python | XP, Florins, and shards reconcile between award receipt and saved state. |
| G14-002 | Currency and rewards | P0 | TypeScript + Python | A repeated reward receipt cannot credit a second payout. |
| G15-001 | Bazaar | P1 | TypeScript + Firestore Rules | An authorized sale transfers the listed item and reconciles both balances. |
| G15-002 | Bazaar | P1 | TypeScript + Firestore Rules | A failed or retried settlement preserves the agreed inventory and currency totals. |
| G16-001 | Peer trade | P1 | TypeScript + C# | Accepted trade updates both fixture inventories exactly once. |
| G16-002 | Peer trade | P1 | TypeScript + C# | Cancel or reconnect before settlement leaves both sides consistent. |
| G17-001 | Tailor, gear and vault | P1 | JavaScript + Playwright | Equip an item, verify its stat change, and confirm after browser reload. |
| G17-002 | Tailor, gear and vault | P1 | JavaScript + Playwright | Remove or replace gear and verify appearance and stats follow the saved loadout. |
| G18-001 | Shops, crafting and resources | P1 | TypeScript + SQL model | A purchase or craft at the exact currency or materials boundary succeeds once. |
| G18-002 | Shops, crafting and resources | P1 | TypeScript + SQL model | An insufficient-resource attempt preserves balances and inventory. |
| G19-001 | Maps and navigation | P1 | TypeScript + Playwright | Every supported destination has a valid spawn and return route. |
| G19-002 | Maps and navigation | P1 | TypeScript + Playwright | Reload in a zone restores the location according to the save contract. |
| G20-001 | Physics and movement | P1 | TypeScript + C++ | Replay collision-edge movement without clipping or leaving world bounds. |
| G20-002 | Physics and movement | P1 | TypeScript + C++ | Equivalent movement over similar elapsed time stays within a defined tolerance. |
| G21-001 | Avatars and animation | P1 | JavaScript + Rust | Rowan assets load with required rigs and clips and survive repeated entry and exit. |
| G21-002 | Avatars and animation | P1 | JavaScript + Rust | Missing models show the usable Classic fallback and retry can recover. |
| G22-001 | Camera and controls | P1 | JavaScript + Playwright | Keyboard, pointer, and touch controls reach the same supported actions. |
| G22-002 | Camera and controls | P1 | JavaScript + Playwright | Open and close a modal and verify movement, focus, and camera recover. |
| G23-001 | NPCs and interactables | P1 | TypeScript + Playwright | Each catalog NPC opens its declared panel from a valid location. |
| G23-002 | NPCs and interactables | P1 | TypeScript + Playwright | Leaving interaction range removes the prompt and preserves keyboard focus. |
| G24-001 | Dorm and public tours | P1 | TypeScript + Firestore Rules | Place decor and verify orientation and appearance after reload. |
| G24-002 | Dorm and public tours | P1 | TypeScript + Firestore Rules | A normal public tour shows only the fields allowed by the tour contract. |
| G25-001 | Houses and social state | P1 | TypeScript + Firestore Rules | A membership change appears consistently in allowed member views. |
| G25-002 | Houses and social state | P1 | TypeScript + Firestore Rules | Reconnect restores the correct house and role for the fixture account. |
| G26-001 | Chat, presence and moderation | P1 | JavaScript + Go | Realm presence changes from online to offline to online as the fixture socket reconnects. |
| G26-002 | Chat, presence and moderation | P1 | JavaScript + Go | Two players with the same display name remain distinct in the mute UI. |
| G27-001 | AI Lectern | P2 | TypeScript + Python | Offline or unconfigured service shows an understandable fallback. |
| G27-002 | AI Lectern | P2 | TypeScript + Python | Fixture success, timeout, and provider errors render the correct result without live calls. |
| G28-001 | Local guest saves | P0 | TypeScript + JavaScript | A rejected write keeps an honest status and a successful retry persists current progress. |
| G28-002 | Local guest saves | P0 | TypeScript + JavaScript | Older local saves load with defaults and isolated realm keys. |
| G29-001 | Account and cloud saves | P1 | TypeScript + Java | Guest migration in the demo emulator preserves progress and avoids duplicate wizards. |
| G29-002 | Account and cloud saves | P1 | TypeScript + Java | Interrupted synchronization resumes with a defined conflict outcome. |
| G30-001 | Network interruption | P0 | JavaScript + Go | Disconnect during a guest session and verify the offline HUD and supported recovery. |
| G30-002 | Network interruption | P0 | JavaScript + Go | Reconnect during a supported duel restores an unambiguous turn and reward state. |
| G31-001 | Audio | P2 | JavaScript + Playwright | Mute and volume choices survive reload. |
| G31-002 | Audio | P2 | JavaScript + Playwright | Repeated transitions stop old playback and preserve alternative cues. |
| G32-001 | Interface states | P1 | TypeScript + Playwright | Loading, empty, failed, and recovered views keep the player’s action available. |
| G32-002 | Interface states | P1 | TypeScript + Playwright | Rapidly close and reopen a slow panel and display only the current result. |
| G33-001 | Accessibility | P1 | HTML/CSS + Playwright | Complete the guest flow with keyboard and accessible labels. |
| G33-002 | Accessibility | P1 | HTML/CSS + Playwright | Verify modal announcements and focus manually using assistive technology. |
| G34-001 | Responsive rendering | P1 | CSS + JavaScript | At narrow and zoomed viewports the essential HUD actions stay reachable. |
| G34-002 | Responsive rendering | P1 | CSS + JavaScript | Reduced motion and WebGL fallback preserve core interaction. |
| G35-001 | Localization, time and content | P2 | Ruby + TypeScript | Verify text expansion and number formatting against known locale fixtures. |
| G35-002 | Localization, time and content | P2 | Ruby + TypeScript | Reset windows and timestamps behave correctly across timezone boundaries. |
| G36-001 | Full player scenarios | P0 | JavaScript + manual desktop | Owner completes title, wizard, realm, duel, and persisted reload on a pinned desktop build. |
| G36-002 | Full player scenarios | P0 | JavaScript + manual desktop | Repeat the journey from a legacy guest save and verify its existing progress. |

## Engineering

| Case | Area | Priority | Suggested implementation | Expected outcome |
|---|---|---|---|---|
| E01-001 | Unit and boundary values | P0 | TypeScript + Vitest | Table-test min, max, and adjacent valid values for a public rule. |
| E01-002 | Unit and boundary values | P0 | TypeScript + Vitest | Empty and missing inputs return the documented default or error. |
| E02-001 | Component and UI contracts | P1 | TSX + Playwright | Render enabled, disabled, busy, and error states for each reused button. |
| E02-002 | Component and UI contracts | P1 | TSX + Playwright | Only one outcome event is emitted by a double click. |
| E03-001 | Static analysis and types | P0 | TypeScript + YAML | Compile with the pinned TypeScript toolchain and verify supported contracts. |
| E03-002 | Static analysis and types | P0 | TypeScript + YAML | Workflow syntax and action references meet the documented repository rules. |
| E04-001 | Property-based testing | P1 | TypeScript + Python | Generate valid decks and assert all drawn cards come from the input multiset. |
| E04-002 | Property-based testing | P1 | TypeScript + Python | Generate XP and reward inputs and assert progression is monotonic. |
| E05-001 | Model and state-machine testing | P1 | Haskell + TypeScript | Enumerate permitted match transitions and compare app states after the same actions. |
| E05-002 | Model and state-machine testing | P1 | Haskell + TypeScript | Compare the reward model with app outcomes for a small fixed replay corpus. |
| E06-001 | Combinatorial testing | P2 | Python | Generate pairwise lineage, element, browser, and realm fixtures. |
| E06-002 | Combinatorial testing | P2 | Python | Report any required pair without a corresponding scenario ID. |
| E07-001 | Seeded simulations and balance | P2 | R + Julia | Report outcome distributions for a fixed panel of decks and seeds. |
| E07-002 | Seeded simulations and balance | P2 | R + Julia | Flag agreed balance thresholds using a baseline with fixed seeds and sample size. |
| E08-001 | Authorization and policy | P0 | TypeScript + Firestore Rules | Verify expected access for supported guest, owner, teammate, and spectator roles. |
| E08-002 | Authorization and policy | P0 | TypeScript + Firestore Rules | Keep the owner fixture’s writes scoped to the correct realm and document. |
| E09-001 | Privacy and data handling | P1 | Python + TypeScript | Verify rendered public records contain only approved fields. |
| E09-002 | Privacy and data handling | P1 | Python + TypeScript | Check captured fixture logs omit account metadata and private save content. |
| E10-001 | Protocol contracts | P1 | JavaScript + Go | Compare server health and supported event sequences against shared fixtures. |
| E10-002 | Protocol contracts | P1 | JavaScript + Go | Check that two independent clients interpret the versioned JSON contract the same way. |
| E11-001 | Integration | P0 | JavaScript + Java | Run the built app and verify the server, browser, and demo emulator connect. |
| E11-002 | Integration | P0 | JavaScript + Java | Close the test resources cleanly and confirm a second test start succeeds. |
| E12-001 | Smoke and end-to-end | P0 | JavaScript + Playwright | Run the guest first-playable journey against the built app. |
| E12-002 | Smoke and end-to-end | P0 | JavaScript + Playwright | Run the same smoke on each supported browser and capture failing step IDs. |
| E13-001 | Regression | P0 | TypeScript | Show a behavior test fails on the known-bad fixture and passes after its fix. |
| E13-002 | Regression | P0 | TypeScript | Verify related paths and the original known-good behavior in the same run. |
| E14-001 | Invalid inputs | P1 | TypeScript + Ruby | Reject unsupported save schema versions with a clear message. |
| E14-002 | Invalid inputs | P1 | TypeScript + Ruby | Reject unknown catalog IDs while preserving previously saved valid state. |
| E15-001 | Schema and referential integrity | P0 | TypeScript + Ruby | Each spell, quest, NPC, model, and localized asset reference resolves. |
| E15-002 | Schema and referential integrity | P0 | TypeScript + Ruby | A removed fixture reference fails with its originating catalog row. |
| E16-001 | Save migration | P0 | TypeScript + Python | Read each supported historical save fixture and compare its normalized projection. |
| E16-002 | Save migration | P0 | TypeScript + Python | Reapply migration and confirm the same output without duplicated rewards. |
| E17-001 | Concurrency and atomicity | P1 | TypeScript + Firestore Rules | Simultaneous permitted claim requests yield one payout. |
| E17-002 | Concurrency and atomicity | P1 | TypeScript + Firestore Rules | An interrupted write leaves the fixture state consistent for the next attempt. |
| E18-001 | Fault injection and resilience | P1 | TypeScript + JavaScript | A fixture load error shows fallback and the next successful attempt recovers. |
| E18-002 | Fault injection and resilience | P1 | TypeScript + JavaScript | Repeated recoverable errors stop at the configured retry budget. |
| E19-001 | Differential and replay | P1 | Python + Haskell | Compare one versioned deterministic match replay against two independent implementations. |
| E19-002 | Differential and replay | P1 | Python + Haskell | Compare guest and demo-cloud saves after normalization of documented differences. |
| E20-001 | Mutation testing | P2 | TypeScript | Change a reward boundary in a disposable copy and confirm the intended tests detect it. |
| E20-002 | Mutation testing | P2 | TypeScript | Track surviving mutations once the focused suite has a baseline. |
| E21-001 | Coverage quality | P1 | TypeScript + Python | Map each first-playable acceptance step to a runnable case or a manual record. |
| E21-002 | Coverage quality | P1 | TypeScript + Python | Check that skipped cases and retry passes are visible in receipts. |
| E22-001 | Visual regression | P1 | JavaScript + Playwright | Compare critical HUD, wizard, and fallback views in fixed viewports. |
| E22-002 | Visual regression | P1 | JavaScript + Playwright | Verify Rowan animation reference frames with a documented rendering tolerance. |
| E23-001 | Assistive technology | P1 | HTML/CSS + Playwright | Check names, roles, keyboard order, and contrast on critical panels. |
| E23-002 | Assistive technology | P1 | HTML/CSS + Playwright | Record the owner’s assistive-technology pass or observed gaps by environment. |
| E24-001 | Browser, OS, and device compatibility | P0 | JavaScript + PowerShell | Run guest browser coverage on Chromium, Firefox, and WebKit. |
| E24-002 | Browser, OS, and device compatibility | P0 | JavaScript + PowerShell | Validate Windows, macOS, and Linux build entry points and record real-device checks separately. |
| E25-001 | 3D and audio accessibility | P1 | JavaScript + GLSL | Provide visible text cues for essential audio or 3D-only status. |
| E25-002 | 3D and audio accessibility | P1 | JavaScript + GLSL | Test keyboard and touch access to the same required world interactions. |
| E26-001 | Performance | P1 | JavaScript + Python | Measure startup and scene entry against a stated baseline and runner image. |
| E26-002 | Performance | P1 | JavaScript + Python | Repeat campus entry and exit and record whether retained resources trend upward. |
| E27-001 | Bounded load | P2 | Go + JavaScript | Run a capped number of normal fixture clients against a local game server and measure latency. |
| E27-002 | Bounded load | P2 | Go + JavaScript | Verify cleanup leaves no fixture sockets or sessions behind after the run. |
| E28-001 | Offline and caching | P0 | JavaScript + Playwright | Loss of network updates the HUD and the supported guest path remains usable. |
| E28-002 | Offline and caching | P0 | JavaScript + Playwright | Restore connection or cached assets and verify the expected revision loads. |
| E29-001 | Observability | P1 | Python + Ruby | Link a synthetic failure to its case ID and revision in a readable log. |
| E29-002 | Observability | P1 | Python + Ruby | Check that the final run result distinguishes failure, skip, retry, and pass. |
| E30-001 | Build and reproducibility | P0 | Bash + PowerShell | Install from the existing lockfiles and build from a clean checkout. |
| E30-002 | Build and reproducibility | P0 | Bash + PowerShell | Compare portable manifests and asset checksums where byte equality is expected. |
| E31-001 | Dependencies and provenance | P1 | YAML + Python | Review changes to action pins and dependency lockfiles. |
| E31-002 | Dependencies and provenance | P1 | YAML + Python | Confirm build evidence links artifacts to the exact checked-out source. |
| E32-001 | Release and rollback | P1 | Bash + PowerShell | Exercise a documented rollback in a disposable local target. |
| E32-002 | Release and rollback | P1 | Bash + PowerShell | Verify a simulated failed release leaves the previous validated build selectable. |
| E33-001 | Backup and restore | P1 | Python + Java | Restore a synthetic save snapshot and compare record counts and key invariants. |
| E33-002 | Backup and restore | P1 | Python + Java | Measure missing fixture data and recovery time against a declared test objective. |
| E34-001 | Runner policy and service cost | P0 | Python + YAML | Exercise the existing runner-policy checker on representative workflow fixtures. |
| E34-002 | Runner policy and service cost | P0 | Python + YAML | Verify normal CI uses the demo emulator and local service fixtures. |
| E35-001 | Asset integrity | P1 | Rust + JavaScript | Check GLB container length, expected chunks, and referenced textures against fixtures. |
| E35-002 | Asset integrity | P1 | Rust + JavaScript | Confirm model and sound manifests identify the revision used by a built game. |
| E36-001 | Generated input testing | P2 | Rust + TypeScript | Generate bounded benign model and save variations and record failing seeds. |
| E36-002 | Generated input testing | P2 | Rust + TypeScript | Run catalog parsers on mixed valid and unsupported formats with stable error results. |
| E37-001 | Owner playtesting | P0 | Manual | Record the owner’s desktop first-playable checklist against the exact build. |
| E37-002 | Owner playtesting | P0 | Manual | Capture observed friction and link the corresponding canonical issues. |
| E38-001 | Time and flaky tests | P0 | JavaScript + Python | Replay an isolated flaky browser scenario and retain each attempt outcome. |
| E38-002 | Time and flaky tests | P0 | JavaScript + Python | Freeze fixture clocks across a reset boundary and assert deterministic results. |
| E39-001 | Content provenance | P1 | Ruby + Python | Check that distributable assets resolve to source and license records. |
| E39-002 | Content provenance | P1 | Ruby + Python | Verify build output retains required attributions. |
| E40-001 | Future adapters | P2 | C# + Kotlin | When a second client exists, run it against the same versioned fixture contract. |
| E40-002 | Future adapters | P2 | C# + Kotlin | When a new backend exists, compare supported save readback with the existing adapter. |
