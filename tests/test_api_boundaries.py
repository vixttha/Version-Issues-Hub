"""Focused independent-audit response boundary regressions."""
import unittest
from unittest.mock import Mock
from tools import install, session, lifecycle, gate, standard

SHA = "a"*40
PREFIX = "/repos/example/test"

class ResponseBoundaryTests(unittest.TestCase):
    def test_malformed_ref_responses_are_controlled(self):
        for value in (None, [], "ref", {}, {"ref":"refs/heads/main","object":None},
                      {"ref":"refs/heads/main","object":{"type":"commit"}}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                install.read_ref(Mock(request=Mock(return_value=value)), PREFIX, "main")
        for status in (404, 429):
            api = Mock(request=Mock(side_effect=install.ApiError(status)))
            if status == 404:
                self.assertIsNone(install.read_ref(api, PREFIX, "main"))
            else:
                with self.assertRaises(install.ApiError):
                    install.read_ref(api, PREFIX, "main")

    def test_malformed_file_content_is_controlled(self):
        for value in (None, [], 1, {}):
            item = {"type":"file","encoding":"base64","path":"x","content":value}
            with self.subTest(value=value), self.assertRaises(ValueError):
                install.read_text(Mock(request=Mock(return_value=item)), PREFIX, "x", SHA)

    def test_malformed_tree_rows_are_controlled(self):
        commit = {"sha":SHA,"tree":{"sha":SHA}}
        good = {"path":"x","type":"blob","mode":"100644","sha":SHA}
        for row in (None, {}, {**good,"sha":"bad"}, {**good,"type":"bad"},
                    {**good,"mode":"040000"}, {**good,"path":"../x"}):
            value = {"sha":SHA,"truncated":False,"tree":[row]}
            with self.subTest(row=row), self.assertRaises(ValueError):
                lifecycle.tree_entries(Mock(request=Mock(return_value=value)), PREFIX, SHA, commit=commit)
        value = {"sha":SHA,"truncated":False,"tree":[good,
                 {"path":"link","type":"blob","mode":"120000","sha":SHA},
                 {"path":"submodule","type":"commit","mode":"160000","sha":SHA}]}
        self.assertEqual(len(lifecycle.tree_entries(Mock(request=Mock(return_value=value)),
                          PREFIX,SHA,commit=commit)[1]),3)

    def test_boolean_ids_do_not_match_integer_identity(self):
        state = {"prefix":PREFIX,"manifest":{"product_branch":"main","target_repository_id":1}}
        with self.assertRaises(ValueError):
            session.get_issue(Mock(request=Mock(return_value={"number":True})),state,1)
        pr = {"number":1,"base":{"ref":"main","repo":{"id":True}},"head":{"sha":SHA}}
        with self.assertRaises(ValueError):
            session.get_pr(Mock(request=Mock(return_value=pr)),state,{"pull_request":1,"candidate_sha":SHA})
        policy = {"repository_id":1,"pull_request":1,"head_sha":SHA,"merge_sha":SHA,"base_sha":"b"*40}
        run = {"id":1,"run_attempt":1,"repository":{"id":1},"event":"pull_request",
               "head_sha":SHA,"status":"completed","conclusion":"success"}
        standard.check_pr_run(run,policy,1,1)
        for changed in ({"id":True},{"run_attempt":True},{"repository":{"id":True}}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                standard.check_pr_run({**run,**changed},policy,1,1)

    def test_invalid_collection_rows_fail_closed(self):
        api = Mock(request=Mock(return_value={"total_count":1,"jobs":[None]}))
        with self.assertRaises(ValueError):
            gate.exact_collection(api,"/jobs","jobs")

    def test_malformed_nested_pr_compare_and_run_fail_closed(self):
        state = {"prefix":PREFIX,"manifest":{"product_branch":"main","target_repository_id":1}}
        active = {"pull_request":1,"candidate_sha":SHA}
        for pr in (None, {"number":1,"base":None}, {"number":1,"base":{"repo":None},"head":{}}):
            with self.subTest(pr=pr), self.assertRaises(ValueError):
                session.get_pr(Mock(request=Mock(return_value=pr)),state,active)
        with self.assertRaises(ValueError):
            gate.check_ancestry(Mock(request=Mock(return_value={"status":"ahead","merge_base_commit":None})),PREFIX,SHA,SHA)
        with self.assertRaises(ValueError):
            standard.check_pr_run(None,{},1,1)
