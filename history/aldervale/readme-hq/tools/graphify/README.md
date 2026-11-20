# README HQ template maps

[Graphify HQ](../../Graphify%20HQ/README.md) has one folder for each approved README HQ template in the `readme_hq` section of the baseline manifest. The three archived HQ documents are the map inputs. The generator checks the original landing page and guide against their recorded commits and records all three archive blobs in `receipt.json`. Frozen map bytes are independent of the PR merge commit. The Actions run records its exact checkout.

When archiving an approved HQ version, generate its map with the locked Graphify packages using `python tools/graphify/version_maps.py /path/to/new-output`. Add the new folder and the regenerated Graphify HQ index to the archive PR. Open the graph with `python -m graphify.serve 'Graphify HQ/<version>/graph.json'`.

The read-only workflow on the public Ubuntu runner rebuilds every approved version, queries the three source nodes over Graphify MCP, and checks the files byte for byte. If a new version is missing its map, the job log provides the new files and updated index in the `GRAPHIFY_MAPS_EXPORT` lines. The chunks in log order form a base64-encoded gzip JSON object that maps output paths to UTF-8 file contents. Review and commit those files on the archive PR, then verify the rerun.
