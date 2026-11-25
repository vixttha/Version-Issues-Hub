# Live acceptance isolation — #51

This review-only candidate separates self-install/template checks (core) from the three live adopter checks (external). Both scopes must pass for full live acceptance; neither proves independent agent acceptance. A failed or unavailable case fails its scope, and other cases still record evidence. No adopter writes or automatic installation. The core scope still requires GitHub and pinned same-repository data; Graphify has its own pinned tool dependency. The offline unittest suite is independent of live adopter availability.

The original README-HQ empty-slot plan remains supported; if installed, check the current verified package and duplicate refusal without claiming a new plan. BART historical package proof is separate from current verified package. Only the observed RemoteDisconnected GET failure receives bounded retry in the harness client; subprocess transport errors remain failures. Prior historical receipts remain unchanged.

The workflow now emits two scope-specific artifacts and two jobs instead of one aggregate job. Any release preflight/optional hard-gate policy that binds old live job names, job counts or receipt format must be explicitly reconciled and reverified before integration. Do not treat a green core job as full acceptance. No change to installed runtime, release candidate or owner authority.
