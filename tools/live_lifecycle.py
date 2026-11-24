"""One-time real remote lifecycle acceptance; scoped to the public clouds pilot only."""
import hashlib
import json
import os
import subprocess
import sys
from tools import install, session, lifecycle

TARGET = "vixttha/clouds"
TARGET_ID = 1468365268
PRODUCT = "a76b568467ea9ea6a6f9171d85e8ac4c58df81ca"
OLD = "c79217ea4c18d892cd49112bc30b7b28a2fb502b"
PILOT = "refs/heads/ops/vib-phase4-cli-pilot"

def main():
    if (os.environ.get("GITHUB_REPOSITORY") != TARGET or os.environ.get("GITHUB_REF") != PILOT
            or os.environ.get("GITHUB_EVENT_NAME") != "push"):
        raise ValueError("Not the authorized pilot push")
    new = install.require(install.SHA, os.environ["VIB_TEST_SOURCE"], "reviewed candidate")
    checkout = subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    assert checkout == new
    api = install.GitHub(os.environ["GH_TOKEN"])
    prefix = install.repo_path(TARGET)
    meta = api.request("GET",prefix)
    assert meta["id"] == TARGET_ID and meta["full_name"] == TARGET
    assert meta["private"] is False and meta["default_branch"] == "main"
    assert install.read_ref(api,prefix,"main") == PRODUCT
    assert install.read_ref(api,prefix,install.BRANCH) is None, "Pilot already installed; inspect rather than retry"
    def cli(module,*args, expect_fail=False):
        p = subprocess.run([sys.executable,"-m",module,"--target",TARGET,*args],
                           capture_output=True,text=True,check=False)
        if expect_fail:
            assert p.returncode != 0, "Negative control unexpectedly passed"
            return p.stderr.strip()
        if p.returncode:
            raise RuntimeError(p.stderr.strip())
        return json.loads(p.stdout)
    args = ("--source-sha",OLD,"--baseline","v0.0.0")
    plan = cli("tools.install",*args)
    assert plan["status"] == "planned"
    assert install.read_ref(api,prefix,install.BRANCH) is None
    first = cli("tools.install",*args,"--apply")
    assert first["status"] == "installed"
    sha = first["installed_sha"]
    initial = session.load(api,TARGET,sha)
    assert initial["ledger"]["issues"] == [] and initial["handoff"]["active"] is None
    assert initial["manifest"]["source_sha"] == OLD
    state_paths = (session.LEDGER,session.HANDOFF)
    before = {p:hashlib.sha256(install.read_text(api,prefix,p,sha).encode()).hexdigest() for p in state_paths}
    duplicate = cli("tools.install",*args,"--apply",expect_fail=True)
    assert "already exists" in duplicate
    up_args = ("--expected-sha",sha,"upgrade","--source-sha",new)
    upgrade_plan = cli("tools.lifecycle",*up_args)
    assert upgrade_plan["status"] == "planned"
    assert install.read_ref(api,prefix,install.BRANCH) == sha
    upgraded = cli("tools.lifecycle",*up_args,"--apply","--owner-approved")
    final = upgraded["installed_sha"]
    assert upgraded["status"] == "upgraded"
    current = session.load(api,TARGET,final)
    assert current["manifest"]["source_sha"] == new
    assert current["manifest"]["enforcement"] == "disabled"
    assert before == {p:hashlib.sha256(install.read_text(api,prefix,p,final).encode()).hexdigest() for p in state_paths}
    stale = cli("tools.lifecycle",*up_args,"--apply","--owner-approved",expect_fail=True)
    assert "advanced" in stale
    archive = cli("tools.lifecycle","--expected-sha",final,"prepare-retirement","--apply","--owner-approved")
    assert archive["status"] == "archive_verified"
    assert archive["installation_removed"] is False
    assert install.read_ref(api,prefix,archive["archive_branch"]) == final
    assert install.read_ref(api,prefix,install.BRANCH) == final
    assert install.read_ref(api,prefix,"main") == PRODUCT
    resumed = cli("tools.session","--expected-sha",final,"inspect")
    assert resumed["installed_sha"] == final and resumed["status"] == "head_scope_required"
    print(install.render({"kind":"live_remote_cli_lifecycle","repository":TARGET,"repository_id":TARGET_ID,
        "source_before":OLD,"source_after":new,"initial_install":sha,"upgraded_install":final,
        "archive_branch":archive["archive_branch"],"archive_sha":final,"state_sha256":before,
        "product_before":PRODUCT,"product_after":PRODUCT,"duplicate_install_refused":True,
        "stale_upgrade_refused":True,"fresh_process_recovered":True,"live_deletion_performed":False,
        "run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"]}),end="")

if __name__ == "__main__":
    main()
