"""Owner-controlled Standard VIB package upgrades and non-destructive retirement preparation."""
import argparse
import hashlib
import os
from tools import checkpoint, install, session

def tree_entries(api, prefix, sha, *, commit=None):
    if commit is None:
        commit = api.request("GET", prefix + "/git/commits/" + sha)
    commit = install.response_object(commit, "commit")
    if commit.get("sha") != sha:
        raise ValueError("Commit identity mismatch")
    tree = install.require(install.SHA, install.response_object(commit.get("tree"), "commit tree").get("sha"), "tree SHA")
    result = install.response_object(api.request("GET", prefix + "/git/trees/" + tree + "?recursive=1"), "tree")
    if result.get("sha") != tree or result.get("truncated") is not False:
        raise ValueError("Tree is incomplete")
    entries = {}
    modes = {"blob": ("100644", "100755", "120000"), "tree": ("040000",), "commit": ("160000",)}
    for item in install.response_rows(result.get("tree"), "tree entries"):
        path, kind, mode = item.get("path"), item.get("type"), item.get("mode")
        if (not isinstance(path, str) or any(part in ("", ".", "..") for part in path.split("/"))
                or "\0" in path or not isinstance(kind, str) or mode not in modes.get(kind, ())):
            raise install.MalformedResponse("Malformed GitHub tree entry")
        blob = install.require(install.SHA, item.get("sha"), "tree entry SHA")
        if path in entries:
            raise ValueError("Duplicate tree path")
        entries[path] = (kind, mode, blob)
    return tree, entries

def digest_files(files):
    return {p: hashlib.sha256(s.encode("utf-8")).hexdigest() for p,s in files.items()}

def blob_id(value):
    raw = value.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def idle_state(api, target, expected_sha, *, preserve_staged=False):
    install.require(install.SHA, expected_sha, "expected installed SHA")
    state = session.load(api, target, expected_sha)
    if state["manifest"].get("enforcement") != "disabled":
        raise ValueError("Disable and independently revoke enforced mode before lifecycle changes")
    if session.pending_closure(state["handoff"]) is not None:
        raise ValueError("Reconcile unresolved closure before lifecycle changes")
    if session.active_rows(state["handoff"]) or any(
            row["state"] == "in_progress" or (row["state"] == "staged" and not preserve_staged)
            for row in state["ledger"]["issues"]):
        raise ValueError("Finish active work and reconcile staged issues before lifecycle changes")
    return state

def current(api, state):
    manifest, prefix = state["manifest"], state["prefix"]
    meta = api.request("GET", prefix)
    if (meta.get("id") != manifest["target_repository_id"]
            or meta.get("full_name") != manifest["target_repository"]
            or meta.get("default_branch") != manifest["product_branch"]
            or meta.get("archived") or meta.get("disabled")):
        raise ValueError("Target identity or default branch changed")
    if (install.read_ref(api, prefix, install.BRANCH) != state["ref"]
            or install.read_ref(api, prefix, manifest["product_branch"]) != state["product_sha"]):
        raise ValueError("Target refs advanced; reload before applying")

def staged_upgrade_scope(api, state, source_sha):
    """Bind a staged-preserving closure upgrade to immutable evidence and live PR identities.

    This is not integration verification: historical candidates remain stale until
    separately requalified. No stage, issue, receipt or product ref is modified.
    """
    from tools import gate
    if state["handoff"]["schema_version"] != 1:
        raise ValueError("Staged-preserving closure upgrade requires singleton state")
    staged = [r for r in state["ledger"]["issues"] if r["state"] == "staged"]
    if not staged:
        raise ValueError("No staged issues to preserve")
    prefix, manifest = state["prefix"], state["manifest"]
    snapshots, ancestry, scope = {}, set(), []
    def ancestor(old, new):
        if (old, new) not in ancestry:
            gate.check_ancestry(api, prefix, old, new)
            ancestry.add((old, new))
    for row in sorted(staged, key=lambda r:r["issue"]):
        archive = next((r for r in reversed(state["handoff"]["history"])
                        if r["handoff"]["issue"] == row["issue"]), None)
        if archive is None or archive["disposition"] != "staged":
            raise ValueError("Missing latest staged archive; reconcile before upgrade")
        h = archive["handoff"]
        number = h["pull_request"]
        if number not in snapshots:
            pr = session.pr_response(api.request("GET", prefix + "/pulls/" + str(number)))
            repo_id = manifest["target_repository_id"]
            if (not install.same_id(pr.get("number"), number) or pr.get("state") != "open"
                    or pr.get("merged") is not False
                    or pr["base"].get("ref") != manifest["product_branch"]
                    or pr["base"].get("sha") != state["product_sha"]
                    or not install.same_id(pr["base"]["repo"].get("id"), repo_id)
                    or not install.same_id((pr["head"].get("repo") or {}).get("id"), repo_id)):
                raise ValueError("Staged PR identity or disposition changed; reconcile before upgrade")
            snapshots[number] = install.require(install.SHA, pr["head"].get("sha"), "staged PR current head")
        head = snapshots[number]
        ancestor(h["fix_sha"], h["candidate_sha"])
        ancestor(h["candidate_sha"], head)
        scope.append({"issue":row["issue"], "version":row["version"],
                      "archive_sha256":session.closure_digest(archive),
                      "fix_sha":h["fix_sha"], "candidate_sha":h["candidate_sha"],
                      "pull_request":number, "current_head":head})
    return {"repository":manifest["target_repository"], "installed_sha":state["ref"],
            "product_sha":state["product_sha"], "new_source":source_sha, "staged":scope}

