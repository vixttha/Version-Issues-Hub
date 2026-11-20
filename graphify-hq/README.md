# Graphify HQ

These maps cover six version numbers and their distinct records from the [README HQ version index](../versions/README.md). Each version groups the archived HQ guides, standalone changes, and available homepage records of the same number.

| Version | Map |
| --- | --- |
| v0.0.6 | [Standalone continuation and AlderVale guide](maps/v0.0.6/README.md) |
| v0.0.5 | [AlderVale guide](maps/v0.0.5/README.md) |
| v0.0.4 | [AlderVale guide and two homepage records](maps/v0.0.4/README.md) |
| v0.0.3 | [AlderVale guide and two homepage records](maps/v0.0.3/README.md) |
| v0.0.2 | [AlderVale guide and two homepage records](maps/v0.0.2/README.md) |
| v0.0.1 | [Three HQ records and two homepage records](maps/v0.0.1/README.md) |

Each map has a readable source outline, the Graphify JSON, and a receipt. The receipt records the input commit, file digests, engine version, graph digest, and MCP result. Graph test links point to archive verification or template tests. Historical product-level test evidence remains in its original records.

## Rebuild and verify

Use CPython 3.12 on Linux x86-64 with the pinned source commit in the local Git history. Run from the repository root.

```bash
kit=graphify-hq/template/v0.0.8
python -m pip install --require-hashes --only-binary=:all: --no-deps -r "$kit/requirements.txt"
python -m pip check
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s "$kit" -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 python graphify-hq/version_maps.py --check
```

To inspect a saved map over MCP, run `python -m graphify.serve graphify-hq/maps/v0.0.6/graph.json`. The archived template is [Graphify HQ v0.0.8](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/6af3c2025be3f51e02dca4e4502088c526aae6d1/versions/v0.0.8). [Template files](template/v0.0.8/README.md)

## Veraphify v0.0.9 adoption

Use [Veraphify v0.0.9 at `ed56500`](https://github.com/vixttha/Veraphify/commit/ed5650085e33cf142a37de695757a4df999a7cf3) to import, verify, and look up source-linked archives. This Git SHA is the merged mechanical revision. The [adopter walkthrough](https://github.com/vixttha/Veraphify/blob/ed5650085e33cf142a37de695757a4df999a7cf3/docs/adopter-walkthrough.md) documents the archive commands and limits. The Graphify producer and the Veraphify archive reader have separate version pins.

The public adoption check archives the pinned README HQ checker and verifies the technique registry implementation citation. The README HQ version-map rebuild and original receipts keep their own workflow.

The [public workflow](../.github/workflows/veraphify-adoption.yml) checks the source pin, runs the Graphify MCP check, compares the archive SHA-256, and verifies the citation against the exact Git blob. The disposable archive version `v0.0.0.1` identifies the probe. Each public run retains a small receipt with the adopter SHA, Veraphify SHA, and citation.
