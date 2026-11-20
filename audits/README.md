# Repository audits

A README HQ audit is a source-based review of a repository's front door. It identifies missing information, stale claims, and useful techniques that may fit other projects. Use the [portfolio audit](2026-11-19-foundation.md) as the first example.

## Inspect a repository

1. Resolve the requested ref to a full SHA. Note repo visibility, branch purpose, applicable instructions, project maturity, and the latest advertised release. Check for alternate README files and docs branches before calling a README missing.
2. Read the complete homepage README. Follow its primary routes through the repo tree into actual manifests, commands, code entry points, docs, tests, workflows, releases, and license. Inspect source branches and version history when they affect a claim.
3. Walk the first task as a new human reader. Verify prerequisites, supported platform, command order, output, and next action. Verify headings, anchors, path and case accuracy, image alternatives, and rendering where possible.
4. Walk the first task as an agent. Verify where to find authoritative instructions, what version and SHA are in scope, which files are entry points, what command proves success, and which write or release actions the owner controls.
5. For findings, distinguish static inspection from a run at the selected ref. Record severity, reader impact, source file and lines or a commit link, verification status, and a specific fix. List untested routes and any access limits.
6. Search the [external technique catalog](https://github.com/vixttha/README-HQ/tree/README-Technique-Library/catalog) by reader task, aliases, and existing IDs. Check the target's docs and CI for existing use. Record what is already present, what the project could adopt, and what applies elsewhere. Extend an existing technique's evidence for corroboration. Add a new record only for a distinct mechanism with evidence.

## Audit record

Keep a dated Markdown record with the repo and ref, examined surfaces, top findings, first-action result, and open verification gaps. For adopted or proposed techniques, list the catalog commit, record ID, applicability, and next change. A scoped inspection leaves the target repo read-only unless edits are requested. Use only public-safe evidence in this public repository.
