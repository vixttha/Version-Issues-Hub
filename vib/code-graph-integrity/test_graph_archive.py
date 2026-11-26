"""Independent Lydite audit: read durable Veraphify graph bytes, never mutate source."""
import hashlib,json,os,subprocess,tempfile,shutil,unittest
from pathlib import Path
ROOT=Path(os.environ["GITHUB_WORKSPACE"])
REPO=ROOT/"candidate"
ARCHIVE=REPO/"archives"
def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args): return subprocess.check_output(["git",*args],cwd=REPO,encoding="utf-8").strip()
def call(r,scope,archive=ARCHIVE,ok=True):
    p=subprocess.run(["node","veraphifiy.mjs","code-graph","--archive",str(archive),"--project","vixttha/Version-Issues-Hub","--version",r["version"],"--scope",scope,"--source",r["source"],"--graph-sha256",r["graph_sha256"]],cwd=REPO,capture_output=True,encoding="utf-8")
    if (p.returncode==0)!=ok: raise AssertionError(p.stderr)
    return json.loads(p.stdout) if ok else None
class Audit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=read(ROOT/"engineering/ledger/issue-versions.json")["issues"]
        cls.fixes=read(ROOT/"engineering/ledger/receipt-scope.json")["fixes"]
        cls.indexes={s:read(ARCHIVE/f/"index.json") for s,f in (("fix","code-graphs"),("cumulative","cumulative-code-graphs"))}
    def test_inventory(self):
        self.assertEqual([r["version"] for r in self.rows],[f"v0.0.0.{i}" for i in range(1,37)])
        for index in self.indexes.values():
            self.assertFalse(index["failures"])
            self.assertEqual([(r["issue"],r["version"]) for r in index["results"]],[(r["issue"],r["version"]) for r in self.rows])
    def test_original_source_pins(self):
        for r in self.indexes["fix"]["results"]:
            if r["issue"]==40:
                self.assertEqual((r["source"],r["preflight_run"],r["release_status"]),("a472e04f4c2cc781c654000d6c0567e703f32791",45724188129,"open"))
            else: self.assertEqual(r["source"],self.fixes[r["version"]])
            self.assertFalse(r["historical_test_claim"])
    def test_cumulative_ancestry(self):
        prefix=set(); previous=None
        for a,b in zip(self.indexes["fix"]["results"],self.indexes["cumulative"]["results"]):
            if a["issue"]!=40: prefix.add(a["source"])
            self.assertEqual(set(b["covered_fix_sources"]),prefix)
            self.assertEqual(b["original_fix_source"],a["source"])
            for required in prefix | ({previous} if previous else set()):
                self.assertEqual(subprocess.run(["git","merge-base","--is-ancestor",required,b["source"]],cwd=REPO).returncode,0)
            previous=b["source"]
        self.assertEqual(previous,"26e9fe8c019a33c5f84f77a37da70925505204e3")
    def test_actual_graph_retrieval(self):
        for scope,folder in (("fix","code-graphs"),("cumulative","cumulative-code-graphs")):
            for r in self.indexes[scope]["results"]:
                with self.subTest(scope=scope,version=r["version"]):
                    path=ARCHIVE/folder/r["version"]
                    self.assertEqual(sha(path/"graph.json"),r["graph_sha256"])
                    self.assertEqual(git("rev-parse",r["source"]+"^{tree}"),r["tree"])
                    self.assertEqual(read(path/"receipt.json"),r)
                    g=read(path/"graph.json")
                    self.assertEqual(call(r,scope),{"receipt":r,"graph":g})
                    ids={x["id"] for x in g["nodes"]}
                    self.assertEqual(len(ids),r["nodes"])
                    self.assertTrue(all(e["source"] in ids and e["target"] in ids for e in g["links"]))
    def test_wrong_source_and_digest(self):
        r=self.indexes["fix"]["results"][0]
        call({**r,"source":"0"*40},"fix",ok=False)
        call({**r,"graph_sha256":"0"*64},"fix",ok=False)
    def test_cross_version_receipt_and_duplicate_index(self):
        r=self.indexes["fix"]["results"][0]
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/"code-graphs";dest.mkdir()
            shutil.copyfile(ARCHIVE/"code-graphs/index.json",dest/"index.json")
            shutil.copytree(ARCHIVE/"code-graphs"/r["version"],dest/r["version"])
            p=dest/r["version"]/"receipt.json";p.write_bytes((ARCHIVE/"code-graphs/v0.0.0.2/receipt.json").read_bytes())
            call(r,"fix",Path(tmp),ok=False)
            shutil.copyfile(ARCHIVE/"code-graphs"/r["version"]/"receipt.json",p)
            idx=read(dest/"index.json");idx["results"][1]=idx["results"][0]
            (dest/"index.json").write_text(json.dumps(idx),encoding="utf-8")
            call(r,"fix",Path(tmp),ok=False)
if __name__=="__main__": unittest.main(verbosity=2)
