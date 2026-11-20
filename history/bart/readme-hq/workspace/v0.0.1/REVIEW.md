# Public README v0.0.1 publication checklist

- [x] Content grounded in the v0.0.1 foundation branch `45726472fbe7f32de32f87426dc0b21b8fc1e8f7`.
- [x] Planned functionality clearly distinguished from the limited implemented candidate.
- [x] Neutral identity; no private biographical details or external hosted agents.
- [x] Documentation workspace isolated from `main` and Graphify HQ.
- [ ] Recheck the current feature head SHA and required application files immediately before publication.
- [ ] Validate exact application candidate CI, including real Blender tests and Windows/Linux results, without assuming the workflow passed.
- [ ] Confirm the implementation is integrated into `main` before publishing CLI instructions there.
- [ ] Run README HQ documentation validation on the exact candidate commit; record the public-hosted-runner receipt.
- [ ] Prepare separate publication PR with only approved `README.md` and explicitly approved assets.
- [ ] Review PR diff, links, conflicts, and approval against current `main`.
- [ ] Obtain explicit owner publication approval; archive the exact accepted text and changelog.

**Blocker:** `main` currently contains only a heading README. The command examples depend on implementation code absent from `main`. Do not merge documentation to main before the matching application is available.
