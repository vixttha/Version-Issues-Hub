import unittest
from archive_scope import scope

class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.versions = [f"v0.0.0.{i}" for i in range(1,37)]
        self.selected = [v for v in self.versions if v != "v0.0.0.23"]
        self.features = [{"id": v.replace(".", "-")} for v in self.selected]
    def test_two_shards(self):
        self.assertEqual([32,3], list(map(len,scope(self.versions,self.selected,self.features))))
    def test_missing(self):
        with self.assertRaises(ValueError): scope(self.versions,self.selected[:-1],self.features[:-1])
    def test_duplicate(self):
        with self.assertRaises(ValueError): scope(self.versions,self.selected,self.features+[self.features[0]])
    def test_operational_feature_included(self):
        with self.assertRaises(ValueError): scope(self.versions,self.versions,self.features+[{"id":"v0-0-0-23"}])
    def test_unknown_feature(self):
        with self.assertRaises(ValueError): scope(self.versions,self.selected,self.features[:-1]+[{"id":"v0-0-0-99"}])
    def test_duplicate_ledger(self):
        with self.assertRaises(ValueError): scope(self.versions+[self.versions[0]],self.selected,self.features)
if __name__ == "__main__": unittest.main()
