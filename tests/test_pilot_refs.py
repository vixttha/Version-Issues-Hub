"""Regression controls for #39 acceptance harness only; no live GitHub writes."""
import unittest
from unittest.mock import Mock, patch
from tools import install, pilot_refs, session


class PilotRefTests(unittest.TestCase):
    final = "a" * 40
    prefix = "/repos/example/product"

    def test_absent_recovery_created_once_and_confirmed(self):
        api = Mock()
        with patch.object(install, "read_ref", side_effect=[None, self.final]), patch.object(install, "wait_ref") as wait:
            name = pilot_refs.ensure_recovery_ref(api, self.prefix, self.final)
        self.assertEqual(name, "archive/vib-recovery/" + self.final)
        api.request.assert_called_once_with("POST", self.prefix + "/git/refs",
                                            {"ref": "refs/heads/" + name, "sha": self.final})
        wait.assert_called_once_with(api, self.prefix, name, self.final)

    def test_exact_recovery_reused_without_writes(self):
        api = Mock()
        with patch.object(install, "read_ref", return_value=self.final):
            self.assertEqual(pilot_refs.ensure_recovery_ref(api, self.prefix, self.final),
                             "archive/vib-recovery/" + self.final)
        api.request.assert_not_called()

    def test_divergent_or_moving_recovery_ref_refused(self):
        for observations in (["b" * 40], [self.final, "b" * 40], [self.final, None]):
            with self.subTest(observations=observations):
                api = Mock()
                with patch.object(install, "read_ref", side_effect=observations):
                    with self.assertRaises(ValueError):
                        pilot_refs.ensure_recovery_ref(api, self.prefix, self.final)
                api.request.assert_not_called()

    def test_uncertain_post_is_not_retried(self):
        api = Mock()
        api.request.side_effect = OSError("interrupted")
        with patch.object(install, "read_ref", return_value=None):
            with self.assertRaises(OSError):
                pilot_refs.ensure_recovery_ref(api, self.prefix, self.final)
        self.assertEqual(api.request.call_count, 1)

    def test_existing_self_install_uses_pinned_state_not_candidate_plan(self):
        api = Mock()
        main, installed, source, previous = "a"*40, "b"*40, "c"*40, "d"*40
        state = {"manifest": {"source_sha": previous, "enforcement": "disabled"}, "product_sha": main}
        with patch.object(install, "read_ref", side_effect=[main, installed, installed, main]), \
             patch.object(install, "source_files", return_value={"README.md": "candidate"}), \
             patch.object(session, "load", return_value=state) as load, \
             patch.object(install, "install", side_effect=ValueError("Install branch already exists; no overwrite or upgrade performed")):
            report = pilot_refs.verify_self_install(api, "example/product", source)
        load.assert_called_once_with(api, "example/product", installed)
        self.assertEqual(report["mode"], "existing_install_verified")
        self.assertEqual(report["installed_source"], previous)
        self.assertIsNone(report["install_plan_paths"])
        self.assertIn("README.md", report["candidate_package_paths"])
        api.request.assert_not_called()

    def test_absent_self_install_preserves_read_only_plan(self):
        api = Mock()
        main, source = "a"*40, "c"*40
        paths = sorted(["README.md", "vib-install.json", session.LEDGER, session.HANDOFF])
        plan = {"status": "planned", "manifest": {"product_baseline_sha": main, "enforcement": "disabled"}, "paths": paths}
        with patch.object(install, "read_ref", side_effect=[main, None, None, main]), \
             patch.object(install, "source_files", return_value={"README.md": "candidate"}), \
             patch.object(install, "install", return_value=plan) as dry:
            report = pilot_refs.verify_self_install(api, "example/product", source)
        dry.assert_called_once_with(api, "example/product", source, "v0.0.0")
        self.assertEqual(report["install_plan_paths"], paths)
        self.assertEqual(report["mode"], "read_only_plan")
        api.request.assert_not_called()

    def test_changed_self_install_ref_fails_closed(self):
        api = Mock()
        main, installed, source = "a"*40, "b"*40, "c"*40
        state = {"manifest": {"source_sha": source, "enforcement": "disabled"}, "product_sha": main}
        with patch.object(install, "read_ref", side_effect=[main, installed, "d"*40]), \
             patch.object(install, "source_files", return_value={"README.md": "candidate"}), \
             patch.object(session, "load", return_value=state), \
             patch.object(install, "install", side_effect=ValueError("Install branch already exists")):
            with self.assertRaisesRegex(ValueError, "changed"):
                pilot_refs.verify_self_install(api, "example/product", source)
        api.request.assert_not_called()

    def test_self_install_reload_requires_observed_ref_change(self):
        from tools.acceptance_snapshot import SnapshotDrift, retry_snapshot
        api = Mock()
        main, old, new, source = "a"*40, "b"*40, "d"*40, "c"*40
        state = {"manifest": {"source_sha": source, "enforcement": "disabled"}, "product_sha": main}
        with patch.object(install, "read_ref", side_effect=[main, old, new, main, new, new, main]), patch.object(install, "source_files", return_value={"README.md": "candidate"}), patch.object(session, "load", side_effect=[ValueError("Installed branch has advanced; reload before acting"), state]) as load, patch.object(install, "install", side_effect=ValueError("Install branch already exists")):
            result = retry_snapshot(lambda: pilot_refs.verify_self_install(api, "example/product", source))
        self.assertEqual(result["installed_sha"], new)
        self.assertEqual(load.call_count, 2)
        api.request.assert_not_called()
        with patch.object(install, "read_ref", side_effect=[main, old, old]), patch.object(install, "source_files", return_value={}), patch.object(session, "load", side_effect=ValueError("Installed branch has advanced; reload before acting")) as load:
            with self.assertRaises(ValueError) as error:
                retry_snapshot(lambda: pilot_refs.verify_self_install(api, "example/product", source))
            self.assertNotIsInstance(error.exception, SnapshotDrift)
            load.assert_called_once()
