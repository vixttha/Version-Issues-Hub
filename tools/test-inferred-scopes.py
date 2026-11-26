"""Regression tests for nested callbacks, shadowing, and fail-closed inference."""
import ast
import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("audit",Path(__file__).with_name("audit-inferred-graphs.py"))
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

def resolve(code,name,line):
    tree=ast.parse(code)
    parents={c:p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load) and n.id==name and n.lineno==line)
    return audit.resolve_name(node,name,parents)

class ScopeTests(unittest.TestCase):
    def test_nested_same_names(self):
        code="def one():\n def race(): pass\n api.request=race\ndef two():\n def race(): pass\n api.request=race\n"
        self.assertEqual(resolve(code,"race",3),("definition",2))
        self.assertEqual(resolve(code,"race",6),("definition",5))
    def test_lambda_parameter(self):
        self.assertEqual(resolve("def ref(): pass\nx=lambda ref: api.read(ref)\n","ref",2),("parameter",2))
    def test_module_not_function(self):
        self.assertEqual(resolve("from tools import install\ndef run():\n patch.object(install,'x')\n","install",3),("module",1))
    def test_shadowing_fails_closed(self):
        self.assertEqual(resolve("def race(): pass\ndef run():\n race=unknown\n api.request=race\n","race",4),("other",3))
    def test_rebinding_is_ambiguous(self):
        self.assertEqual(resolve("def run():\n def race(): pass\n race=unknown\n api.request=race\n","race",4),("ambiguous",None))
    def test_module_callback(self):
        self.assertEqual(resolve("def f(): pass\ndef run():\n call(f)\n","f",3),("definition",1))
    def test_class_not_lexical_scope(self):
        self.assertEqual(resolve("def f(): pass\nclass X:\n def f(self): pass\n def run(self):\n  call(f)\n","f",5),("definition",1))

if __name__=="__main__":unittest.main()
