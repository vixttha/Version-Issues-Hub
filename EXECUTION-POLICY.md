# Repository visibility and execution policy

**Discussion draft; private support not approved or qualified.** One VIB product, one dedicated installation branch, same five-stage workflow. Repository visibility, execution location, trust and billing are separate dimensions.

| Profile | Execution | Status |
| --- | --- | --- |
| Public hosted | Eligible free standard GitHub-hosted runners | Existing VIB project policy |
| Private hosted | Standard hosted, included allowance or approved overage | Research |
| Private advanced hosted | Larger hosted runners, authorized metered cost | Research |
| Private self-hosted | Owner-managed isolated PC/VM/server registered with Actions | Research |
| Private direct local | Authorized terminal execution, not an Actions runner | Research |

Public policy: no paid or self-hosted runners for this project. Private installation is distinct from validation. Do not remove existing private-target rejection or claim full compatibility. No private runner setup, private execution, budget change, paid fallback or visibility change authorized.

## Proposed operational rules (subordinate to existing laws)
EXEC-001 establish visibility; EXEC-002 authorize execution environment; EXEC-003 no unapproved expenditure; EXEC-004 respect privacy boundary; EXEC-005 never misrepresent provenance; EXEC-006 fail closed on unsupported or uncertain execution. These are proposals, not six new engineering laws.

## Evidence requirements
Exact tested checkout, actual commands/results, runtime/OS, integrity and owner trust policy for every environment. Hosted and registered self-hosted Actions evidence require exact run/attempt/job; self-hosted labels alone do not prove machine identity, cleanliness or isolation. Direct local execution requires separately qualified provenance and review, never fabricated Actions URLs. Public branch names do not confer privacy. Keep confidential evidence within authorized private scope, including external services and graphs. Owner controls budgets, credential scope, repository visibility and integration. Private artifact-attestation availability varies by plan; no universal paid requirement.

## Open decisions
1. Default private hosted to included allowance?
2. Restrict self-hosted to isolated environments or allow qualified personal PCs?
3. Can direct local evidence qualify final acceptance and under what trust rules?
4. How retain and recover private evidence without disclosure?
5. How handle public/private transitions and historical logs?

## Research references
[GitHub Actions billing](https://docs.github.com/en/actions/concepts/billing-and-usage)
· [Secure use](https://docs.github.com/en/actions/reference/security/secure-use)
· [Self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners)
· [Repository visibility](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
