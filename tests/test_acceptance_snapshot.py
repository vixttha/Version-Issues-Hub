import json
import subprocess
import unittest
from unittest.mock import patch
from tools import acceptance_snapshot as a

OLD="a"*40
NEW="b"*40
TARGET="example/repo"

class SnapshotTests(unittest.TestCase):
    def test_reload_only_after_demonstrated_ref_advance(self):
        states=[{"ref":OLD},{"ref":NEW}]
        reports=[{"installed_sha":OLD},{"installed_sha":NEW}]
        results=[subprocess.CompletedProcess([],1,"","VIB session stopped: Installed branch has advanced; reload before acting"),
                 subprocess.CompletedProcess([],0,json.dumps(reports[1]),"")]
        with patch.object(a.session,"load",side_effect=states) as load, \
             patch.object(a.session,"inspect",side_effect=reports), \
             patch.object(a.subprocess,"run",side_effect=results), \
             patch.object(a.install,"read_ref",side_effect=[NEW,NEW]):
            state,report=a.recover_stable(object(),TARGET)
        self.assertEqual(state,states[1]); self.assertEqual(report,reports[1]);self.assertEqual(load.call_count,2)

    def test_other_failure_is_not_hidden(self):
        with patch.object(a.session,"load",return_value={"ref":OLD}) as load, \
             patch.object(a.session,"inspect",return_value={"installed_sha":OLD}), \
             patch.object(a.subprocess,"run",return_value=subprocess.CompletedProcess([],1,"","invalid package")), \
             patch.object(a.install,"read_ref",return_value=NEW):
            with self.assertRaisesRegex(RuntimeError,"invalid package"):
                a.recover_stable(object(),TARGET)
            self.assertEqual(load.call_count,1)

    def test_exhaustion_is_not_a_pass(self):
        with patch.object(a.session,"load",return_value={"ref":OLD}), \
             patch.object(a.session,"inspect",return_value={"installed_sha":OLD}), \
             patch.object(a.subprocess,"run",return_value=subprocess.CompletedProcess([],1,"","Installed branch has advanced; reload before acting")), \
             patch.object(a.install,"read_ref",return_value=NEW):
            with self.assertRaisesRegex(ValueError,"did not stabilize"):
                a.recover_stable(object(),TARGET)

    def test_whole_check_retries_only_observed_drift(self):
        from unittest.mock import Mock
        check = Mock(side_effect=[a.SnapshotDrift("changed"), {"ok": True}])
        self.assertEqual(a.retry_snapshot(check), {"ok": True})
        self.assertEqual(check.call_count, 2)
        for exc in (ValueError("invalid package"), AssertionError("invalid proof")):
            check = Mock(side_effect=exc)
            with self.assertRaises(type(exc)):
                a.retry_snapshot(check)
            check.assert_called_once()

    def test_whole_check_exhaustion_fails_closed(self):
        from unittest.mock import Mock
        check = Mock(side_effect=a.SnapshotDrift("changed"))
        with self.assertRaises(a.SnapshotDrift):
            a.retry_snapshot(check)
        self.assertEqual(check.call_count, 3)

    def test_inspection_child_delay_propagates_without_ref_probe(self):
        receipt=json.dumps({"kind":"vib_api_delay","status":429,"retry_after":90})
        with patch.object(a.session,"load",return_value={"ref":OLD}), \
             patch.object(a.session,"inspect",return_value={"installed_sha":OLD}), \
             patch.object(a.subprocess,"run",return_value=subprocess.CompletedProcess([],1,"",receipt)), \
             patch.object(a.install,"read_ref") as read:
            with self.assertRaises(a.install.ApiError) as error:
                a.recover_stable(object(),TARGET)
        self.assertEqual(error.exception.retry_after,90)
        read.assert_not_called()