def upgrade(api, target, expected_sha, source_sha, *, apply=False, owner_approved=False, prepare_only=False,
            preserve_staged=False, staged_scope_sha256=None):
    if prepare_only and not apply:
        raise ValueError("Prepare-only requires explicitly approved object creation")
    install.require(install.SHA, source_sha, "new pinned source")
    if staged_scope_sha256 is not None and not preserve_staged:
        raise ValueError("Staged scope digest requires explicit preserve-staged mode")
    state = idle_state(api, target, expected_sha, preserve_staged=preserve_staged)
    manifest, prefix = state["manifest"], state["prefix"]
    old_source = manifest["source_sha"]
    if source_sha == old_source:
        raise ValueError("Already on requested source")
    comparison = api.request("GET", install.repo_path(install.SOURCE) + "/compare/" + old_source + "..." + source_sha)
    if comparison.get("status") != "ahead" or comparison["merge_base_commit"]["sha"] != old_source:
        raise ValueError("Upgrade must advance the pinned source history")
    old_files = install.source_files(api, old_source)
    new_files = install.source_files(api, source_sha)
    session.require_closure_compatible_history(state["handoff"], session.supports_closure_execution(new_files))
    scope = None
    if preserve_staged:
        if not session.supports_closure_execution(new_files):
            raise ValueError("Target pin lacks reviewed closure capability")
        scope = staged_upgrade_scope(api, state, source_sha)
        digest = hashlib.sha256(install.render(scope).encode("utf-8")).hexdigest()
        if (staged_scope_sha256 is not None and staged_scope_sha256 != digest) or (apply and staged_scope_sha256 != digest):
            raise ValueError("Exact reviewed staged scope digest required; inspect fresh plan")
    if state["handoff"]["schema_version"] == 2 and not session.supports_parallel_package(new_files):
        raise ValueError("Upgrade target lacks parallel handoff support")
    if not set(old_files).issubset(new_files):
        raise ValueError("Package path removal requires a separate migration")
    if apply:
        install.require_publishable_package(new_files)
    if not {"tools/session.py", "tools/install.py", "tools/lifecycle.py"}.issubset(new_files):
        raise ValueError("Target pin lacks lifecycle-compatible package")
    base_tree, entries = tree_entries(api, prefix, expected_sha)
    for p in old_files:
        if entries.get(p) != ("blob", "100644", blob_id(old_files[p])):
            raise ValueError("Installed package path differs from pinned bytes or mode")
    for p in ("vib-install.json", session.LEDGER, session.HANDOFF):
        if p not in entries or entries[p][:2] != ("blob", "100644"):
            raise ValueError("Invalid state file")
    for p in set(new_files) - set(old_files):
        if p in entries or any(q.startswith(p + "/") for q in entries):
            raise ValueError("New package path collides with adopter content")
        parts = p.split("/")
        for i in range(1,len(parts)):
            parent = "/".join(parts[:i])
            if parent in entries and entries[parent][0] != "tree":
                raise ValueError("New package parent collides with adopter content")
    new_manifest = {**manifest, "source_sha": source_sha, "package_files_sha256": digest_files(new_files)}
    changes = {p:s for p,s in new_files.items() if old_files.get(p) != s}
    changes["vib-install.json"] = install.render(new_manifest)
    plan = {"status":"planned", "operation":"upgrade", "repository":manifest["target_repository"],
            "from_source":old_source,"to_source":source_sha,"expected_sha":expected_sha,
            "changed_paths":sorted(changes),"product_sha":state["product_sha"]}
    if scope is not None:
        plan.update(staged_scope=scope, staged_scope_sha256=digest,
                    staged_integration_verified=False)
    if not apply:
        return plan
    if not owner_approved:
        raise ValueError("Explicit owner approval required")
    current(api, state)
    tree = install.require(install.SHA, api.request("POST", prefix + "/git/trees", {
        "base_tree":base_tree, "tree":[{"path":p,"type":"blob","mode":"100644","content":s}
                                   for p,s in sorted(changes.items())]})["sha"], "upgrade tree")
    commit = install.require(install.SHA, api.request("POST", prefix + "/git/commits", {
        "tree":tree,"parents":[expected_sha],"message":"Owner-approved pinned VIB package upgrade"
    })["sha"], "upgrade commit")
    # Check every leaf before publishing the ref; unchanged state and adopter files must be byte-identical.
    proposed_tree, proposed = tree_entries(api, prefix, commit)
    expected = {p:v for p,v in entries.items() if v[0] != "tree"}
    expected.update({p:("blob","100644",blob_id(s)) for p,s in changes.items()})
    if proposed_tree != tree or {p:v for p,v in proposed.items() if v[0] != "tree"} != expected:
        raise ValueError("Proposed upgrade tree changed unrelated paths")
    current(api,state)
    if scope is not None and staged_upgrade_scope(api, state, source_sha) != scope:
        raise ValueError("Staged scope advanced; inspect fresh plan before publishing")
    current(api,state)
    if prepare_only:
        return {**plan,"status":"prepared","prepared_sha":commit,"tree_sha":tree,"ref_moved":False}
    api.request("PATCH",prefix+"/git/refs/heads/"+install.BRANCH,{"sha":commit,"force":False})
    install.wait_ref(api,prefix,install.BRANCH,commit,expected_sha)
    observed = session.load(api,target,commit)
    if observed["manifest"] != new_manifest or observed["ledger"] != state["ledger"] or observed["handoff"] != state["handoff"]:
        raise ValueError("Upgrade readback mismatch; stop and inspect")
    if observed["product_sha"] != state["product_sha"]:
        raise ValueError("Product advanced concurrently; inspect before retry")
    return {**plan,"status":"upgraded","installed_sha":commit,"tree_sha":tree}

