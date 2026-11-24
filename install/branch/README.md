# Version-Issues-Hub

This branch is VIB's standalone installation, not the product branch. Do not merge it into the product branch. Read [vib-install.json](vib-install.json) for the pinned package and adopter identity, [WORKFLOW.md](WORKFLOW.md) for the owner-approved workflow, and [the ledger](ledger/issue-versions.json) for this repository's assignments.

Run `python tools/checkpoint.py check` in this branch to validate the ledger. GitHub issues and the ledger retain project history. A baseline such as v0.0.0 uses v0.0.0.1 onward to build v0.0.1. Merge enforcement is disabled until explicitly configured and verified by the owner.
