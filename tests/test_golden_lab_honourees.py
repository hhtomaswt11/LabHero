import ast
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
DATA = ROOT / 'data'

HONOUREES = {
    'isabel': {
        'world_image': 'isabel_rocha.png',
        'portrait': 'isabel_rocha.jpg',
        'display_name': 'Isabel Rocha',
    },
    'bernhard': {
        'world_image': 'bernhard_palsson.png',
        'portrait': 'bernhard_palsson.jpg',
        'display_name': 'B. O. Palsson',
    },
    'jens': {
        'world_image': 'jens_nielsen.png',
        'portrait': 'jens_nielsen.jpg',
        'display_name': 'Jens Nielsen',
    },
    'chris': {
        'world_image': 'chris_henry.png',
        'portrait': 'chris_henry.jpg',
        'display_name': 'Chris Henry',
    },
    'ahmad': {
        'world_image': 'ahmad_zeidan.png',
        'portrait': 'ahmad_zeidan.jpg',
        'display_name': 'Ahmad Zeidan',
    },
}


EASTER_MAN = {
    'object_name': 'easter_man',
    'world_image': 'easter_man.png',
    'portrait': 'easter_man.jpg',
}


class GoldenLabHonoureeTests(unittest.TestCase):
    def _player_objects(self):
        root = ET.parse(DATA / 'map_lb.tmx').getroot()
        player_layer = next(
            layer for layer in root.findall('objectgroup')
            if layer.attrib.get('name') == 'Player'
        )
        return {obj.attrib.get('name'): obj for obj in player_layer.findall('object')}

    def _secondary_tileset(self):
        root = ET.parse(DATA / 'map_lb.tmx').getroot()
        tileset_ref = next(
            ts for ts in root.findall('tileset')
            if ts.attrib.get('source') == 'Tilesets/Secondary Characters.tsx'
        )
        firstgid = int(tileset_ref.attrib['firstgid'])
        tsx_root = ET.parse(DATA / 'Tilesets' / 'Secondary Characters.tsx').getroot()
        images = {
            int(tile.attrib['id']): Path(tile.find('image').attrib['source']).name
            for tile in tsx_root.findall('tile')
        }
        return firstgid, images

    def test_all_five_honourees_exist_on_player_layer_with_expected_sprites(self):
        objects = self._player_objects()
        firstgid, images = self._secondary_tileset()
        for object_name, expected in HONOUREES.items():
            self.assertIn(object_name, objects)
            gid = int(objects[object_name].attrib['gid'])
            self.assertEqual(images[gid - firstgid], expected['world_image'])

    def test_all_honouree_portraits_exist(self):
        for expected in HONOUREES.values():
            path = ROOT / 'graphics' / 'dialogues' / expected['portrait']
            self.assertTrue(path.exists(), path)
            self.assertGreater(path.stat().st_size, 0, path)

    def test_level_renders_and_registers_player_layer_honourees(self):
        source = (CODE / 'level.py').read_text(encoding='utf-8')
        self.assertIn('GOLDEN_LAB_DIALOGUE_INTERACTIONS', source)
        self.assertIn("if obj.name in GOLDEN_LAB_DIALOGUE_INTERACTIONS:", source)
        self.assertIn("[self.all_sprites, self.collision_sprites]", source)
        self.assertIn("Interaction((obj.x, obj.y), (obj.width, obj.height), self.interaction_sprites, obj.name)", source)

    def test_player_routes_honourees_to_generic_dialogues(self):
        source = (CODE / 'player.py').read_text(encoding='utf-8')
        for object_name in HONOUREES:
            self.assertIn(repr(object_name), source)
        self.assertIn('*GOLDEN_LAB_HONOUREE_INTERACTIONS', source)
        self.assertIn('self.character = sprite.name', source)
        self.assertIn('self.dialogues()', source)

    def test_dialogues_use_correct_portraits_names_and_historical_topics(self):
        source = (CODE / 'dialogues.py').read_text(encoding='utf-8')
        for object_name, expected in HONOUREES.items():
            self.assertIn(f"self.character == '{object_name}'", source)
            self.assertIn(expected['portrait'], source)
            self.assertIn(expected['display_name'], source)

        # High-level scientific anchors for the homage text.
        for phrase in (
            'OptFlux',
            'COBRA',
            'Saccharomyces cerevisiae',
            'ModelSEED',
            'KBase',
            'industrial biotechnology',
            'food biotechnology',
        ):
            self.assertIn(phrase, source)

    def test_easter_man_tiled_sprite_and_portrait_are_connected(self):
        objects = self._player_objects()
        firstgid, images = self._secondary_tileset()
        self.assertIn(EASTER_MAN['object_name'], objects)
        gid = int(objects[EASTER_MAN['object_name']].attrib['gid'])
        self.assertEqual(images[gid - firstgid], EASTER_MAN['world_image'])

        portrait = ROOT / 'graphics' / 'dialogues' / EASTER_MAN['portrait']
        self.assertTrue(portrait.exists(), portrait)
        self.assertGreater(portrait.stat().st_size, 0, portrait)

    def test_easter_man_uses_golden_lab_generic_dialogue_path(self):
        player = (CODE / 'player.py').read_text(encoding='utf-8')
        level = (CODE / 'level.py').read_text(encoding='utf-8')
        dialogue = (CODE / 'dialogues.py').read_text(encoding='utf-8')

        self.assertIn("'easter_man'", player)
        self.assertIn('GOLDEN_LAB_MYSTERY_INTERACTIONS', player)
        self.assertIn('GOLDEN_LAB_DIALOGUE_INTERACTIONS', level)
        self.assertIn("self.character == 'easter_man'", dialogue)
        self.assertIn('golden_egg_collected', dialogue)
        self.assertIn('is_campaign_complete', dialogue)
        self.assertIn('easter_man.jpg', dialogue)
        self.assertIn("'???'", dialogue)

    def test_honouree_dialogues_are_progression_neutral(self):
        player = (CODE / 'player.py').read_text(encoding='utf-8')
        # The five interactions must remain outside mission-start gating and do
        # nothing except select the generic dialogue character.
        mission_set = ast.literal_eval(
            next(
                node.value for node in ast.parse(player).body
                if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'MISSION_START_INTERACTIONS' for t in node.targets)
            )
        )
        for object_name in HONOUREES:
            self.assertNotIn(object_name, mission_set)


if __name__ == '__main__':
    unittest.main()
