"""Read-only regression contract for pinned VIB source and canonical state."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(os.environ["GITHUB_WORKSPACE"])
def read(root, path):
    return json.loads((root / path).read_text(encoding="utf-8"))
def version(v):
    if not re.fullmatch(r"v0\.0\.0\.[1-9][0-9]*",v):
        raise ValueError("invalid checkpoint")
    return int(v.rsplit(".",1)[1])
def require(ok, message):
    if not ok:
        raise ValueError(message)
def validate(engineering, installed, prior, scope, graph, history, old_history):
    rows = installed["issues"]
    keys = ("issue","version","acceptance")
    def bindings(x):
        return [{k:r[k] for k in keys} for r in x["issues"]]
    require(bindings(engineering)==bindings(installed)==bindings(prior), "immutable mapping or criteria")
    numbers = [version(r["version"]) for r in rows]
    require(numbers==list(range(1,len(rows)+1)), "non-contiguous numeric versions")
    require(len({r["issue"] for r in rows})==len(rows), "duplicate issue")
    require(len(rows)==36 and rows[-1]["version"]=="v0.0.0.36", "wrong candidate version")
    by_issue = {r["issue"]:r for r in rows}
    require({r["issue"] for r in rows if r["state"]=="deferred"}=={12,14,34}, "deferred scope")
    require([r["issue"] for r in rows if r["state"]=="in_progress"]==[40], "active row")
    require(all(r["state"]=="staged" for r in rows if r["issue"] not in {12,14,34,40}), "completed closure not staged")
    require(history["active"]==old_history["active"] and history["active"]["issue"]==40, "active handoff changed")
    require(history["history"][:len(old_history["history"])]==old_history["history"], "history rewritten")
    expected={r["version"] for r in rows if r["issue"]!=40}
    require(len(scope["versions"])==len(expected) and set(scope["versions"])==set(scope["fixes"])==expected, "receipt scope mismatch")
    ids=[f["id"] for f in graph["features"]]
    require(len(ids)==len(expected) and set(ids)=={v.replace(".","-") for v in expected}, "graph scope mismatch")
    latest={}
    for entry in history["history"]:
        latest[entry["handoff"]["issue"]]=entry
    for r in rows:
        if r["state"]=="staged":
            entry=latest[r["issue"]]
            require(entry["disposition"]=="staged" and entry["merged_sha"] is None, "false main integration")
            require(entry["handoff"]["version"]==r["version"] and entry["handoff"]["fix_sha"]==scope["fixes"][r["version"]], "handoff binding")
    return {"checkpoints":len(rows),"code_features":len(ids),"operational_exclusions":["v0.0.0.23"],"staged":32,"deferred":3,"active":40}
class IntegrityTests(unittest.TestCase):
    def setUp(self):
        e,i,p=ROOT/"engineering",ROOT/"installed",ROOT/"prior"
        self.data=[read(e,"ledger/issue-versions.json"),read(i,"ledger/issue-versions.json"),read(p,"ledger/issue-versions.json"),read(e,"ledger/receipt-scope.json"),read(e,"docs/receipt-evidence.json"),read(i,"ledger/handoff.json"),read(p,"ledger/handoff.json")]
    def test_positive(self): self.assertEqual(validate(*self.data)["checkpoints"],36)
    def mutate(self,fn):
        d=copy.deepcopy(self.data);fn(d)
        with self.assertRaises((ValueError,KeyError)): validate(*d)
    def test_changed_binding(self): self.mutate(lambda d:d[1]["issues"][0].update(issue=999))
    def test_changed_criteria(self): self.mutate(lambda d:d[1]["issues"][0]["acceptance"].append("unapproved"))
    def test_assigned_closed(self): self.mutate(lambda d:d[1]["issues"][19].update(state="assigned"))
    def test_false_integration(self): self.mutate(lambda d:d[1]["issues"][0].update(state="integrated"))
    def test_missing_graph(self): self.mutate(lambda d:d[4]["features"].pop())
    def test_duplicate_graph(self): self.mutate(lambda d:d[4]["features"].append(d[4]["features"][0]))
    def test_missing_receipt(self): self.mutate(lambda d:d[3]["versions"].pop())
    def test_history_tamper(self): self.mutate(lambda d:d[5]["history"][0].update(decision="rewritten"))
    def test_active_drift(self): self.mutate(lambda d:d[5]["active"].update(issue=37))
    def test_optional_not_completed(self): self.mutate(lambda d:d[1]["issues"][5].update(state="staged"))
    def test_numeric_order(self): self.assertGreater(version("v0.0.0.36"),version("v0.0.0.9"))
    def test_pinned_package_integrity(self):
        installed=ROOT/"installed"; manifest=read(installed,"vib-install.json")
        for p,digest in manifest["package_files_sha256"].items():
            # Git blob bytes are stable even when Windows checkout translates line endings.
            raw=subprocess.check_output(["git","show","HEAD:"+p],cwd=installed)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)
        self.assertEqual(manifest["source_sha"],"4fc9ac47462101b941ea2f78fc939d42a9de0032")
        self.assertEqual(manifest["enforcement"],"disabled")
if __name__=="__main__":
    unittest.main(verbosity=2)
