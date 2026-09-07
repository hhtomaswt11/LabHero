"""Exercise desktop persistence without touching a student's save directory."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
import save_load


class DesktopAtomicSaveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        for mocked in (
            patch.object(save_load, '_IS_WEB', False),
            patch.object(save_load, 'get_save_path', side_effect=lambda name: str(self.directory / name)),
        ):
            mocked.start()
            self.addCleanup(mocked.stop)

    def test_replace_failure_preserves_previous_evidence(self):
        path = self.directory / 'challenge_score.txt'
        save_load.save_challenge_score({'score': 3})
        with patch.object(save_load.os, 'replace', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                save_load.save_challenge_score({'score': 4})
        self.assertEqual(json.loads(path.read_text()), {'score': 3})
        self.assertEqual(list(self.directory.iterdir()), [path])

    def test_serialization_failure_preserves_previous_evidence(self):
        save_load.save_challenge_score({'score': 3})
        with self.assertRaises(TypeError):
            save_load.save_challenge_score({'score': object()})
        self.assertEqual(save_load.load_challenge_score(), {'score': 3})

    def test_main_save_round_trip_preserves_identity_and_rewards(self):
        data = ['Mónica', [], ['01'], [], {'campaign_mode': 'easy'},
                save_load.create_reward_state()]
        save_load.save_file(data)
        self.assertEqual(save_load.load_file(str(self.directory / 'data')), data)
        self.assertEqual([p.name for p in self.directory.iterdir()], ['data.txt'])


if __name__ == '__main__':
    unittest.main()
