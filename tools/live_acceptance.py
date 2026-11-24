"""Read-only live adoption and cross-template interoperability checks."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tools import install, session
from tools.acceptance_snapshot import recover_stable
from tools.pilot_refs import verify_self_install

class ReadOnlyGitHub(install.GitHub):
    def request(self, method, path, body=None):
        if method != "GET":
            raise AssertionError("Live acceptance must be read-only")
        return super().request(method, path, body)

def verify_aldervale_install(api):
    target = "vixttha/AlderVale-Pact-of-Ten"
    prefix = install.repo_path(target)
    pin = "da4a15c8a1b86931cdc46b08eb466ec731c83269"
    source = "c79217ea4c18d892cd49112bc30b7b28a2fb502b"
    baseline = "a6c2060b8175f505cc6327ccb5658cc00a458b24"
    meta = api.request("GET", prefix)
    assert meta["private"] is False and meta["id"] == 1458626201
    historical = api.request("GET", prefix + "/git/commits/" + pin)
    assert historical["sha"] == pin
    assert [p["sha"] for p in historical["parents"]] == [baseline]
    manifest = json.loads(install.read_text(api, prefix, "vib-install.json", pin))
    assert manifest["source_sha"] == source and manifest["target_repository"] == target
    assert manifest["target_repository_id"] == meta["id"] and manifest["enforcement"] == "disabled"
    assert manifest["product_baseline_sha"] == baseline and manifest["baseline_version"] == "v0.0.0"
    assert manifest["target_version"] == "v0.0.1"
    files = install.source_files(api, source)
    assert manifest["package_files_sha256"] == {p: hashlib.sha256(s.encode()).hexdigest() for p,s in files.items()}
    assert all(install.read_text(api, prefix, p, pin) == s for p,s in files.items())
    tree = api.request("GET", prefix + "/git/trees/" + historical["tree"]["sha"] + "?recursive=1")
    assert not tree["truncated"]
    assert {x["path"] for x in tree["tree"] if x["type"] == "blob"} == set(files) | {
        "vib-install.json", "ledger/issue-versions.json", "ledger/handoff.json"}
    ledger = json.loads(install.read_text(api, prefix, "ledger/issue-versions.json", pin))
    handoff = json.loads(install.read_text(api, prefix, "ledger/handoff.json", pin))
    assert ledger == {"schema_version":1,"repository":target,"issues":[]}
    assert handoff == {"schema_version":1,"active":None,"history":[]}
    state, report = recover_stable(api, target, requested=13)
    assert report["repository"] == target and report["issue"]["number"] == 13
    assert report["owner_merge_required"] and not report["evidence_verified"]
    try:
        install.install(api, target, source, "v0.0.0")
    except ValueError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("Occupied AlderVale branch was not refused")
    return {"repository": target, "initial_install": pin, "current_install": state["ref"],
            "source": source, "product_parent": baseline, "initial_package_files": len(files),
            "initial_ledger_empty": True, "fresh_process_match": True,
            "actual_issue_lookup": report["issue"]["number"], "occupied_install_refused": True,
            "no_product_writes": True}

def verify_live_cli_plan(api, source):
    target = "vixttha/README-HQ"
    prefix = install.repo_path(target)
    meta = api.request("GET", prefix)
    assert meta["private"] is False
    product = install.read_ref(api,prefix,meta["default_branch"])
    assert product is not None
    # This is a read-only installation plan, not an allocation or migration of README HQ checkpoints.
    before = install.read_ref(api,prefix,install.BRANCH)
    assert before is None
    report = json.loads(subprocess.check_output([sys.executable, "-m", "tools.install",
        "--target", target, "--source-sha", source, "--baseline", "v0.0.6"], text=True))
    assert report["status"] == "planned"
    assert report["manifest"]["source_sha"] == source
    assert report["manifest"]["target_repository_id"] == meta["id"]
    assert report["manifest"]["product_baseline_sha"] == product
    assert report["manifest"]["enforcement"] == "disabled"
    assert install.read_ref(api,prefix,install.BRANCH) is None
    assert install.read_ref(api,prefix,meta["default_branch"]) == product
    return {"repository":target,"mode":"read_only_cli_plan","product_sha":product,
            "source":source,"baseline":"v0.0.6","planned_files":len(report["paths"]),
            "branch_created":False,"issue_assignments_changed":False}

api = ReadOnlyGitHub(os.environ.get("GH_TOKEN"))
repo = install.SOURCE
prefix = install.repo_path(repo)
source = os.environ["VIB_TEST_SOURCE"]
# The successful fresh self-install pilot may have occupied the previously empty slot.
# Verify its historical package without overwriting it or claiming a new install plan.
self_install = verify_self_install(api, repo, source)
bart = "vixttha/Blender-Agent-Refinement-Toolkit"
state, report = recover_stable(api, bart)
# Historical actual BART install is not a new write trial; verify its parent and package pin.
first_install = "cf777c6f4303b766fcc0e4bb9ff6e3ba04ae73b6"
first = api.request("GET", install.repo_path(bart) + "/git/commits/" + first_install)
original = json.loads(install.read_text(api, install.repo_path(bart), "vib-install.json", first_install))
assert [p["sha"] for p in first["parents"]] == [original["product_baseline_sha"]]
assert original["target_repository"] == bart and original["install_branch"] == install.BRANCH
assert original["source_sha"] == state["manifest"]["source_sha"]
assert report["repository"] == bart and report["owner_merge_required"]
assert not report["evidence_verified"]
# Separate fresh process, no transcript or shared Python state.
# Run the read-only CLI; reject a changed revision rather than comparing mixed state.
try:
    install.install(api, bart, source, "v0.0.3")
except ValueError as exc:
    assert "already exists" in str(exc)
else:
    raise AssertionError("Existing installation was not refused")
# Independent template snapshots; the candidate archive pins its own source, not today's moving head.
pins = {
    "Provenistem": "8f20e5f7d1da1436f37ef4f51dd16a280c5fe748",
    "Veraphify": "829fdfae2ac0e8167d740e1a0ad8e8201295c34e",
    "README HQ": "18c99e2e3a9d93ff7cfa37203ae18e88160062dc",
    "Lydite": "e0f2aae2679ecce8c9a6e78cabad4ba0479d17ca",
}
def read(path, pin):
    return install.read_text(api, prefix, path, pin)
archive_source = "3b6951be81d2fc9468b5379aead57c7afc444754"
folder = f"archives/candidates/{archive_source}/45331511873-1"
receipt = json.loads(read(folder + "/candidate-receipt.json", pins["Veraphify"]))
archive = read(folder + "/archive/253596b8399e7853745c1e50d09cfa3e240cedce793165959b45d9ed154e2307.json", pins["Veraphify"])
assert hashlib.sha256(archive.encode()).hexdigest() == receipt["archive_sha256"]
ledger = json.loads(read("ledger/issue-versions.json", archive_source))
assert set(receipt["lookups"]) == {item["version"].replace(".", "-") for item in ledger["issues"]}
assert receipt["status"] == "candidate_only" and receipt["source"] == archive_source
assert "VIB remains independent of Provenistem" in read("PROJECT.md", pins["Provenistem"])
assert "VIB remains independent of Provenistem" in read("workspace/v0.0.1/DRAFT.md", pins["README HQ"])
assert "Lydite Test Vault" in read("README.md", pins["Lydite"])
assert "Verify execution receipts" in read("starter/test-vault/README.md", pins["Lydite"])
assert len(read("starter/test-vault/verify_receipts.py", pins["Lydite"])) > 0
assert "Provenistem" in read("install/branch/AGENTS.md", source)
assert all(not path.startswith(("provenistem/", "veraphify/", "test-vault/")) for path in self_install["candidate_package_paths"])
print(json.dumps({
    "kind": "read_only_live_acceptance",
    "readme_hq_cli_plan": verify_live_cli_plan(api, source),
    "aldervale": verify_aldervale_install(api),
    "source": source, "install_plan_paths": self_install["install_plan_paths"],
    "self_install": self_install,
    "existing_adopter": bart, "adopter_installed_sha": state["ref"],
    "historical_install_sha": first_install, "historical_product_parent": original["product_baseline_sha"],
    "adopter_package_sha": state["manifest"]["source_sha"],
    "adopter_state": report["status"], "active": report["active"],
    "fresh_process_match": True, "occupied_install_refused": True,
    "template_pins": pins, "archive_source": archive_source,
    "archive_digest": receipt["archive_sha256"], "checkpoint_count": len(receipt["lookups"]),
    "limits": ["this job verifies prior live installations, no writes or deletion", "no independent LLM trial", "no live merge gate", "reference-level cooperation only"]
}, indent=2))
