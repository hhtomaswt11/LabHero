import copy
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

# settings imports pygame.Vector2. Provide the same tiny stub used by other
# persistence-only tests so this suite remains runnable without pygame.
if 'pygame' not in sys.modules:
    fake_pygame = types.ModuleType('pygame')

    class _Vector2:
        def __init__(self, *args, **kwargs):
            pass

    fake_pygame.Vector2 = _Vector2
    sys.modules['pygame'] = fake_pygame

import save_load  # noqa: E402
from hint_system import create_reward_state  # noqa: E402


class FakeLocalStorage:
    def __init__(self, initial=None):
        self.data = dict(initial or {})

    @property
    def length(self):
        return len(self.data)

    def key(self, index):
        try:
            return list(self.data.keys())[index]
        except IndexError:
            return None

    def setItem(self, key, value):
        self.data[str(key)] = str(value)

    def getItem(self, key):
        return self.data.get(str(key))

    def removeItem(self, key):
        self.data.pop(str(key), None)


class WebPersistentBrowserSaveTests(unittest.TestCase):
    def setUp(self):
        self.original_is_web = save_load._IS_WEB
        self.original_memstore = copy.deepcopy(save_load._MEMSTORE)
        self.original_warning = save_load._WEB_STORAGE_WARNING_EMITTED
        save_load._IS_WEB = True
        save_load._MEMSTORE.clear()
        save_load._WEB_STORAGE_WARNING_EMITTED = False
        self.storage = FakeLocalStorage({'other-app:key': 'keep-me'})
        self.storage_patch = patch.object(save_load, '_browser_local_storage', return_value=self.storage)
        self.storage_patch.start()

    def tearDown(self):
        self.storage_patch.stop()
        save_load._IS_WEB = self.original_is_web
        save_load._MEMSTORE.clear()
        save_load._MEMSTORE.update(self.original_memstore)
        save_load._WEB_STORAGE_WARNING_EMITTED = self.original_warning

    def _sample_save(self):
        reward = create_reward_state()
        reward['keys']['bronze'] = 12
        reward['mission_hints']['01'] = 2
        reward['mission_scores']['01'] = 2
        return [
            'Browser Student',
            [{'growth': 0.42}],
            ['01', '02'],
            ['01'],
            {
                'scene': 'main_map',
                'x': 123.5,
                'y': 456.25,
                'facing': 'right',
                'status': 'right_idle',
                'skin_id': 'default',
            },
            reward,
        ]


    def test_real_pygbag_bridge_uses_platform_window_localstorage(self):
        import platform as platform_module

        fake_window = types.SimpleNamespace(localStorage=self.storage)
        with patch.object(platform_module, 'window', fake_window, create=True):
            self.assertIs(save_load._browser_local_storage(), self.storage)

    def test_main_save_survives_simulated_page_refresh(self):
        original = self._sample_save()
        save_load.save_file(original)

        storage_key = save_load._web_storage_key('data')
        self.assertIn(storage_key, self.storage.data)
        self.assertEqual(json.loads(self.storage.data[storage_key])[0], 'Browser Student')

        # A browser refresh recreates Python/WASM state, so RAM is empty while
        # origin localStorage remains.
        save_load._MEMSTORE.clear()
        loaded = save_load.load_file('data')

        self.assertEqual(loaded[0], 'Browser Student')
        self.assertEqual(loaded[4]['x'], 123.5)
        self.assertEqual(loaded[5]['keys']['bronze'], 12)
        self.assertEqual(loaded[5]['mission_hints']['01'], 2)
        self.assertEqual(loaded[5]['mission_scores']['01'], 2)
        self.assertIn('data', save_load._MEMSTORE)

    def test_mission_evidence_survives_simulated_page_refresh(self):
        report = {
            'evidence_complete': True,
            'latest_attempt': {'growth': 0.31, 'ethanol': 4.2},
        }
        save_load.save_mission40_final_certification(report)
        save_load._MEMSTORE.clear()

        self.assertEqual(save_load.load_mission40_final_certification(), report)

    def test_clear_memstore_preserves_durable_save(self):
        save_load.save_file(self._sample_save())
        save_load.clear_memstore()

        self.assertEqual(save_load._MEMSTORE, {})
        self.assertIn(save_load._web_storage_key('data'), self.storage.data)
        self.assertEqual(save_load.load_file('data')[0], 'Browser Student')

    def test_explicit_new_game_clear_removes_only_labhero_namespace(self):
        save_load.save_file(self._sample_save())
        save_load.save_mission36_fermentation_onset({'row': 1})
        self.storage.setItem('labhero-unrelated', 'leave-this-too')

        save_load.clear_web_persistent_storage()

        self.assertEqual(save_load._MEMSTORE, {})
        self.assertNotIn(save_load._web_storage_key('data'), self.storage.data)
        self.assertNotIn(save_load._web_storage_key('mission36_fermentation_onset'), self.storage.data)
        self.assertEqual(self.storage.data['other-app:key'], 'keep-me')
        self.assertEqual(self.storage.data['labhero-unrelated'], 'leave-this-too')

    def test_delete_one_mission_artifact_removes_localstorage_copy(self):
        save_load.save_mission31_environmental_suppression_check({'ok': True})
        key = save_load._web_storage_key('mission31_environmental_suppression_check')
        self.assertIn(key, self.storage.data)

        save_load.clear_mission31_environmental_suppression_check()

        self.assertNotIn(key, self.storage.data)
        self.assertIsNone(save_load.load_mission31_environmental_suppression_check())

    def test_all_web_values_are_json_strings_in_storage(self):
        save_load.save_challenge_score({'score': 7})
        raw = self.storage.getItem(save_load._web_storage_key('challenge_score'))
        self.assertIsInstance(raw, str)
        self.assertEqual(json.loads(raw), {'score': 7})

    def test_source_has_no_direct_per_artifact_memstore_assignments(self):
        source = (CODE / 'save_load.py').read_text(encoding='utf-8')
        self.assertNotIn("_MEMSTORE['mission", source)
        self.assertNotIn("_MEMSTORE['data']", source)
        self.assertIn("_WEB_STORAGE_PREFIX = 'labhero:v1:'", source)

    def test_game_has_web_autosave_and_new_game_durable_clear(self):
        source = (ROOT / 'LabHero.py').read_text(encoding='utf-8')
        self.assertIn("self.web_autosave_elapsed >= 5.0", source)
        self.assertIn("clear_web_persistent_storage()", source)
        self.assertIn("save_file(self.level.player.get_save_data())", source)

    def test_back_to_title_saves_then_clears_only_ram_cache(self):
        source = (CODE / 'menu_2.py').read_text(encoding='utf-8')
        marker = source.index('def back_to_title():')
        block = source[marker: marker + 600]
        self.assertLess(block.index('save_file(self.player.get_save_data())'), block.index('clear_memstore()'))
        self.assertNotIn('clear_web_persistent_storage()', block)

    def test_storage_status_exposes_namespace(self):
        status = save_load.get_web_storage_status()
        self.assertTrue(status['is_web'])
        self.assertTrue(status['local_storage_available'])
        self.assertEqual(status['namespace'], 'labhero:v1:')


if __name__ == '__main__':
    unittest.main()
