"""Real Git history checked through VIB checkpoint.verify_fix_ancestry."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import test_core as core
from tools import checkpoint
from record import run_suite

class Ancestry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp=tempfile.TemporaryDirectory(prefix="vib54 ancestry ")
        cls.addClassCleanup(temp.cleanup)
        cls.root=Path(temp.name)
        env=dict(os.environ,GIT_CONFIG_NOSYSTEM="1",GIT_CONFIG_GLOBAL=os.devnull,
                 GIT_AUTHOR_NAME="fixture",GIT_AUTHOR_EMAIL="fixture@example.invalid",
                 GIT_COMMITTER_NAME="fixture",GIT_COMMITTER_EMAIL="fixture@example.invalid")
        def git(*args,data=None):
            return subprocess.check_output(["git","-C",str(cls.root),*args],input=data,env=env,stderr=subprocess.PIPE,timeout=20).decode().strip()
        git("init","--bare","--object-format=sha1","-q")
        cls.tree=git("mktree",data=b"")
        cls.blob=git("hash-object","-w","--stdin",data=b"synthetic")
        cls.a=git("commit-tree",cls.tree,"-m","root")
        cls.b=git("commit-tree",cls.tree,"-p",cls.a,"-m","left")
        cls.c=git("commit-tree",cls.tree,"-p",cls.a,"-m","right")
        cls.d=git("commit-tree",cls.tree,"-p",cls.b,"-p",cls.c,"-m","merge")
        cls.e=git("commit-tree",cls.tree,"-m","unrelated")
    def setUp(self):
        cwd=Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir,cwd)
    def test_blob_not_commit(self):
        with self.assertRaisesRegex(ValueError,"not a commit"):
            checkpoint.verify_fix_ancestry("v1.0.0.1",self.blob,self.d)
    def test_tree_not_commit(self):
        with self.assertRaisesRegex(ValueError,"not a commit"):
            checkpoint.verify_fix_ancestry("v1.0.0.1",self.tree,self.d)

def ancestry_case(left,right,allowed):
    def test(self):
        args=("v1.0.0.1",getattr(self,left),getattr(self,right))
        if allowed: checkpoint.verify_fix_ancestry(*args)
        else:
            with self.assertRaisesRegex(ValueError,"not in candidate history"):
                checkpoint.verify_fix_ancestry(*args)
    return test
for left,right,allowed in [
    ("a","b",True),("a","c",True),("a","d",True),("b","d",True),("c","d",True),("d","d",True),
    ("b","c",False),("c","b",False),("d","b",False),("e","d",False),("d","e",False),("b","a",False)]:
    setattr(Ancestry,"test_"+left+"_to_"+right,ancestry_case(left,right,allowed))

if __name__=="__main__":
    run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(Ancestry),14,"ancestry")
