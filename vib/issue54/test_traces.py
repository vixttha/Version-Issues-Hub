"""Deterministic model-based stress tests for the current single-lane product.

Each seed is one named test; inner operations are not counted as extra tests.
"""
import copy
import random
import unittest
import test_completion as fixtures
from tools import checkpoint,session
from record import run_suite

s=fixtures.s

class Traces(unittest.TestCase):
    def allocation(self,seed):
        rng=random.Random(seed)
        ledger=s.state()["ledger"]
        model={}
        lines=["v1.0.2","v1.0.9","v1.0.10","v2.0.0"]
        counters=dict.fromkeys(lines,0)
        for issue in rng.sample(range(1,10000),128):
            line=rng.choice(lines)
            before=copy.deepcopy(ledger)
            counters[line]+=1
            expected=line+"."+str(counters[line])
            criteria=["accept issue "+str(issue)]
            self.assertEqual(checkpoint.register(ledger,issue,line,criteria),(expected,True))
            model[issue]=expected
            self.assertEqual(checkpoint.bindings(ledger),model)
            checkpoint.check_history(ledger,before)
            replay=copy.deepcopy(ledger)
            self.assertEqual(checkpoint.register(ledger,issue,line,criteria),(expected,False))
            self.assertEqual(ledger,replay)
            wrong=next(x for x in lines if x!=line)
            with self.assertRaises(ValueError):
                checkpoint.register(ledger,issue,wrong,criteria)
            self.assertEqual(ledger,replay)
        self.assertEqual(len(ledger["issues"]),128)
        numeric=[tuple(map(int,row["version"][1:].split("."))) for row in ledger["issues"]]
        self.assertEqual(numeric,sorted(numeric))
    def workflow(self,seed):
        rng=random.Random(seed)
        api=s.Fake(); state=s.state(); model={}
        def apply(call,*args,**kw):
            old=copy.deepcopy(state)
            ledger,handoff=call(api,state,*args,**kw)
            self.assertEqual(state,old)
            checkpoint.check_history(ledger,old["ledger"])
            self.assertEqual(handoff["history"][:len(old["handoff"]["history"])],old["handoff"]["history"])
            session.validate_handoff(handoff,ledger)
            state["ledger"],state["handoff"]=ledger,handoff
            active=handoff["active"]
            in_progress=[x["issue"] for x in ledger["issues"] if x["state"]=="in_progress"]
            self.assertEqual(in_progress,[active["issue"]] if active else [])
        for index,issue in enumerate(rng.sample(range(1,10000),12),1):
            api.pr.update(state="open",merged=False,head={"sha":s.CANDIDATE})
            criteria=["accept "+str(issue)]
            apply(session.claim,issue,criteria,"Fix")
            expected="v1.0.6."+str(index)
            model[issue]=expected
            self.assertEqual(state["handoff"]["active"]["version"],expected)
            before=copy.deepcopy(state)
            with self.assertRaises(ValueError):
                session.claim(api,state,10001,["other"],"Other")
            self.assertEqual(state,before)
            route=rng.choice(["blocked","deferred","rework","direct","staged"])
            if route in ("blocked","deferred"):
                apply(session.advance,"return",return_to_head=True)
                apply(session.finish,route,"Owner decision")
                self.assertIsNone(state["handoff"]["active"])
                apply(session.claim,issue,criteria,"Resume")
                self.assertEqual(state["handoff"]["active"]["version"],expected)
            apply(session.advance,"candidate",fix=s.FIX,candidate=s.CANDIDATE,pr=8)
            if route=="rework":
                apply(session.advance,"rework",rework=True)
                self.assertEqual(state["handoff"]["active"]["evidence"],[])
                apply(session.advance,"candidate",fix=s.FIX,candidate=s.CANDIDATE,pr=8)
            apply(session.advance,"verified",evidence=[s.RUN])
            apply(session.advance,"Head")
            if route=="staged":
                apply(session.finish,"staged","Owner stages")
                api.pr.update(state="closed",merged=True)
                apply(session.reconcile,issue,"Owner integrates")
            else:
                api.pr.update(state="closed",merged=True)
                apply(session.finish,"integrated","Owner integrates")
            self.assertIsNone(state["handoff"]["active"])
            self.assertEqual(checkpoint.bindings(state["ledger"]),model)
            self.assertTrue(all(x["state"]=="integrated" for x in state["ledger"]["issues"]))
        self.assertEqual(len(state["ledger"]["issues"]),12)
        self.assertEqual(api.writes,[])

def seeded(method,seed):
    def test(self): getattr(self,method)(seed)
    return test
for method in ("allocation","workflow"):
    for seed in (54,56,57,101,257,1024,4096,20261125):
        setattr(Traces,"test_"+method+"_"+str(seed),seeded(method,seed))

if __name__=="__main__":
    run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(Traces),16,"traces")
