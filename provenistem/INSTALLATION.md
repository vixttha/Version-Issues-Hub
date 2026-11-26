# Provenistem on Lydite-Test-Vault

This library tracks Ideas and Features for the `Lydite-Test-Vault` template workspace in `vixttha/Version-Issues-Hub`. Start at the [library guide](README.md), then open the [Ideas index](ideas/INDEX.md) or [Features index](features/INDEX.md). Use the [agent guide](LIBRARY-AGENT-GUIDE.md) when passing the workspace to an LLM.

This copy was initialized from the [portable Provenistem v0.0.2 package](https://github.com/vixttha/Provenistem/tree/e36fcd6d12633395e9b573228c0797ade9e775b0/packages/provenistem). The catalog starts empty. Record this workspace’s own ideas, features, decisions, and evidence under `provenistem/` on the template branch. When adopting the template into another repository, start a separate local catalog with fresh IDs and evidence.

The library stays with the template branch. A product pull request can link to a pinned record or carry a separately reviewed output. Template and product versioning remain independent.

Source reconciliation: current upstream Provenistem v0.0.2 source `d64d0c73538e79af0292642c1f23bafe2e979ec0` adds engineering-law and standalone discovery documentation. This optional nested copy adopts the six laws, not a second standalone capability marker. The initial pin above remains historical. Schemas, fixtures and license bytes remain unchanged. This draft also carries the already-reviewed VIB host repairs from PR #3/#5: reject non-directory destination parents, preserve exact large-integer identity without Decimal normalization, and corresponding test coverage. These are local candidate repairs, not a new upstream release. Host-specific installation notes, generated indexes and records are outside portable-doc neutrality checks; other Markdown remains checked. Copy tests with tools, docs, templates and license. Do not distribute host records as starter data.


## Reviewed forward synchronization candidate

Upstream source `8230fdb8162ed2ebf2966354563205dd6851f8e4` (`packages/provenistem/`) includes accepted decimal, Unicode and self-contained adoption repairs. This is an exact-source reconciliation, not a new release. Preserve nested discovery, host-neutrality exclusions, blocked-parent guard, stronger diagnostics and large-integer regression. Historical pins above remain intact. Host-owned installation notes and records are not portable copy inputs; full regression testing uses a clean synthetic starter. Populated host records use check and authorized build only. Never distribute host records or overwrite host paths.

Forward repair: restore the missing-destination ancestor check from upstream `f676059bf15e466d18a0d49c317920c8c1160418` (`packages/provenistem/tools/adopter.py`) while retaining the local existing-destination `CONFLICT_PARENT` handling. Focused regression checks both a direct and nested missing child beneath a host file, plus a valid missing path. No host records or existing package license changes.
