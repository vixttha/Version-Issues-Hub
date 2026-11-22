# Install VIB on a dedicated GitHub branch

[FEAT-000007](../features/records/FEAT-000007.json) records the planned installation feature and links to the VIB dogfood run for the receipt behavior this package needs to carry into another repository.

## Install and discover

Install a pinned copy of the VIB package on a dedicated `Version-Issues-Hub` branch in the adopting repository. The branch holds the workflow contract, installation guides, validation tools, and repository-specific VIB configuration and ledger. Start with an empty adopter ledger and bind it to the adopter's repository and GitHub issue numbers. Preserve assignments when upgrading the package. Check for a branch-name collision before writing and show the owner the incoming source revision and changes. The installation itself preserves the product branch and its files.

The human and agent install paths produce the same receipt with the source package revision, installed branch revision, target repository, and enabled mode. The repository owner can share that receipt as the starting point for a new ChatGPT session or agent harness. The session needs access to the adopted repository and explicitly loads the contract from the installed revision. An owner may add a small discovery link to existing repository instructions if their host supports it. Codex discovers its repository `AGENTS.md` guidance along the checked-out project tree, so a separate branch alone does not provide automatic discovery. [Codex project instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

## What VIB requires

Follow **Head → Worker → Validate → Internal Auditor → Head** with one active Worker. Head accepts the issue and assigns its checkpoint. The Worker links the candidate change, Validate records the exact tested revision and results, and the Internal Auditor checks the scope and evidence. Head owns integration and publication. Each accepted issue keeps its checkpoint through retries. For example, `v0.0.0.1` through `v0.0.0.n` build toward `v0.0.1`. One PR can carry several checkpoints, with a separate receipt for each linked issue and its pinned fix.

GitHub Issues and PRs keep the acceptance and handoff records usable across sessions. Graphify may index the links to the exact revision and evidence. Any other review, incident, or CI tools can supply links when relevant.

## Enforce on the product branch

The branch install provides a guided workflow. The owner separately enables enforcement on the product target by requiring a VIB status check from a trusted publisher, with the validator policy pinned outside the candidate's control. The check validates the current candidate and the host's issue assignments and receipts. Code, test output, and review claims supplied by the candidate are inputs to the check. GitHub rulesets apply the verdict at merge time, including when a person or agent ignores the guide. An authorized bypass remains governed by the owner's GitHub settings. [GitHub required checks and expected sources](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-status-checks-to-pass-before-merging)

The validator can reuse Actions code pinned to an exact commit. Any caller or publisher used for enforcement must be protected so changing the product PR cannot supply its own passing verdict. Requiring a job name alone does not prove that the intended workflow ran. The existing required-check pilot will establish a supported publisher configuration for a disposable public repository before we claim enforcement on an adopter's product branch. [GitHub reusable workflow references](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows#calling-a-reusable-workflow)

## Acceptance proof

Install from a fresh GitHub repository and one that already has product files and agent instructions. Compare the product branch before and after installation, then resume one issue from both ChatGPT and an independent harness. Run the existing two-checkpoint test on standard GitHub-hosted public runners and compare receipts after a docs-only change. Run the ruleset's passing and failing controls, including missing or skipped evidence and an attempted policy change in the candidate. Verify the actual GitHub merge result. Exercise an upgrade and removal while retaining issue history and evidence links.