def prepare_retirement(api, target, expected_sha, *, apply=False, owner_approved=False):
    state = idle_state(api,target,expected_sha)
    prefix = state["prefix"]
    archive = "archive/vib/" + expected_sha
    if archive == state["manifest"]["product_branch"]:
        raise ValueError("Archive cannot be product branch")
    existing = install.read_ref(api,prefix,archive)
    if existing not in (None,expected_sha):
        raise ValueError("Archive ref occupied by another revision")
    plan = {"status":"planned","operation":"prepare_retirement","repository":state["manifest"]["target_repository"],
            "archive_branch":archive,"archived_sha":expected_sha,"product_sha":state["product_sha"],
            "installation_removed":False,"manual_removal_required":True}
    if not apply:
        return plan
    if not owner_approved:
        raise ValueError("Explicit owner approval required")
    current(api,state)
    if existing is None:
        api.request("POST",prefix+"/git/refs",{"ref":"refs/heads/"+archive,"sha":expected_sha})
    install.wait_ref(api,prefix,archive,expected_sha)
    current(api,state)
    return {**plan,"status":"archive_verified"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target",required=True)
    p.add_argument("--expected-sha",required=True)
    sub=p.add_subparsers(dest="command",required=True)
    u=sub.add_parser("upgrade")
    u.add_argument("--source-sha",required=True)
    u.add_argument("--prepare-only",action="store_true",help="Create verified objects, never move a ref")
    u.add_argument("--preserve-staged", action="store_true", help="Explicit closure-capability upgrade with staged archives unchanged")
    u.add_argument("--staged-scope-sha256", help="Exact digest from reviewed staged-preserving plan")
    r=sub.add_parser("prepare-retirement")
    for command in (u,r):
        command.add_argument("--apply",action="store_true")
        command.add_argument("--owner-approved",action="store_true")
    args=p.parse_args()
    token=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if args.apply and not token:
        p.error("Apply requires authorized GitHub credential")
    try:
        api=install.GitHub(token)
        opts={"apply":args.apply,"owner_approved":args.owner_approved}
        result=(upgrade(api,args.target,args.expected_sha,args.source_sha,prepare_only=args.prepare_only, preserve_staged=args.preserve_staged,
                       staged_scope_sha256=args.staged_scope_sha256, **opts) if args.command=="upgrade"
                else prepare_retirement(api,args.target,args.expected_sha,**opts))
        print(install.render(result),end="")
    except (ValueError, KeyError, TypeError, OSError, install.ApiError) as exc:
        p.exit(1,f"VIB lifecycle stopped: {exc}\n")

if __name__=="__main__":
    main()
