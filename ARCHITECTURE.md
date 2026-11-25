# Architecture and engineering laws

The [owner-locked principle](https://github.com/vixttha/Version-Issues-Hub/issues/53): **Don't change the way an agent uses VIB. Change the way VIB handles multiple agents using it.**

## Workflow
Head → Worker → Validate → Internal Auditor → Head. These are stages, not mandatory separate agents. Each authorized issue has a stable identity, version, criteria, fix, candidate and evidence. A compatible solo agent can perform the whole workflow. Independent sessions discover repository state instead of requiring chat history or other agents to be online.

Parallel operation is prospective: one active Worker per issue, legacy solo behavior preserved; serialized atomic non-force ref updates protect shared state. Explicit compatible migration, issue-local changes, stale-write refusal, bounded proven contention recovery, no blind retry of ambiguous writes. No fixed team or mandatory coordinating role. 1–100 simulated clients are a qualification target, not measured live LLM capacity. Real host trials remain separate. Agent 5 independent repository audit is advisory research, not an additional required workflow stage.

## Existing six laws (unchanged)
1. **Independence:** Every tool must remain independently installable, usable, versioned and maintained.
2. **Composability:** Installing additional tools expands the agent's capabilities without creating mandatory dependencies.
3. **Portability:** No mandatory AI provider, model, agent harness or paid execution service.
4. **Persistence:** Project knowledge, decisions, progress and evidence survive the termination of an AI session.
5. **Verification:** Development claims must be supported by reproducible, revision-bound evidence.
6. **Owner authority:** The human retains control over scope, architectural decisions, integration and releases.

[Exact law source](https://github.com/vixttha/Version-Issues-Hub/blob/5a6074d77ec37823f81c6d7ebb1f4593d969cd71/ENGINEERING-LAWS.md). Standard validation is advisory; hard enforcement is separate and opt-in, not a Standard release gate. No required branch protection. No automatic integration, release, closure or reassignment. Direct writes may bypass cooperative safeguards; do not advertise enforcement that is absent.

## Ecosystem boundaries
Provenistem owns ideas/features; Lydite owns test organization; Veraphify provides code relationships; README HQ documentation; Brand Identity visual identity. VIB owns issue-version workflow and acceptance. Each remains independently useful. Optional links confer no authority.
