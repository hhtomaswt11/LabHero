import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))


class LazySkinLoadingTests(unittest.TestCase):
    def setUp(self):
        self._saved_modules = {
            name: sys.modules.get(name)
            for name in ('skins', 'functions', 'utils', 'progression')
        }
        self.tmp = tempfile.TemporaryDirectory()
        self.asset_root = Path(self.tmp.name)
        self.import_calls = []

        functions = types.ModuleType('functions')

        def import_folder(path):
            path = Path(path)
            self.import_calls.append(path)
            return [f'surface:{path.parent.name}:{path.name}'] if any(path.iterdir()) else []

        functions.import_folder = import_folder
        sys.modules['functions'] = functions

        utils = types.ModuleType('utils')
        utils.get_resource_path = lambda rel: str(self.asset_root / rel)
        sys.modules['utils'] = utils

        progression = types.ModuleType('progression')
        progression.unlock_requirement = lambda kind, item_id: '35' if (kind, item_id) == ('skin', 'golden') else None
        progression.mission_requirement_met = lambda requirement, completed: requirement is None or requirement in (completed or [])
        sys.modules['progression'] = progression

        sys.modules.pop('skins', None)
        self.skins_module = importlib.import_module('skins')

    def tearDown(self):
        sys.modules.pop('skins', None)
        for name, module in self._saved_modules.items():
            if name == 'skins':
                continue
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        self.tmp.cleanup()

    def _make_skin_tree(self, folder, missing_state=None):
        root = self.asset_root / folder
        for state in self.skins_module.ANIMATION_STATES:
            if state == missing_state:
                continue
            state_dir = root / state
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / '0.png').write_bytes(b'not-decoded-by-discovery')
        return root

    def _registry(self):
        SkinDefinition = self.skins_module.SkinDefinition
        return [
            SkinDefinition('default', 'Classic', 'classic'),
            SkinDefinition('alt', 'Scarlet', 'scarlet'),
            SkinDefinition('golden', 'Golden', 'golden', unlocked=False, unlock_after_mission='35'),
        ]

    def test_manager_discovers_skins_without_decoding_any_animation(self):
        for folder in ('classic', 'scarlet', 'golden'):
            self._make_skin_tree(folder)

        manager = self.skins_module.SkinManager(self._registry())

        self.assertEqual(manager.skin_ids(), ['default', 'alt', 'golden'])
        self.assertEqual(manager.animations_by_skin, {})
        self.assertEqual(self.import_calls, [])

    def test_first_animation_request_loads_only_requested_skin(self):
        for folder in ('classic', 'scarlet', 'golden'):
            self._make_skin_tree(folder)
        manager = self.skins_module.SkinManager(self._registry())

        animations = manager.get_animations('default')

        self.assertEqual(set(animations), set(self.skins_module.ANIMATION_STATES))
        self.assertEqual(len(self.import_calls), len(self.skins_module.ANIMATION_STATES))
        self.assertEqual(set(manager.animations_by_skin), {'default'})
        self.assertTrue(all(path.parent.name == 'classic' for path in self.import_calls))

    def test_loaded_skin_is_reused_without_reading_frames_again(self):
        for folder in ('classic', 'scarlet', 'golden'):
            self._make_skin_tree(folder)
        manager = self.skins_module.SkinManager(self._registry())

        first = manager.get_animations('alt')
        calls_after_first = list(self.import_calls)
        second = manager.get_animations('alt')

        self.assertIs(first, second)
        self.assertEqual(self.import_calls, calls_after_first)
        self.assertEqual(set(manager.animations_by_skin), {'alt'})

    def test_validity_does_not_depend_on_skin_already_being_loaded(self):
        for folder in ('classic', 'scarlet', 'golden'):
            self._make_skin_tree(folder)
        manager = self.skins_module.SkinManager(self._registry())

        self.assertTrue(manager.is_valid_skin('alt'))
        self.assertFalse(manager.is_valid_skin('missing'))
        self.assertNotIn('alt', manager.animations_by_skin)
        self.assertEqual(self.import_calls, [])

    def test_incomplete_skin_is_excluded_without_loading_other_skins(self):
        self._make_skin_tree('classic')
        self._make_skin_tree('scarlet', missing_state='left_idle')
        self._make_skin_tree('golden')

        manager = self.skins_module.SkinManager(self._registry())

        self.assertEqual(manager.skin_ids(), ['default', 'golden'])
        self.assertFalse(manager.is_valid_skin('alt'))
        self.assertEqual(self.import_calls, [])

    def test_unknown_skin_falls_back_to_default_and_loads_only_default(self):
        for folder in ('classic', 'scarlet', 'golden'):
            self._make_skin_tree(folder)
        manager = self.skins_module.SkinManager(self._registry())

        unknown = manager.get_animations('does-not-exist')
        default = manager.get_animations('default')

        self.assertIs(unknown, default)
        self.assertEqual(set(manager.animations_by_skin), {'default'})
        self.assertEqual(len(self.import_calls), len(self.skins_module.ANIMATION_STATES))

    def test_locked_skin_metadata_does_not_force_image_loading(self):
        for folder in ('classic', 'scarlet', 'golden'):
            self._make_skin_tree(folder)
        manager = self.skins_module.SkinManager(self._registry())

        self.assertFalse(manager.is_unlocked('golden', ['34']))
        self.assertTrue(manager.is_unlocked('golden', ['35']))
        self.assertEqual([skin.id for skin in manager.unlocked_skins(['34'])], ['default', 'alt'])
        self.assertEqual([skin.id for skin in manager.unlocked_skins(['35'])], ['default', 'alt', 'golden'])
        self.assertEqual(self.import_calls, [])

    def test_preview_loads_only_the_previewed_skin_then_reuses_it(self):
        for folder in ('classic', 'scarlet', 'golden'):
            self._make_skin_tree(folder)
        manager = self.skins_module.SkinManager(self._registry())

        first = manager.get_preview_surface('alt')
        calls_after_first = list(self.import_calls)
        second = manager.get_preview_surface('alt')

        self.assertEqual(first, 'surface:scarlet:down_idle')
        self.assertEqual(first, second)
        self.assertEqual(self.import_calls, calls_after_first)
        self.assertEqual(set(manager.animations_by_skin), {'alt'})

    def test_real_registry_has_all_current_skin_directories_and_states(self):
        # Source-level regression against the actual project assets. No pygame
        # import or image decode is required for this check.
        source = (CODE / 'skins.py').read_text(encoding='utf-8')
        expected_folders = (
            'graphics/character',
            'graphics/character_alt',
            'graphics/character_alt2',
            'graphics/character_alt3',
            'graphics/character_alt4',
            'graphics/character_alt5',
            'graphics/character_golden',
        )
        for folder in expected_folders:
            self.assertIn(folder, source)
            for state in self.skins_module.ANIMATION_STATES:
                path = ROOT / folder / state
                self.assertTrue(path.is_dir(), path)
                self.assertTrue(any(path.iterdir()), path)


if __name__ == '__main__':
    unittest.main()
