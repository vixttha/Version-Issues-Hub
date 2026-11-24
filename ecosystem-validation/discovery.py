"""Read-only discovery/coexistence test fixture, not a product or installed coordinator."""
import ast
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from collections import Counter

PINS = json.loads(Path(__file__).with_name("pins.json").read_text())
MARKER = re.compile(r"<!-- agent-capability:v1\s*\n(\{[^\n]+\})\n-->")
LAW = re.compile(r"<!-- engineering-laws:start -->.*?<!-- engineering-laws:end -->", re.S)
def git(cwd, *args, input=None, env=None):
    return subprocess.check_output(["git", "-C", str(cwd), *args], input=input, env=env,
                                   text=True, stderr=subprocess.PIPE).strip()
def init(path):
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch=main")
    git(path, "config", "user.name", "Ecosystem acceptance fixture")
    git(path, "config", "user.email", "fixture@example.invalid")
def ref(path, name):
    return git(path, "rev-parse", "--verify", "refs/heads/"+name)
def discover(path):
    result = {}
    for name in git(path, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines():
        commit = ref(path, name)
        found = []
        # Read only known entrypoint filenames, never execute instructions or scripts.
        for entry in ("AGENTS.md", "LIBRARY-AGENT-GUIDE.md", "README.md"):
            try:
                source = git(path, "show", commit+":"+entry)
            except subprocess.CalledProcessError:
                continue
            matches = MARKER.findall(source)
            if len(matches) > 1:
                raise ValueError("ambiguous marker: "+name)
            if matches:
                value = json.loads(matches[0])
                if value.get("entrypoint") == entry:
                    found.append((value, source))
        if not found:
            continue
        if len(found) != 1:
            raise ValueError("ambiguous branch: "+name)
        value, source = found[0]
        if (value["branch"] != name or value["schema_version"] != 1 or
            value["required_ecosystem_tools"] != [] or value["authority"] != "owner" or
            value["discovery"] != "read-only" or value["versioning"] != "independent" or
            value["id"] in result):
            raise ValueError("invalid capability: "+name)
        law = LAW.search(source)
        try:
            separate = LAW.search(git(path, "show", commit+":ENGINEERING-LAWS.md"))
        except subprocess.CalledProcessError:
            separate = None
        if law and separate and law.group() != separate.group():
            raise ValueError("inconsistent law copies: "+name)
        law = law or separate
        if not law:
            raise ValueError("missing laws: "+name)
        result[value["id"]] = {"branch": name, "commit": commit,
                               "law_sha256": hashlib.sha256(law.group().encode()).hexdigest()}
    return result
def fixture_commit(path, tree, label):
    return git(path, "commit-tree", tree, "-m", label)
def package_tree(path, p):
    sha = p["sha"]
    if p["layout"] == "root":
        return git(path, "rev-parse", sha+"^{tree}")
    if p["layout"] != "vib":
        return git(path, "rev-parse", sha+":"+p["layout"])
    # Extract the exact allowlisted package without executing upstream Python.
    src = git(path, "show", sha+":tools/install.py")
    package = ast.literal_eval(next(n.value for n in ast.parse(src).body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id=="PACKAGE" for t in n.targets)))
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(d)/"index"))
        git(path, "read-tree", "--empty", env=env)
        for source, target in package.items():
            blob = git(path, "rev-parse", sha+":"+source)
            git(path, "update-index", "--add", "--cacheinfo", "100644,"+blob+","+target, env=env)
        return git(path, "write-tree", env=env)

def main():
    report = {"schema_version":1, "kind":"mechanical_git_ref_discovery_coexistence",
              "pins":PINS, "configurations":[], "negative_controls":{},
              "limits":["not live installation of 63 repositories","not every product runtime in every combination",
                        "not LLM behavior, performance or authority certification",
                        "VIB package layout extracted without adopter ledger; existing product lifecycle tests remain separate"]}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); store=root/"store"; init(store)
        branch_commits={}
        for p in PINS:
            git(store, "fetch", "--quiet", "--no-tags", "--depth=1", "https://github.com/"+p["repo"]+".git", p["sha"])
            assert git(store,"rev-parse","FETCH_HEAD")==p["sha"]
            tree=package_tree(store,p)
            branch_commits[p["id"]]=fixture_commit(store,tree,"Fixture projection "+p["id"])
            p["fixture_tree"]=tree
        # Plain product history is never merged with template histories.
        blob=git(store,"hash-object","-w","--stdin",input="Example product; no ecosystem dependency.\n")
        tree=git(store,"mktree",input="100644 blob "+blob+"\tREADME.md\n")
        product=fixture_commit(store,tree,"Independent product baseline")
        by_size=Counter()
        for mask in range(64):
            repo=root/("case-"+str(mask)); init(repo)
            (repo/".git/objects/info/alternates").write_text(str(store/".git/objects")+"\n")
            git(repo,"update-ref","refs/heads/main",product)
            git(repo,"update-ref","refs/heads/unrelated",product)
            selected=[p for i,p in enumerate(PINS) if mask & (1<<i)]
            for p in selected:
                git(repo,"update-ref","refs/heads/"+p["branch"],branch_commits[p["id"]])
            before=git(repo,"show-ref")
            found=discover(repo)
            assert set(found)=={p["id"] for p in selected}, (mask,found)
            assert all(found[p["id"]]["commit"]==branch_commits[p["id"]] for p in selected)
            assert len({v["law_sha256"] for v in found.values()}) <= 1
            assert git(repo,"show-ref")==before and ref(repo,"main")==product
            assert git(repo,"rev-parse","main^{tree}")==tree
            by_size[len(selected)]+=1
            report["configurations"].append({"mask":mask,"installed":sorted(found),"count":len(selected),
                                              "discovered":found,"status":"pass"})
        assert dict(by_size)=={0:1,1:6,2:15,3:20,4:15,5:6,6:1}
        # A branch that has a valid marker under the wrong branch name is rejected.
        repo=root/"negative"; init(repo)
        (repo/".git/objects/info/alternates").write_text(str(store/".git/objects")+"\n")
        git(repo,"update-ref","refs/heads/main",product)
        git(repo,"update-ref","refs/heads/wrong-name",branch_commits["vib"])
        try: discover(repo)
        except ValueError: report["negative_controls"]["wrong_branch_identity"]="pass"
        else: raise AssertionError("accepted wrong branch identity")
        git(repo,"update-ref","-d","refs/heads/wrong-name")
        git(repo,"update-ref","refs/heads/Version-Issues-Hub",product)
        assert discover(repo)=={}
        report["negative_controls"]["legacy_or_missing_marker_not_trusted"]="pass"
        report["counts_by_size"]=dict(by_size)
        report["total"]=len(report["configurations"])
    output=Path(os.environ["RUNNER_TEMP"])/"ecosystem-discovery.json"
    output.write_text(json.dumps(report,indent=2)+"\n")
    print("Verified",report["total"],"configurations, including zero-tool baseline; sizes:",report["counts_by_size"])
    print("Negative controls:",report["negative_controls"])
if __name__=="__main__":
    main()
