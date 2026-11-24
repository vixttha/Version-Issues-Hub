"""Owner-authorized disposable installation trial in the VIB source repository.
Never run on a foreign repository. Never touch an existing install or product ref.
The trial's temporary install branch is removed with a Git lease; archive its full state.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from tools import install, session

REPO = install.SOURCE
PREFIX = install.repo_path(REPO)
OLD = "8af9508e20fa80e6dc312ededc83f4a8007ecf92"
NEW = "c79217ea4c18d892cd49112bc30b7b28a2fb502b"
REF = "refs/heads/" + install.BRANCH
assert os.environ["GITHUB_REPOSITORY"] == REPO
assert os.environ["GITHUB_REF"] == "refs/heads/test/vib-install-lifecycle"
assert os.environ["GITHUB_EVENT_NAME"] == "push"
api = install.GitHub(os.environ["GH_TOKEN"])
output = Path(os.environ["RUNNER_TEMP"]) / "vib-lifecycle"
output.mkdir()
receipt = {"repository": REPO, "old_source": OLD, "new_source": NEW,
           "workflow_sha": os.environ["GITHUB_SHA"], "run": os.environ["GITHUB_RUN_ID"],
           "attempt": os.environ["GITHUB_RUN_ATTEMPT"], "results": {}}
def record(name, value=True):
    receipt["results"][name] = value
    (output / "receipt.json").write_text(install.render(receipt), encoding="utf-8")
record("started")
meta = api.request("GET", PREFIX)
assert meta["full_name"] == REPO and not meta["private"] and meta["default_branch"] == "main"
assert install.read_ref(api, PREFIX, install.BRANCH) is None, "Existing install: refuse"
protected = ["main", "Brand-Identity", "Provenistem", "Veraphify", "Lydite-Test-Vault", "readme-hq", "readme-hq-v0.0.1"]
before = {name: install.read_ref(api, PREFIX, name) for name in protected}
assert all(before.values())
receipt["untouched_refs_before"] = before
owned = None
try:
    plan = install.install(api, REPO, OLD, "v0.0.0")
    assert plan["status"] == "planned" and install.read_ref(api, PREFIX, install.BRANCH) is None
    record("dry_run")
    result = install.install(api, REPO, OLD, "v0.0.0", apply=True)
    owned = result["installed_sha"]
    receipt["installed_sha"] = owned
    assert result["manifest"] == plan["manifest"]
    tree = api.request("GET", PREFIX + "/git/trees/" + result["installed_tree_sha"] + "?recursive=1")
    assert not tree["truncated"]
    assert {e["path"] for e in tree["tree"] if e["type"] == "blob"} == set(plan["paths"])
    assert all(e["mode"] == "100644" for e in tree["tree"] if e["type"] == "blob")
    state = session.load(api, REPO, owned)
    assert state["ledger"]["issues"] == [] and state["handoff"]["active"] is None
    record("actual_install_isolated_tree")
    try:
        install.install(api, REPO, NEW, "v0.0.0", apply=True)
    except ValueError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("Overwrite unexpectedly accepted")
    assert install.read_ref(api, PREFIX, install.BRANCH) == owned
    record("occupied_install_refused")
    # Trial-only state in the temporary branch, not a product decision or an issue mutation.
    ledger, handoff = session.claim(api, state, 9, ["Disposable lifecycle preservation test"], "TRIAL ONLY: preserve state on upgrade")
    save = session.save(api, state, ledger, handoff, apply=True)
    owned = save["installed_sha"]
    state = session.load(api, REPO, owned)
    assert state["handoff"]["active"]["issue"] == 9
    assert session.inspect(api, state)["status"] == "resume"
    record("adopter_state_saved")
    # Manual reviewed upgrade, not a new installer CLI command.
    old_files = install.source_files(api, OLD)
    new_files = install.source_files(api, NEW)
    assert set(old_files) <= set(new_files), "Unexpected removed package paths"
    assert set(new_files).isdisjoint({session.LEDGER, session.HANDOFF, "vib-install.json"})
    assert install.read_ref(api, PREFIX, install.BRANCH) == owned
    manifest = dict(state["manifest"], source_sha=NEW,
                    package_files_sha256={p: hashlib.sha256(s.encode()).hexdigest() for p,s in new_files.items()})
    prior = api.request("GET", PREFIX + "/git/commits/" + owned)
    entries = [{"path": p, "type": "blob", "mode": "100644", "content": s}
               for p,s in {**new_files, "vib-install.json": install.render(manifest)}.items()]
    tree_sha = api.request("POST", PREFIX + "/git/trees", {"base_tree": prior["tree"]["sha"], "tree": entries})["sha"]
    upgraded = api.request("POST", PREFIX + "/git/commits", {
        "message": "TRIAL ONLY: upgrade pinned package; preserve adopter state", "tree": tree_sha, "parents": [owned]})["sha"]
    api.request("PATCH", PREFIX + "/git/refs/heads/" + install.BRANCH, {"sha": upgraded, "force": False})
    owned = upgraded
    check = session.load(api, REPO, owned)
    assert check["ledger"] == state["ledger"] and check["handoff"] == state["handoff"]
    assert check["manifest"] == manifest
    receipt["upgraded_sha"] = owned
    record("manual_upgrade_preserved_state")
    # Export full branch state prior to removal. Never silently discard the local ledger.
    paths = sorted(set(new_files) | {session.LEDGER, session.HANDOFF, "vib-install.json"})
    archived = {p: install.read_text(api, PREFIX, p, owned) for p in paths}
    payload = install.render({"repository": REPO, "installed_sha": owned, "files": archived})
    (output / "installation-archive.json").write_bytes(payload.encode())
    receipt["archive_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    assert json.loads(payload)["files"][session.LEDGER] == install.render(check["ledger"])
    assert json.loads(payload)["files"][session.HANDOFF] == install.render(check["handoff"])
    record("state_exported")
finally:
    if owned is not None:
        # Cleanup ONLY the exact branch this run created and last advanced.
        assert install.read_ref(api, PREFIX, install.BRANCH) == owned, "Concurrent branch change; leave untouched"
        assert api.request("GET", PREFIX)["default_branch"] == "main"
        subprocess.run(["git", "push", "--force-with-lease=" + REF + ":" + owned,
                        "origin", ":" + REF], check=True)
        assert install.read_ref(api, PREFIX, install.BRANCH) is None
        record("lease_checked_removal")
    after = {name: install.read_ref(api, PREFIX, name) for name in protected}
    receipt["untouched_refs_after"] = after
    assert before == after, "Product/template ref changed concurrently; inspect"
    record("product_and_templates_unchanged")
print(install.render(receipt))
