"""Capture successful case identities directly from unittest; fail closed."""
import json
import os
from pathlib import Path
import unittest

class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.passed=[]
    def addSuccess(self,test):
        super().addSuccess(test)
        self.passed.append(test.id())

def verdict(expected,passed,tests_run,successful):
    return bool(expected) and successful is True and type(tests_run) is int and tests_run==len(expected) and len(passed)==len(expected) and len(set(passed))==len(passed) and set(passed)==set(expected)

def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

def run_suite(suite,count,kind):
    expected=[t.id() for t in flatten(suite)]
    if len(expected)!=count or len(set(expected))!=count:
        raise RuntimeError(f"Unexpected inventory: {len(expected)} expected {count}")
    result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
    out=Path(os.environ["RUNNER_TEMP"])/"issue54"
    out.mkdir(exist_ok=True)
    (out/(kind+"-identities.json")).write_text(json.dumps(result.passed)+"\n",encoding="utf-8")
    raise SystemExit(0 if verdict(expected,result.passed,result.testsRun,result.wasSuccessful()) else 1)
