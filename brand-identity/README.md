# Brand identity kit

A workspace for a project's look, language, and public identity. The owner directs the art. The agent researches, draws, revises, exports, and documents the assets.

| Folder | Contents |
| --- | --- |
| [Strategy](01-strategy/brief.md) | Product, audience, first surface, comparable references, and creative brief |
| [Naming](02-naming/naming.md) | Naming research, aliases, pronunciation, and collision checks |
| [Voice and slogan](03-messaging/voice.md) | Slogan, short descriptor, tone, and claims |
| [Logo](04-logo/logo.md) | Symbol, silhouette, clear space, variants, and minimum size |
| [Wordmark](05-wordmark/wordmark.md) | Lettering, spelling, spacing, and logo lockup |
| [Visual system](06-visual-system/system.md) | Color, typography, layout, iconography, and imagery |
| [Applications](07-applications/applications.md) | UI, README, repository avatar, social, and accessible usage |
| [Review](08-review/review.md) | Visual checks, source/rights records, decisions, and rollout |
| [Assets](09-assets/README.md) | PNG exports and [asset manifest](09-assets/manifest.json) |

## Working session

In your copied kit, set `kind` to `"project"` in [the asset manifest](09-assets/manifest.json). Leave `assets` empty while you work on the brief and confirm the name. Run the commands below from your repository root.

1. Record the product, audience, first placement, and the owner's taste in the [brief](01-strategy/brief.md).
2. Complete the [creative direction workflow](01-strategy/creative-direction.md). Pick an initial logo category, pick an art style, screen categories for brand fit, write three distinct concept examples, rate them on the same criteria, and select one.
3. Present the ranked examples and ask the owner whether the exact product name and wordmark text are locked for this project. The [decision record](01-strategy/creative-decision.json) is the source for both exact strings. Update its `names` before presenting them. Wait for an explicit answer and record that answer in `confirmation`. If either string changes, reconfirm both together.
4. Run `python3 brand-identity/verify.py --ready-for-artwork`. After it passes, use **@Images** to create the selected logo and wordmark PNGs and record their generation brief. Develop the slogan, typography, color, icon, and application guidance around the selected idea.
5. Review exact lettering, silhouette in one color, small-size use, light/dark placement, and the combined lockup. Register the files and record owner feedback. Roll out only to authorized surfaces.

Run `python3 brand-identity/verify.py` to check the kit and any registered PNGs. A new project can pass inventory checks while it waits for confirmation. A project with registered PNGs requires a complete creative decision. Draft inventories can grow one asset at a time. Run `python3 brand-identity/verify.py --ready-for-handoff` before handoff to require both logo and wordmark PNGs. The verifier checks the record and asset files. The owner reviews the cited confirmation and the visual work.
