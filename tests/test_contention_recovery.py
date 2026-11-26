"""Bounded contention recovery, using actual Git objects and a simulated API."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools import session, install, lifecycle
from test_lifecycle import GitApi, OLD_FILES, REPO
from test_session import Fake, state

A, B, C = 247, 248, 249

class Remote(GitApi):
    def request(self, method, path, body=None):
        if method == "POST" and path.endswith("/git/commits"):
            self.writes.append((method, path, body))
            args = ["commit-tree", body["tree"]]
            for parent in body["parents"]:
                args.extend(["-p", parent])
            return {"sha": self.git(*args, data=body["message"] + "\n")}
        if method == "GET" and "/issues/" in path:
            return {"number": int(path.rsplit("/", 1)[1]), "state": "open"}
        result = super().request(method, path, body)
        if method == "GET" and "/git/commits/" in path:
            result["parents"] = [{"sha": p} for p in self.git(
                "show", "-s", "--format=%P", result["sha"]).split()]
            result["message"] = self.git("show", "-s", "--format=%B", result["sha"])
        return result

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.api = Remote(tmp.name)
        api = self.api
        package = {**OLD_FILES, "tools/session.py": Path(session.__file__).read_text(encoding="utf-8")}
        manifest = {**api.manifest, "package_files_sha256": lifecycle.digest_files(package)}
        tree = api.tree({"tools/session.py": package["tools/session.py"],
                         "vib-install.json": install.render(manifest)}, api.git("rev-parse", api.old+"^{tree}"))
        pin = api.commit(tree, [api.old])
        api.ref(install.BRANCH, pin)
        self.addCleanup(patch.stopall)
        patch.object(install, "source_files", return_value=package).start()
        patch.object(install, "read_text", side_effect=lambda api,prefix,path,ref:api.read(ref,path)).start()
        patch.object(install.time, "sleep").start()
        s = session.load(api, REPO, pin)
        first = session.claim(api, s, A, ["A"], "A", parallel=True)
        pin = session.save(api, s, *first, True, issue=A)["installed_sha"]
        self.s = session.load(api, REPO, pin)

    def claim(self, s, issue):
        return session.claim(self.api, s, issue, ["test"], "claim")

    def recover(self, plan, issue, **kw):
        return session.recover_save(self.api, REPO, self.s, plan, issue, **kw)

    def inject(self, competing):
        api = self.api
        original = api.request
        def race(method,path,body=None):
            if method == "PATCH":
                api.request = original
                competing()
            return original(method,path,body)
        api.request = race

    def test_automatic_real_git_conflict_preserves_both_claims(self):
        self.inject(lambda: session.save(self.api, self.s, *self.claim(self.s,C),True,issue=C))
        result = self.recover(lambda s:self.claim(s,B),B)
        self.assertEqual(result["contention_retries"],1)
        fresh=session.load(self.api,REPO,result["installed_sha"])
        self.assertEqual([r["issue"] for r in fresh["handoff"]["active"]],[A,B,C])
        self.assertEqual(len(set(r["version"] for r in fresh["ledger"]["issues"])),4)
        self.assertEqual(session.issue_view(fresh["ledger"],fresh["handoff"],A),
                         session.issue_view(self.s["ledger"],self.s["handoff"],A))
        self.assertEqual(self.api.ref("main"),self.api.product)
        self.assertEqual(self.api.read(fresh["ref"],"notes/custom.md"),"keep me\n")

    def test_same_issue_change_stops_without_replaying(self):
        self.inject(lambda: session.save(self.api,self.s,*session.claim(self.api,self.s,B,["test"],"different intent"),True,issue=B))
        with self.assertRaisesRegex(ValueError,"Issue or archive changed"):
            self.recover(lambda s:self.claim(s,B),B)
        latest=session.load(self.api,REPO)
        self.assertEqual([r["issue"] for r in latest["handoff"]["active"]],[A,B])
        self.assertEqual(sum(m=="PATCH" for m,_,_ in self.api.writes),3)

    def test_advance_replans_only_unchanged_issue(self):
        self.inject(lambda: session.save(self.api,self.s,*self.claim(self.s,C),True,issue=C))
        result=self.recover(lambda s:session.advance(self.api,s,"owner decision",issue=A,return_to_head=True),A)
        self.assertEqual(result["contention_retries"],1)
        latest=session.load(self.api,REPO)
        self.assertEqual(session.select_active(latest["handoff"],A)["phase"],"Head")
        self.assertEqual(session.select_active(latest["handoff"],C)["phase"],"Worker")

    def test_prepublication_conflict_recovers_without_repeating_old_patch(self):
        session.save(self.api,self.s,*self.claim(self.s,C),True,issue=C)
        result=self.recover(lambda s:self.claim(s,B),B)
        self.assertEqual(result["contention_retries"],1)
        self.assertEqual(sum(m=="PATCH" for m,_,_ in self.api.writes),3)

    def test_ambiguous_and_rate_limited_writes_never_replay(self):
        for error in (session.HandoffUnconfirmed("a"*40),install.ApiError(403),
                      install.ApiError(422,retry_after=120),install.ApiError(429,retry_after=60)):
            with self.subTest(error=type(error).__name__), patch.object(session,"save",side_effect=error) as save:
                with self.assertRaises(type(error)):
                    self.recover(lambda s:self.claim(s,B),B)
                self.assertEqual(save.call_count,1)

    def test_bounded_exhaustion_no_infinite_retry(self):
        with patch.object(session,"save",side_effect=session.HandoffStale("advanced")) as save, \
             patch.object(session,"load",return_value=self.s), \
             patch.object(session,"retry_scope",return_value=None):
            with self.assertRaisesRegex(ValueError,"budget exhausted"):
                self.recover(lambda s:self.claim(s,B),B)
            self.assertEqual(save.call_count,4)

    def test_unchanged_ref_rejects_422_not_contention(self):
        error=session.HandoffRejected(install.ApiError(422),"a"*40,"b"*40)
        with patch.object(session,"save",side_effect=error) as save:
            with self.assertRaises(session.HandoffRejected):
                self.recover(lambda s:self.claim(s,B),B)
            self.assertEqual(save.call_count,1)

    def test_intermediate_change_then_revert_is_not_safe(self):
        s=self.s
        changed=copy.deepcopy(s["handoff"])
        session.select_active(changed,A)["next_action"]="temporary change"
        tree=self.api.tree({session.HANDOFF:install.render(changed)}, self.api.git("rev-parse",s["ref"]+"^{tree}"))
        middle=self.api.commit(tree,[s["ref"]])
        final=self.api.commit(self.api.git("rev-parse",s["ref"]+"^{tree}"),[middle])
        self.api.ref(install.BRANCH,final)
        fresh=session.load(self.api,REPO)
        with self.assertRaisesRegex(ValueError,"Issue or archive changed"):
            session.retry_scope(self.api,s,fresh,A,session.HandoffStale("advanced"))

    def test_exact_committed_candidate_not_replayed(self):
        result=self.recover(lambda s:self.claim(s,B),B)
        published=result["installed_sha"]
        tree=self.api.git("rev-parse",published+"^{tree}")
        current=session.load(self.api,REPO)
        session.save(self.api,current,*self.claim(current,C),True,issue=C)
        error=session.HandoffRejected(install.ApiError(422),published,tree,result["operation_id"])
        with patch.object(session,"save",side_effect=error) as save:
            result=self.recover(lambda s:self.claim(s,B),B)
        self.assertEqual(result["installed_sha"],published)
        self.assertTrue(result["recovered_response"])
        self.assertEqual(save.call_count,1)

    def test_replan_changed_intent_refused(self):
        session.save(self.api,self.s,*self.claim(self.s,C),True,issue=C)
        def plan(s):
            return session.claim(self.api,s,B,["test"],"original" if s["ref"]==self.s["ref"] else "changed")
        with self.assertRaisesRegex(ValueError,"intent changed"):
            self.recover(plan,B)
        self.assertEqual(sum(m=="PATCH" for m,_,_ in self.api.writes),2)

    def test_three_successive_real_git_conflicts_then_success(self):
        api=self.api
        original=api.request
        competing=iter((250,251,252))
        def race(method,path,body=None):
            if method=="PATCH":
                number=next(competing,None)
                if number is not None:
                    api.request=original
                    current=session.load(api,REPO)
                    session.save(api,current,*self.claim(current,number),True,issue=number)
                    api.request=race
            return original(method,path,body)
        api.request=race
        result=self.recover(lambda s:self.claim(s,B),B)
        self.assertEqual(result["contention_retries"],3)
        latest=session.load(api,REPO)
        self.assertEqual([r["issue"] for r in latest["handoff"]["active"]],[A,B,250,251,252])
        self.assertEqual(len(set(r["version"] for r in latest["ledger"]["issues"])),6)
        self.assertEqual(sum(m=="PATCH" for m,_,_ in api.writes),8)

    def test_finish_archive_is_appended_once_after_conflict(self):
        api=self.api
        result=session.save(api,self.s,*session.advance(api,self.s,"Head",issue=A,return_to_head=True),True,issue=A)
        self.s=session.load(api,REPO,result["installed_sha"])
        self.inject(lambda:session.save(api,self.s,*self.claim(self.s,C),True,issue=C))
        result=self.recover(lambda s:session.finish(api,s,"blocked","owner decision",issue=A),A)
        latest=session.load(api,REPO)
        self.assertEqual(result["contention_retries"],1)
        self.assertEqual([a["issue"] for a in latest["handoff"]["active"]],[C])
        self.assertEqual(len(session.issue_view(latest["ledger"],latest["handoff"],A)[2]),1)
        self.assertEqual(session.issue_view(latest["ledger"],latest["handoff"],A)[0]["state"],"blocked")

    def test_product_change_refuses_replan(self):
        session.save(self.api,self.s,*self.claim(self.s,C),True,issue=C)
        product=self.api.commit(self.api.git("rev-parse",self.api.product+"^{tree}"),[self.api.product])
        self.api.ref("main",product)
        with self.assertRaisesRegex(ValueError,"product changed"):
            self.recover(lambda s:self.claim(s,B),B)
        self.assertEqual(sum(m=="PATCH" for m,_,_ in self.api.writes),2)

    def test_unrelated_acceptance_change_refused(self):
        s=self.s
        ledger=copy.deepcopy(s["ledger"])
        ledger["issues"][0]["acceptance"]=["tampered"]
        tree=self.api.tree({session.LEDGER:install.render(ledger)},self.api.git("rev-parse",s["ref"]+"^{tree}"))
        self.api.ref(install.BRANCH,self.api.commit(tree,[s["ref"]]))
        fresh=session.load(self.api,REPO)
        with self.assertRaisesRegex(ValueError,"Historical acceptance criteria changed"):
            session.retry_scope(self.api,s,fresh,B,session.HandoffStale("advanced"))

    def test_package_change_then_restore_refused(self):
        s=self.s
        tree=self.api.tree({"tools/session.py":"changed\n"},self.api.git("rev-parse",s["ref"]+"^{tree}"))
        middle=self.api.commit(tree,[s["ref"]])
        restored=self.api.commit(self.api.git("rev-parse",s["ref"]+"^{tree}"),[middle])
        self.api.ref(install.BRANCH,restored)
        fresh=session.load(self.api,REPO)
        with self.assertRaisesRegex(ValueError,"Installed package changed"):
            session.retry_scope(self.api,s,fresh,B,session.HandoffStale("advanced"))

    def test_retired_row_cannot_be_reopened_during_unrelated_contention(self):
        api = self.api
        ledger = copy.deepcopy(self.s["ledger"])
        from tools import checkpoint
        checkpoint.register(ledger, 8, "v1.0.6", ["retired criterion"])
        row = next(row for row in ledger["issues"] if row["issue"] == 8)
        row["state"] = "retired"
        baseline_tree = api.tree({session.LEDGER: install.render(ledger)},
                                 api.git("rev-parse", self.s["ref"] + "^{tree}"))
        baseline = api.commit(baseline_tree, [self.s["ref"]])
        api.ref(install.BRANCH, baseline)
        previous = session.load(api, REPO, baseline)
        # A valid unrelated claim must remain recoverable with a retired row present.
        valid = session.save(api, previous, *self.claim(previous, C), True, issue=C)
        fresh = session.load(api, REPO, valid["installed_sha"])
        self.assertIsNone(session.retry_scope(api, previous, fresh, B,
                                              session.HandoffStale("advanced")))
        changed = copy.deepcopy(fresh["ledger"])
        next(row for row in changed["issues"] if row["issue"] == 8)["state"] = "blocked"
        tree = api.tree({session.LEDGER: install.render(changed)},
                        api.git("rev-parse", fresh["ref"] + "^{tree}"))
        tampered = api.commit(tree, [fresh["ref"]])
        api.ref(install.BRANCH, tampered)
        observed = session.load(api, REPO, tampered)
        before = list(api.writes)
        with self.assertRaisesRegex(ValueError, "Terminal record changed"):
            session.retry_scope(api, previous, observed, B, session.HandoffStale("advanced"))
        self.assertEqual(api.writes, before)
        # Detect a transient invalid intermediate state even if restored later.
        restored = api.commit(api.git("rev-parse", fresh["ref"] + "^{tree}"), [tampered])
        api.ref(install.BRANCH, restored)
        final = session.load(api, REPO, restored)
        with self.assertRaisesRegex(ValueError, "Terminal record changed"):
            session.retry_scope(api, previous, final, B, session.HandoffStale("advanced"))
        self.assertEqual(api.writes, before)

    def test_unrelated_terminal_archive_append_is_refused(self):
        api, previous = self.api, self.s
        handoff = copy.deepcopy(previous["handoff"])
        record = next(record for record in handoff["history"]
                      if record["disposition"] == "integrated")
        handoff["history"].append(copy.deepcopy(record))
        tree = api.tree({session.HANDOFF: install.render(handoff)},
                        api.git("rev-parse", previous["ref"] + "^{tree}"))
        pin = api.commit(tree, [previous["ref"]])
        api.ref(install.BRANCH, pin)
        fresh = session.load(api, REPO, pin)
        self.assertEqual(fresh["ledger"], previous["ledger"])
        before = list(api.writes)
        with self.assertRaisesRegex(ValueError, "terminal issue history appended"):
            session.retry_scope(api, previous, fresh, B, session.HandoffStale("advanced"))
        self.assertEqual(api.writes, before)

    def test_intervening_multi_issue_transaction_is_refused(self):
        api, previous = self.api, self.s
        ledger, handoff = self.claim(previous, C)
        # A second unrelated active issue in the same untrusted commit is not a
        # legal single-issue transaction, even if the recovery target is unchanged.
        intermediate = {**previous, "ledger": ledger, "handoff": handoff}
        ledger, handoff = self.claim(intermediate, C + 1)
        tree = api.tree({session.LEDGER: install.render(ledger),
                         session.HANDOFF: install.render(handoff)},
                        api.git("rev-parse", previous["ref"] + "^{tree}"))
        pin = api.commit(tree, [previous["ref"]])
        api.ref(install.BRANCH, pin)
        fresh = session.load(api, REPO, pin)
        before = list(api.writes)
        with self.assertRaisesRegex(ValueError, "Multiple issue scopes changed"):
            session.retry_scope(api, previous, fresh, B, session.HandoffStale("advanced"))
        self.assertEqual(api.writes, before)

    def test_operation_identity_stable_across_replan_and_distinct_intent(self):
        self.inject(lambda: session.save(self.api,self.s,*self.claim(self.s,C),True,issue=C))
        plan=lambda s:self.claim(s,B)
        ledger,handoff=plan(self.s)
        intent=session.planned_issue_view(ledger,handoff,B,True)
        identity=session.operation_identity(self.s,B,intent,{"note":"original"})
        self.assertNotEqual(identity,session.operation_identity(self.s,B,intent,{"note":"different"}))
        result=self.recover(plan,B,request={"note":"original"})
        self.assertEqual(result["operation_id"],identity)
        self.assertEqual(result["contention_retries"],1)
        messages=[body["message"] for method,path,body in self.api.writes
                  if method=="POST" and path.endswith("/git/commits") and "VIB-Operation:" in body["message"]]
        self.assertEqual(len(messages),2)
        self.assertEqual(messages[0],messages[1])
        self.assertIn("VIB-Operation: "+identity,self.api.git("show","-s","--format=%B",result["installed_sha"]))

    def test_final_rejection_confirms_existing_candidate(self):
        result=self.recover(lambda s:self.claim(s,B),B)
        published=result["installed_sha"]
        tree=self.api.git("rev-parse",published+"^{tree}")
        error=session.HandoffRejected(install.ApiError(422),published,tree,result["operation_id"])
        with patch.object(session,"save",side_effect=error) as save:
            recovered=self.recover(lambda s:self.claim(s,B),B,attempts=1)
        self.assertEqual(recovered["installed_sha"],published)
        self.assertTrue(recovered["recovered_response"])
        self.assertEqual(save.call_count,1)

    def test_final_unclassified_rejection_is_not_contention(self):
        error=session.HandoffRejected(install.ApiError(422),"a"*40,"b"*40)
        with patch.object(session,"save",side_effect=error) as save:
            with self.assertRaises(session.HandoffRejected):
                self.recover(lambda s:self.claim(s,B),B,attempts=1)
        self.assertEqual(save.call_count,1)

    def test_second_bounded_round_continues_after_four_wins(self):
        api=self.api
        original=api.request
        competing=iter((250,251,252,253))
        def race(method,path,body=None):
            if method=="PATCH":
                number=next(competing,None)
                if number is not None:
                    api.request=original
                    current=session.load(api,REPO)
                    session.save(api,current,*self.claim(current,number),True,issue=number)
                    api.request=race
            return original(method,path,body)
        api.request=race
        result=self.recover(lambda s:self.claim(s,B),B,rounds=2)
        self.assertEqual(result["contention_retries"],4)
        latest=session.load(api,REPO)
        self.assertEqual([r["issue"] for r in latest["handoff"]["active"]],[A,B,250,251,252,253])
        self.assertEqual(len(set(r["version"] for r in latest["ledger"]["issues"])),7)

    def test_verified_exhaustion_preserves_identity_and_bound(self):
        with patch.object(session,"save",side_effect=session.HandoffStale("advanced")) as save, \
             patch.object(session,"load",return_value=self.s), \
             patch.object(session,"retry_scope",return_value=None):
            with self.assertRaises(session.HandoffDeferred) as error:
                self.recover(lambda s:self.claim(s,B),B,rounds=2)
        self.assertEqual(save.call_count,8)
        self.assertEqual(error.exception.initial_sha,self.s["ref"])
        self.assertRegex(error.exception.operation_id,r"^[0-9a-f]{64}$")

    def test_intervening_unchanged_manifest_is_not_refetched(self):
        result=session.save(self.api,self.s,*self.claim(self.s,C),True,issue=C)
        fresh=session.load(self.api,REPO,result["installed_sha"])
        with patch.object(install,"read_text",wraps=install.read_text) as read:
            self.assertIsNone(session.retry_scope(self.api,self.s,fresh,B,session.HandoffStale("advanced")))
        self.assertEqual([call.args[2] for call in read.call_args_list],[session.LEDGER,session.HANDOFF])

    def test_changed_blob_bytes_must_match_tree(self):
        result=session.save(self.api,self.s,*self.claim(self.s,C),True,issue=C)
        fresh=session.load(self.api,REPO,result["installed_sha"])
        raw=self.api.read(fresh["ref"],session.LEDGER)+" "
        with patch.object(install,"read_text",side_effect=lambda api,prefix,path,ref:raw if path==session.LEDGER else api.read(ref,path)):
            with self.assertRaisesRegex(ValueError,"State blob identity mismatch"):
                session.retry_scope(self.api,self.s,fresh,B,session.HandoffStale("advanced"))

    def test_final_candidate_with_mismatched_receipt_is_unconfirmed(self):
        result=self.recover(lambda s:self.claim(s,B),B)
        published=result["installed_sha"]
        tree=self.api.git("rev-parse",published+"^{tree}")
        error=session.HandoffRejected(install.ApiError(422),published,tree,"f"*64)
        with patch.object(session,"save",side_effect=error) as save:
            with self.assertRaises(session.HandoffUnconfirmed):
                self.recover(lambda s:self.claim(s,B),B,attempts=1)
        self.assertEqual(save.call_count,1)

    def test_operation_receipt_survives_process_restart(self):
        import subprocess
        import sys
        result=self.recover(lambda s:self.claim(s,B),B)
        script="from tools import session; import json,sys,subprocess; path,sha,op=sys.argv[1:]; message=subprocess.check_output(['git','-C',path,'show','-s','--format=%B',sha],text=True); session.verify_operation_commit({'message':message},op); print(op)"
        output=subprocess.check_output([sys.executable,"-B","-c",script,self.api.path,result["installed_sha"],result["operation_id"]],text=True)
        self.assertEqual(output.strip(),result["operation_id"])

    def test_prepublication_ticket_confirms_exact_candidate_read_only(self):
        api = self.api
        tickets = []
        original = api.request
        def request(method, path, body=None):
            if method == "PATCH":
                self.assertEqual(len(tickets), 1)
                self.assertEqual(tickets[0]["candidate_sha"], body["sha"])
                original(method, path, body)
                raise install.ApiTransportError("PATCH", "git/refs", True)
            return original(method, path, body)
        api.request = request
        result = self.recover(lambda s: self.claim(s, B), B, on_recovery_ticket=tickets.append)
        api.request = original
        fresh = session.load(api, REPO)
        before = list(api.writes)
        ticket = tickets[0]
        confirmed = session.inspect_operation(api, fresh, ticket)
        self.assertEqual(confirmed["status"], "published")
        self.assertEqual(confirmed["installed_sha"], result["installed_sha"])
        self.assertEqual(confirmed["operation_id"], result["operation_id"])
        self.assertTrue(confirmed["read_only"])
        for changes in ({"issue": A}, {"repository": "/repos/other/repo"},
                        {"tree_sha": "f"*40}, {"operation_id": "f"*64},
                        {"parent_sha": "f"*40}, {"schema_version": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                session.inspect_operation(api, fresh, {**ticket, **changes})
        self.assertEqual(api.writes, before)

    def test_ticket_sink_failure_does_not_publish(self):
        tickets = []
        before = self.api.ref(install.BRANCH)
        def broken(ticket):
            tickets.append(ticket)
            raise OSError("receipt sink unavailable")
        with self.assertRaisesRegex(OSError, "receipt sink"):
            self.recover(lambda s: self.claim(s, B), B, on_recovery_ticket=broken)
        self.assertEqual(len(tickets), 1)
        self.assertEqual(self.api.ref(install.BRANCH), before)
        fresh = session.load(self.api, REPO)
        writes = list(self.api.writes)
        with self.assertRaisesRegex(ValueError, "not confirmed"):
            session.inspect_operation(self.api, fresh, tickets[0])
        self.assertEqual(self.api.writes, writes)

    def test_recovery_ticket_rejects_unrelated_tree_mutation(self):
        api, state = self.api, self.s
        ledger, handoff = self.claim(state, B)
        intent = session.planned_issue_view(ledger, handoff, B, True)
        operation_id = session.operation_identity(state, B, intent)
        tree = api.tree({session.LEDGER: install.render(ledger),
                         session.HANDOFF: install.render(handoff),
                         "notes/custom.md": "tampered\n"},
                        api.git("rev-parse", state["ref"] + "^{tree}"))
        candidate = api.git("commit-tree", tree, "-p", state["ref"],
                            data="VIB cooperative handoff\n\nVIB-Operation: " + operation_id + "\n")
        api.ref(install.BRANCH, candidate)
        fresh = session.load(api, REPO)
        ticket = {"schema_version": 1, "repository": state["prefix"], "issue": B,
                  "parent_sha": state["ref"], "candidate_sha": candidate,
                  "tree_sha": tree, "operation_id": operation_id}
        before = list(api.writes)
        with self.assertRaisesRegex(ValueError, "unrelated tree entries"):
            session.inspect_operation(api, fresh, ticket)
        self.assertEqual(api.writes, before)

    def test_retry_source_cache_never_caches_installed_bytes(self):
        api = self.api
        cache = {}
        with patch.object(install, "source_files", wraps=install.source_files) as source, \
             patch.object(install, "read_text", wraps=install.read_text) as read:
            first = session.load(api, REPO, _source_cache=cache)
            second = session.load(api, REPO, _source_cache=cache)
            self.assertEqual(first, second)
            self.assertEqual(source.call_count, 1)
            for path in first["manifest"]["package_files_sha256"]:
                self.assertEqual(sum(call.args[2] == path for call in read.call_args_list), 2)
        with patch.object(install, "read_text", side_effect=lambda api, prefix, path, ref:
                          "changed" if path == "tools/session.py" else api.read(ref, path)):
            with self.assertRaisesRegex(ValueError, "pinned source"):
                session.load(api, REPO, _source_cache=cache)

    def test_durable_ticket_survives_fresh_process_and_refuses_overwrite(self):
        import subprocess
        import sys
        api = self.api
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            def journal(ticket):
                paths.append(session.persist_recovery_ticket(directory, ticket))
            result = self.recover(lambda s: self.claim(s, B), B, on_recovery_ticket=journal)
            self.assertEqual(len(paths), 1)
            script = "import json,sys; from pathlib import Path; print(json.dumps(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))))"
            ticket = json.loads(subprocess.check_output(
                [sys.executable, "-B", "-c", script, str(paths[0])], text=True))
            self.assertEqual(ticket["candidate_sha"], result["installed_sha"])
            self.assertEqual(ticket["operation_id"], result["operation_id"])
            before = paths[0].read_bytes()
            with self.assertRaises(FileExistsError):
                session.persist_recovery_ticket(directory, ticket)
            self.assertEqual(paths[0].read_bytes(), before)
            fresh = session.load(api, REPO)
            writes = list(api.writes)
            self.assertEqual(session.inspect_operation(api, fresh, ticket)["status"], "published")
            self.assertEqual(api.writes, writes)

    def test_journal_failure_prevents_publication(self):
        api = self.api
        previous = api.ref(install.BRANCH)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(session.os, "fsync", side_effect=OSError("journal flush failed")):
                with self.assertRaisesRegex(OSError, "journal flush failed"):
                    self.recover(lambda s: self.claim(s, B), B,
                                 on_recovery_ticket=lambda ticket: session.persist_recovery_ticket(directory, ticket))
        self.assertEqual(api.ref(install.BRANCH), previous)
