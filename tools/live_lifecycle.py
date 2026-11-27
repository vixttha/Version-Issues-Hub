"""One-time real remote lifecycle acceptance; scoped to the public clouds pilot only."""
import hashlib
import json
import os
import subprocess
import sys
from tools import install, session, lifecycle
from tools.pilot_refs import ensure_recovery_ref

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
    resume = os.environ.get("VIB_RESUME_SHA")
    prepared = os.environ.get("VIB_PREPARED_SHA")
    if prepared:
        install.require(install.SHA, prepared, "prepared upgraded revision")
        assert resume and install.read_ref(api,prefix,install.BRANCH) == prepared
    if resume:
        install.require(install.SHA, resume, "exact recovered install")
        assert install.read_ref(api,prefix,install.BRANCH) == (prepared or resume)
    else:
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
    if resume:
        sha = resume
        commit = api.request("GET",prefix+"/git/commits/"+sha)
        assert commit["sha"] == sha and [p["sha"] for p in commit["parents"]] == [PRODUCT]
        _, entries = lifecycle.tree_entries(api,prefix,sha)
        expected = set(install.source_files(api,OLD)) | {"vib-install.json",session.LEDGER,session.HANDOFF}
        assert {p for p,v in entries.items() if v[0] != "tree"} == expected
    else:
        plan = cli("tools.install",*args)
        assert plan["status"] == "planned"
        assert install.read_ref(api,prefix,install.BRANCH) is None
        first = cli("tools.install",*args,"--apply")
        assert first["status"] == "installed"
        sha = first["installed_sha"]
    if prepared:
        # Independently reconstruct the exact expected upgraded tree from the archived old commit.
        old_manifest = json.loads(install.read_text(api,prefix,"vib-install.json",sha))
        assert old_manifest["source_sha"] == OLD and old_manifest["target_repository_id"] == TARGET_ID
        assert json.loads(install.read_text(api,prefix,session.LEDGER,sha))["issues"] == []
        assert json.loads(install.read_text(api,prefix,session.HANDOFF,sha))["active"] is None
        parent = api.request("GET",prefix+"/git/commits/"+prepared)
        assert [p["sha"] for p in parent["parents"]] == [sha]
        _, old_tree = lifecycle.tree_entries(api,prefix,sha)
        _, actual = lifecycle.tree_entries(api,prefix,prepared)
        new_files = install.source_files(api,new)
        expected_manifest = {**old_manifest,"source_sha":new,"package_files_sha256":lifecycle.digest_files(new_files)}
        expected_leaves = {p:v for p,v in old_tree.items() if v[0] != "tree"}
        expected_leaves.update({p:("blob","100644",lifecycle.blob_id(s)) for p,s in new_files.items()})
        expected_leaves["vib-install.json"] = ("blob","100644",lifecycle.blob_id(install.render(expected_manifest)))
        assert {p:v for p,v in actual.items() if v[0] != "tree"} == expected_leaves
    else:
        initial = session.load(api,TARGET,sha)
        assert initial["ledger"]["issues"] == [] and initial["handoff"]["active"] is None
        assert initial["manifest"]["source_sha"] == OLD
    state_paths = (session.LEDGER,session.HANDOFF)
    before = {p:hashlib.sha256(install.read_text(api,prefix,p,sha).encode()).hexdigest() for p in state_paths}
    duplicate = cli("tools.install",*args,"--apply",expect_fail=True)
    assert "already exists" in duplicate
    up_args = ("--expected-sha",sha,"upgrade","--source-sha",new)
    if prepared:
        final = prepared
    else:
        upgrade_plan = cli("tools.lifecycle",*up_args)
        assert upgrade_plan["status"] == "planned"
        assert install.read_ref(api,prefix,install.BRANCH) == sha
        upgraded = cli("tools.lifecycle",*up_args,"--apply","--owner-approved","--prepare-only")
        assert upgraded["status"] == "prepared" and upgraded["ref_moved"] is False
        assert install.read_ref(api,prefix,install.BRANCH) == sha
        print(install.render({**upgraded,"kind":"live_remote_upgrade_prepared","initial_install":sha,
            "run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"]}),end="")
        return
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
    # Prove the archived commit can be restored under a separate pilot-only ref, never delete the install.
    recovery = ensure_recovery_ref(api, prefix, final)
    assert lifecycle.tree_entries(api,prefix,final)[0] == lifecycle.tree_entries(api,prefix,install.read_ref(api,prefix,recovery))[0]
    resumed = cli("tools.session","--expected-sha",final,"inspect")
    assert resumed["installed_sha"] == final and resumed["status"] == "head_scope_required"
    print(install.render({"kind":"live_remote_cli_lifecycle","repository":TARGET,"repository_id":TARGET_ID,
        "source_before":OLD,"source_after":new,"initial_install":sha,"upgraded_install":final,
        "archive_branch":archive["archive_branch"],"archive_sha":final,"recovery_branch":recovery,"recovery_sha":final,"state_sha256":before,
        "product_before":PRODUCT,"product_after":PRODUCT,"duplicate_install_refused":True,
        "stale_upgrade_refused":True,"fresh_process_recovered":True,"live_deletion_performed":False,
        "recovered_prior_install":bool(resume),"run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"]}),end="")

if __name__ == "__main__":
    main()
