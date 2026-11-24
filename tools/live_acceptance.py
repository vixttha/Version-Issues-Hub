"""Read-only live adoption and cross-template interoperability checks."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tools import install, session

class ReadOnlyGitHub(install.GitHub):
    def request(self, method, path, body=None):
        if method != "GET":
            raise AssertionError("Live acceptance must be read-only")
        return super().request(method, path, body)

api = ReadOnlyGitHub(os.environ.get("GH_TOKEN"))
repo = install.SOURCE
prefix = install.repo_path(repo)
source = os.environ["VIB_TEST_SOURCE"]
# Existing product with no VIB installation: exercise real GitHub reads and package digests.
before = install.read_ref(api, prefix, "main")
plan = install.install(api, repo, source, "v0.0.0")
assert plan["status"] == "planned" and plan["manifest"]["product_baseline_sha"] == before
assert plan["manifest"]["enforcement"] == "disabled"
assert install.read_ref(api, prefix, install.BRANCH) is None
assert install.read_ref(api, prefix, "main") == before
bart = "vixttha/Blender-Agent-Refinement-Toolkit"
state = session.load(api, bart)
report = session.inspect(api, state)
assert report["repository"] == bart and report["owner_merge_required"]
assert not report["evidence_verified"]
# Separate fresh process, no transcript or shared Python state.
# Run the read-only CLI; reject a changed revision rather than comparing mixed state.
second = json.loads(subprocess.check_output([sys.executable, "-m", "tools.session", "--target", bart, "--expected-sha", state["ref"], "inspect"], text=True))
assert second["installed_sha"] == state["ref"] and second["active"] == report["active"]
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
assert "Lydite" in read("starter/test-vault/README.md", pins["Lydite"])
assert "Provenistem" in read("install/branch/AGENTS.md", source)
assert all(not path.startswith(("provenistem/", "veraphify/", "test-vault/")) for path in plan["paths"])
print(json.dumps({
    "kind": "read_only_live_acceptance",
    "source": source, "install_plan_paths": plan["paths"],
    "existing_adopter": bart, "adopter_installed_sha": state["ref"],
    "adopter_package_sha": state["manifest"]["source_sha"],
    "adopter_state": report["status"], "active": report["active"],
    "fresh_process_match": True, "occupied_install_refused": True,
    "template_pins": pins, "archive_source": archive_source,
    "archive_digest": receipt["archive_sha256"], "checkpoint_count": len(receipt["lookups"]),
    "limits": ["no new live installation or deletion", "no independent LLM trial", "no live merge gate", "reference-level cooperation only"]
}, indent=2))
