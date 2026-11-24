"""Offline acceptance harness contract; no remote calls or writes."""
import unittest
from unittest.mock import Mock, patch
from http.client import RemoteDisconnected
from tools import live_acceptance as live

SOURCE = "a" * 40
REF = "b" * 40
PRODUCT = "c" * 40

class LiveIsolationTests(unittest.TestCase):
    def test_core_never_invokes_external_adopters(self):
        with patch.object(live, "verify_self_install", return_value={}), patch.object(live, "verify_templates", return_value={}), patch.object(live, "verify_live_cli_plan") as external, patch.object(live, "verify_aldervale_install") as alder, patch.object(live, "verify_bart") as bart:
            result = live.run_cases(Mock(), SOURCE, "core")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(set(result["cases"]), {"self_install", "templates"})
        for m in (external, alder, bart):
            m.assert_not_called()

    def test_failed_external_does_not_suppress_other_evidence(self):
        with patch.object(live, "verify_live_cli_plan", side_effect=live.install.ApiError(404)), patch.object(live, "verify_aldervale_install", return_value={"ok": True}), patch.object(live, "verify_bart", return_value={"ok": True}), patch.object(live, "verify_self_install") as core:
            result = live.run_cases(Mock(), SOURCE, "external")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["cases"]["readme_hq"], {"status": "failed", "error_type": "ApiError", "http_status": 404})
        self.assertEqual(result["cases"]["bart"]["status"], "passed")
        core.assert_not_called()

    def test_all_scope_never_green_on_bad_proof(self):
        with patch.object(live, "verify_self_install", return_value={}), patch.object(live, "verify_templates", side_effect=AssertionError("private details")), patch.object(live, "verify_live_cli_plan", return_value={}), patch.object(live, "verify_aldervale_install", return_value={}), patch.object(live, "verify_bart", return_value={}):
            result = live.run_cases(Mock(), SOURCE, "all")
        self.assertEqual(len(result["cases"]), 5)
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("private details", str(result))

    def test_get_disconnect_retries_bounded(self):
        api = live.ReadOnlyGitHub(None)
        with patch.object(live.install.GitHub, "request", side_effect=[RemoteDisconnected(), {"ok": True}]) as call, patch.object(live.time, "sleep"):
            self.assertEqual(api.request("GET", "/test"), {"ok": True})
            self.assertEqual(call.call_count, 2)
        with patch.object(live.install.GitHub, "request", side_effect=RemoteDisconnected()) as call, patch.object(live.time, "sleep"):
            with self.assertRaises(RemoteDisconnected):
                api.request("GET", "/test")
            self.assertEqual(call.call_count, 3)

    def test_no_write_or_generic_retry(self):
        api = live.ReadOnlyGitHub(None)
        with patch.object(live.install.GitHub, "request", side_effect=ValueError("bad")) as call:
            with self.assertRaises(AssertionError):
                api.request("POST", "/test", {})
            with self.assertRaises(AssertionError):
                api.request("GET", "/test", {})
            call.assert_not_called()
            with self.assertRaises(ValueError):
                api.request("GET", "/test")
            self.assertEqual(call.call_count, 1)

    def test_occupied_readme_is_not_a_new_plan(self):
        api = Mock()
        api.request.return_value = {"private": False, "id": 1463992109, "default_branch": "main"}
        state = {"ref": REF, "product_sha": PRODUCT, "manifest": {"source_sha": SOURCE, "enforcement": "disabled"}}
        report = {"repository": "vixttha/README-HQ", "owner_merge_required": True, "evidence_verified": False}
        with patch.object(live.install, "read_ref", side_effect=[PRODUCT, REF, REF, PRODUCT]), patch.object(live, "recover_stable", return_value=(state, report)), patch.object(live, "verify_occupied") as occupied, patch.object(live.subprocess, "check_output") as cli:
            result = live.verify_live_cli_plan(api, SOURCE)
        self.assertEqual(result["mode"], "existing_install_verified")
        self.assertIsNone(result["planned_files"])
        self.assertFalse(result["branch_created"])
        occupied.assert_called_once()
        cli.assert_not_called()

    def test_occupied_readme_rejects_drift(self):
        api = Mock()
        api.request.return_value = {"private": False, "id": 1463992109, "default_branch": "main"}
        state = {"ref": REF, "product_sha": PRODUCT, "manifest": {"source_sha": SOURCE, "enforcement": "disabled"}}
        report = {"repository": "vixttha/README-HQ", "owner_merge_required": True, "evidence_verified": False}
        with patch.object(live.install, "read_ref", side_effect=[PRODUCT, REF, "d"*40]), patch.object(live, "recover_stable", return_value=(state, report)), patch.object(live, "verify_occupied"):
            with self.assertRaises(AssertionError):
                live.verify_live_cli_plan(api, SOURCE)
