"""Diagnostic replay of original lifecycle tests; no source files modified."""
import unittest
from unittest.mock import patch
from test_core import original, safe_git, safe_read

if __name__ == "__main__":
    with patch.object(original.GitApi, "git", safe_git), patch.object(original.GitApi, "read", safe_read):
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(original.LifecycleTests)
        if suite.countTestCases() != 13:
            raise RuntimeError("Unexpected original test inventory")
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        raise SystemExit(0 if result.wasSuccessful() else 1)
