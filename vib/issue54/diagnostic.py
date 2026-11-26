"""Diagnostic replay of original lifecycle tests; no source files modified."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from test_core import original, safe_git, safe_read

class Results(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed_ids = []
    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed_ids.append(test.id())

if __name__ == "__main__":
    with patch.object(original.GitApi, "git", safe_git), patch.object(original.GitApi, "read", safe_read):
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(original.LifecycleTests)
        expected = {test.id() for test in suite}
        if len(expected) != 13:
            raise RuntimeError("Unexpected original test inventory")
        result = unittest.TextTestRunner(verbosity=2, resultclass=Results).run(suite)
        out = Path(os.environ["RUNNER_TEMP"]) / "issue54"
        out.mkdir(exist_ok=True)
        (out/"diagnostic-identities.json").write_text(json.dumps(result.passed_ids)+"\n",encoding="utf-8")
        raise SystemExit(0 if result.wasSuccessful() and set(result.passed_ids)==expected and len(result.passed_ids)==len(expected) else 1)
