# Write a README for people and agents

Start by identifying the project, what works now, and the first useful action. Choose the route that matches the product. A game might begin with **Play**, a CLI with **Install and run**, and a template with **Copy and verify**.

| Section | What readers should be able to determine | Source to check |
| --- | --- | --- |
| Overview and status | What the project does, who can use it, and its current maturity | Release notes, product docs, default branch |
| First success | Prerequisites, exact commands, and a recognizable result | Package metadata, launcher or CLI, smoke checks |
| Common tasks | Supported usage, optional configuration, and how to recover from common failures | Configuration examples, docs, tested workflows |
| Development | How to find the code, run the normal checks, and report problems | Package scripts, CI, issue templates |
| Agent navigation | Where rules, source entry points, and validation instructions live | `AGENTS.md` or repository equivalent, source and workflow files |
| Project terms | License or reuse terms and relevant data or artwork provenance | License, attribution and provenance records |

Put role-specific links near the corresponding task. Keep durable repository instructions in the appropriate agent instruction file and link to it when the README needs to route an agent. Write descriptive link text, use one clear heading hierarchy, and describe informative images with meaningful alt text.

## Verify the first useful action

Run the documented commands from a clean checkout with the advertised prerequisites. Record the tested ref or release, commit, platform, invocation, expected result, and observed outcome. For an example that creates a file, verify that file or structure. Mark unavailable environments as unverified. If a route works only on the development branch or a specific release, put that boundary beside the route.

Review how the README renders at standard desktop and narrow widths. Check relative assets, links, anchors, long code blocks, and the accessibility of the text and images. Inspect the exact copy and image paths as they will appear on the target homepage.

## Draft, archive, and publish

1. Record the target project, docs version, target ref and full SHA, and current homepage status. Decide the first reader task and who needs additional routes.
2. Work in a per-version workspace. Record the intended changes, the draft, any images, and the proof for each claim. Link to the matching canonical source of each platform or compatibility statement.
3. When the owner accepts a draft, freeze the exact README and associated assets, record their origin and evidence, and add the version to the index.
4. Use a distinct publication change to promote the accepted README to the homepage when authorized. Recheck relative paths in that destination. Record the resulting commit, public status, and CI evidence if run.
5. Link to the frozen copy when answering a request for a specific version. Report a working draft, an accepted archive, and a published homepage with their observed statuses.

Use [the audit workflow](audits/README.md) to examine an existing repository before drafting. To choose techniques for a reader task, browse the [README Technique Library](https://github.com/vixttha/README-HQ/tree/README-Technique-Library/catalog). An agent can explain the options and help you choose or adapt them. Record the selected IDs, library commit, and verification results with your project.
