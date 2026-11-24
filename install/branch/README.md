# Version-Issues-Hub

Standalone VIB branch. Do not merge into the product. Start with [AGENTS.md](AGENTS.md) and [WORKFLOW.md](WORKFLOW.md). The installed package pin and target identity are in [vib-install.json](vib-install.json). The [ledger](ledger/issue-versions.json) and [handoff](ledger/handoff.json) belong to the adopter.

Run `python -m tools.session --target OWNER/REPO inspect` in an authorized cloud host to recover the current state. Merge enforcement is disabled unless separately configured and proven by the owner.
