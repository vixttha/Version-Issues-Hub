# README HQ agent entry point

Use the `readme-hq` branch as the durable workspace when asked to use README HQ. Resolve its commit and the target repository's ref independently. Read the target's applicable instructions, version metadata, and repository rules at the selected ref.

| Request | Work |
| --- | --- |
| Show the versions | Read [the version index](versions/README.md). Return the requested project's HQ and homepage versions with status and pinned links. |
| Inspect a repository | Follow [the audit workflow](audits/README.md). Give ranked findings with source and validation status, then record any reusable discovery with its source evidence. |
| Draft or update a README | Use [the README guide](README-GUIDE.md). Use the external library to help the owner select or adapt suitable techniques, then draft on a working branch and verify the target entry points. |
| Archive or publish a README | Use the guide's version workflow and the target repository's acceptance rules. Return the approved archive and homepage publication evidence independently. |

Use [README-Technique-Library](https://github.com/vixttha/README-HQ/tree/README-Technique-Library) for reusable technique and combination definitions. Compare a new observation with active and retired library records before suggesting an addition. Record the library commit, selected IDs, applicability, and evidence with the target project.

Use the public branch for public-safe evidence and general techniques. Keep private repository identities, original files, and private evidence with the owner. Verify changes with `python3 tools/check_readme_hq.py` and report what was actually tested. The owner decides homepage publication and releases.
