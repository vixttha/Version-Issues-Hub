"""Test evidence verdict with explicit positive and adversarial controls."""
import sys
import unittest
from record import verdict,run_suite
class Evidence(unittest.TestCase):
    def test_valid(self): self.assertTrue(verdict(["a","b"],["b","a"],2,True))
    def test_zero(self): self.assertFalse(verdict([],[],0,True))
    def test_duplicate(self): self.assertFalse(verdict(["a","b"],["a","a"],2,True))
    def test_wrong_identity_same_count(self): self.assertFalse(verdict(["a","b"],["a","c"],2,True))
    def test_missing(self): self.assertFalse(verdict(["a","b"],["a"],2,True))
    def test_extra(self): self.assertFalse(verdict(["a"],["a","b"],2,True))
    def test_failed(self): self.assertFalse(verdict(["a"],["a"],1,False))
    def test_wrong_count(self): self.assertFalse(verdict(["a"],["a"],0,True))
    def test_bool_count(self): self.assertFalse(verdict(["a"],["a"],True,True))
    def test_truthy_success(self): self.assertFalse(verdict(["a"],["a"],1,1))
    def test_skip(self): self.assertFalse(verdict(["a"],[],1,True))
    def test_expected_failure(self): self.assertFalse(verdict(["a"],[],1,True))
if __name__=="__main__":
    run_suite(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]),12,"evidence")
