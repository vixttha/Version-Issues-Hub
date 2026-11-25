# Product identity — owner approved

Decision VIB-PRODUCT-IDENTITY-001: [canonical record](https://github.com/vixttha/Version-Issues-Hub/issues/9#issuecomment-7172184112).

Version-Issues-Hub (VIB) is a standalone, GitHub-native engineering workflow toolkit installed as the permanent dedicated `Version-Issues-Hub` branch inside an adopter's repository. Compatible AI agents use persistent issue-version checkpoints, durable handoffs, revision-bound verification, safe recovery and owner-controlled acceptance. **VIB manages engineering work, not the agents performing it.**

## Physical installation
The source product lives in its own repository. The adopter's dedicated branch contains the pinned package and adopter-local ledger/handoff. Product source stays on product branches; never merge the installation branch into main. Permanent means long-lived through normal project use, with explicit owner-controlled upgrades, archival and retirement; it does not mean GitHub mechanically prevents deletion. This product-direction reference branch is not an adopter installation.

## Core scope
Issue and checkpoint mapping; stable version allocation; workflow state; persistent history; reproducible receipts; criterion-specific acceptance; transaction integrity; recovery; independent-agent scalability; owner authority. Scalability and automatic contention recovery remain prospective until qualified.

## Non-goals
No AI model, mandatory coordinator, agent supervisor, CI platform, test engine, database, registration service, required separate repository, mandatory cache, or automatic release manager. Optional ecosystem tools add capabilities without becoming runtime dependencies.

## Brand
Name: Version-Issues-Hub. Agent-facing name: VIB. Visual direction: Cobalt Precision; Circuit Industrial v2. Primary slogan: Every issue. A checkpoint. Secondary slogan: Build. Verify. Advance. Product identity defines the promise and boundaries; it does not replace the visual identity or assert commercial clearance. [Release brand clearance](https://github.com/vixttha/Version-Issues-Hub/issues/45) remains separately governed.
