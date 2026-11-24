# Brand identity kit

A workspace for a project's look, language, and public identity. The owner directs the art. The agent researches, draws, revises, exports, and documents the assets.

| Folder | Contents |
| --- | --- |
| [Strategy](01-strategy/brief.md) | Product, audience, first surface, comparable references, and creative brief |
| [Naming](02-naming/naming.md) | Naming research, aliases, pronunciation, and collision checks |
| [Voice and slogan](03-messaging/voice.md) | Slogan, short descriptor, tone, and claims |
| [Logo](04-logo/logo.md) | Symbol, silhouette, clear space, variants, and minimum size |
| [Wordmark](05-wordmark/wordmark.md) | Lettering, spelling, spacing, and logo lockup |
| [Visual system](06-visual-system/system.md) | Color, typography, layout, iconography, and imagery |
| [Applications](07-applications/applications.md) | UI, README, repository avatar, social, and accessible usage |
| [Review](08-review/review.md) | Visual checks, source/rights records, decisions, and rollout |
| [Assets](09-assets/README.md) | PNG exports and [asset manifest](09-assets/manifest.json) |

## Working session

In your copied kit, set `kind` to `"project"` in [the asset manifest](09-assets/manifest.json). Leave `assets` empty while you work on the brief and confirm the name. Run the commands below from your repository root.

1. Record the product, audience, first placement, and the owner's taste in the [brief](01-strategy/brief.md).
2. Complete the [creative direction workflow](01-strategy/creative-direction.md). Pick an initial logo category, pick an art style, screen categories for brand fit, write three distinct concept examples, rate them on the same criteria, and select one.
3. Present the ranked examples and ask the owner whether the exact product name and wordmark text are locked for this project. The [decision record](01-strategy/creative-decision.json) is the source for both exact strings. Update its `names` before presenting them. Wait for an explicit answer and record that answer in `confirmation`. If either string changes, reconfirm both together.
4. Run `python3 brand-identity/verify.py --ready-for-artwork`. After it passes, use **@Images** to create the selected logo and wordmark PNGs and record their generation brief. Develop the slogan, typography, color, icon, and application guidance around the selected idea.
5. Review exact lettering, silhouette in one color, small-size use, light/dark placement, and the combined lockup. Register the files and record owner feedback. Roll out only to authorized surfaces.

Run `python3 brand-identity/verify.py` to check the kit and any registered PNGs. A new project can pass inventory checks while it waits for confirmation. A project with registered PNGs requires a complete creative decision. Draft and test exports can be registered as the inventory grows. Run `python3 brand-identity/verify.py --ready-for-handoff` before handoff to require at least one logo PNG and one wordmark PNG, each with manifest status `"approved"`. The verifier checks the record and asset files. The owner reviews the cited confirmation and the visual work.

## Owner-approved engineering ecosystem laws

Decision ENGINEERING-ECOSYSTEM-LAWS-001 (2026-11-24). Mission: Build a toolkit that gives compatible LLM agents a structured engineering environment, rather than building another AI model.

<!-- engineering-laws:start -->
1. **Independence:** Every tool must remain independently installable, usable, versioned and maintained.
2. **Composability:** Installing additional tools expands the agent's capabilities without creating mandatory dependencies.
3. **Portability:** No mandatory AI provider, model, agent harness or paid execution service.
4. **Persistence:** Project knowledge, decisions, progress and evidence survive the termination of an AI session.
5. **Verification:** Development claims must be supported by reproducible, revision-bound evidence.
6. **Owner authority:** The human retains control over scope, architectural decisions, integration and releases.
<!-- engineering-laws:end -->

Remain standalone. Other tools are optional; their absence must not block normal operation. Preserve project-local authority and evidence; never automatically install, merge, synchronize or write to another tool's branch. No mandatory seventh coordinator, paid service or AI provider. Existing product scope remains authoritative. Change these laws only by explicit owner approval.

## Agent capability discovery — v1

<!-- agent-capability:v1
{"schema_version":1,"id":"brand-identity","branch":"Brand-Identity","entrypoint":"README.md","scope":"Brand identity and owner-approved visual assets","required_ecosystem_tools":[],"authority":"owner","discovery":"read-only","versioning":"independent"}
-->

A compatible agent may enumerate the target repository's branch refs, resolve this branch to a commit, and read its entry point at that exact commit. Read-only discovery confers no execution, write, integration or release authority. If this branch or marker is absent, the tool is absent or legacy/unverified; continue independently. Check the target's own instructions and owner scope before any action. The marker describes a capability, not a required registry or package version.

Installation convention: human or agent selects a reviewed exact source SHA, checks the dedicated target branch and collisions, follows this product's own installation guide, and records source/target SHA and preserved product state. Never merge a template workspace wholesale into product source. Existing installations require explicit reviewed upgrades; preserve local records and prior receipts. Optional evidence links do not authorize writes. No mandatory coordinator or other ecosystem tool.
