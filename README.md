# Brand Identity Template

Use the [brand identity kit](brand-identity/README.md) to develop your product's name, slogan, logo, wordmark, visual system and PNG assets. Start with your audience, the product's purpose and the first place the brand will appear.

## Add the kit to an existing project

1. Download the [Brand Identity Template ZIP](https://github.com/vixttha/Brand-Identity-Template/archive/refs/heads/main.zip) and extract it. Copy the entire `brand-identity/` directory, including its license, into your repository. If that directory already exists, review the files before copying them.
2. Link `brand-identity/README.md` from your project's existing `AGENTS.md` or equivalent instructions, or point the agent directly to the [kit README](brand-identity/README.md).
3. In the copied `brand-identity/09-assets/manifest.json`, change `"kind": "template"` to `"kind": "project"`. Leave `assets` empty until you register your exports.
4. Start the [creative brief](brand-identity/01-strategy/brief.md). Follow the [creative direction workflow](brand-identity/01-strategy/creative-direction.md) before generating artwork with @Images.
5. From your repository root, run `python3 brand-identity/verify.py`. On Windows, use `py -3 brand-identity/verify.py`. The verifier uses Python 3.10+ and its standard library.

## Review a template change

The pull request check runs on GitHub's combined base and head commit. The Actions job summary records both parents and the tested commit. Before merging, compare the recorded base and head with the current PR. If either changed, update the PR branch with the latest base and require a passing run for the new combination. Branch push checks cover the source checkout.
