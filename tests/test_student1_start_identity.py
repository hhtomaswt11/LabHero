
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from student_identity import infer_name_confirmed, normalize_student_name, validate_student_name


class StudentIdentityRulesTests(unittest.TestCase):
    def test_normalize_name_collapses_whitespace(self):
        self.assertEqual(normalize_student_name("  Tomás   Melo  "), "Tomás Melo")

    def test_blank_or_single_character_name_is_rejected(self):
        self.assertFalse(validate_student_name(" ")[0])
        self.assertFalse(validate_student_name("A")[0])

    def test_unicode_name_is_preserved(self):
        valid, name, _ = validate_student_name("  João  D'Ávila ")
        self.assertTrue(valid)
        self.assertEqual(name, "João D'Ávila")

    def test_explicit_name_confirmed_flag_is_authoritative(self):
        self.assertFalse(infer_name_confirmed(
            "Someone", ["01"], ["01"], {"name_confirmed": False}, "Margaret Dayhoff"
        ))
        self.assertTrue(infer_name_confirmed(
            "Margaret Dayhoff", [], [], {"name_confirmed": True}, "Margaret Dayhoff"
        ))

    def test_historic_progress_is_treated_as_registered(self):
        self.assertTrue(infer_name_confirmed(
            "Margaret Dayhoff", ["01"], [], {}, "Margaret Dayhoff"
        ))

    def test_fresh_historic_placeholder_is_not_registered(self):
        self.assertFalse(infer_name_confirmed(
            "Margaret Dayhoff", [], [], {}, "Margaret Dayhoff"
        ))


class StudentStartNpcIntegrationTests(unittest.TestCase):
    def test_tmx_contains_alves_start_npc(self):
        root = ET.parse(ROOT / "data" / "map_lb.tmx").getroot()
        player_layer = next(
            layer for layer in root.findall("objectgroup")
            if layer.get("name") == "Player"
        )
        alves = [obj for obj in player_layer.findall("object") if obj.get("name") == "Alves"]
        self.assertEqual(len(alves), 1)
        self.assertGreater(int(alves[0].get("gid")), 0)

    def test_secondary_character_gid_resolves_to_start_png(self):
        root = ET.parse(ROOT / "data" / "map_lb.tmx").getroot()
        player_layer = next(
            layer for layer in root.findall("objectgroup")
            if layer.get("name") == "Player"
        )
        alves = next(obj for obj in player_layer.findall("object") if obj.get("name") == "Alves")
        alves_gid = int(alves.get("gid"))

        secondary = next(
            ts for ts in root.findall("tileset")
            if ts.get("source") == "Tilesets/Secondary Characters.tsx"
        )
        secondary_firstgid = int(secondary.get("firstgid"))
        later_firstgids = sorted(
            int(ts.get("firstgid"))
            for ts in root.findall("tileset")
            if int(ts.get("firstgid")) > secondary_firstgid
        )
        next_firstgid = later_firstgids[0] if later_firstgids else None
        self.assertGreaterEqual(alves_gid, secondary_firstgid)
        if next_firstgid is not None:
            self.assertLess(alves_gid, next_firstgid)

        local_tile_id = alves_gid - secondary_firstgid
        tileset = ET.parse(ROOT / "data" / "Tilesets" / "Secondary Characters.tsx").getroot()
        tile = tileset.find(f"./tile[@id='{local_tile_id}']")
        self.assertIsNotNone(tile)
        self.assertTrue(tile.find("image").get("source").endswith("graphics/sec-characters/start.png"))

    def test_level_registers_and_renders_alves(self):
        source = (ROOT / "code" / "level.py").read_text(encoding="utf-8")
        self.assertIn("if obj.name == 'Alves':", source)
        self.assertIn("student_registration = self.toggle_student_registration", source)
        self.assertIn("StudentRegistrationMenu", source)

    def test_player_blocks_mission_start_until_registered(self):
        source = (ROOT / "code" / "player.py").read_text(encoding="utf-8")
        self.assertIn("MISSION_START_INTERACTIONS", source)
        self.assertIn("and not self.name_confirmed", source)
        self.assertIn("register your name with Dr. Melo", source)

    def test_settings_no_longer_edits_student_name(self):
        source = (ROOT / "code" / "menu_2.py").read_text(encoding="utf-8")
        self.assertNotIn("menu.add.text_input('Name: '", source)
        self.assertIn("Student:", source)
        self.assertIn("self.font_path = get_resource_path('font/LycheeSoda.ttf')", source)
        self.assertIn("font_name=self.font_path", source)
        self.assertNotIn("font_name=font_path", source)

    def test_start_npc_uses_melo_identity_and_portrait(self):
        source = (ROOT / "code" / "dialogues.py").read_text(encoding="utf-8")
        start_branch = source.split("elif self.character == 'Alves'", 1)[1].split(
            "elif self.character == 'Nuno'", 1
        )[0]
        self.assertIn("graphics/dialogues/melo.jpg", start_branch)
        self.assertIn("get_dialogue_text_surface(self.font_nome, 'Dr. Melo')", start_branch)
        self.assertNotIn("graphics/dialogues/alves.jpg", start_branch)
        self.assertNotIn("'Dr. Alves'", start_branch)

    def test_nuno_alves_desk_dialogue_is_not_renamed(self):
        source = (ROOT / "code" / "dialogues.py").read_text(encoding="utf-8")
        nuno_branch = source.split("elif self.character == 'Nuno'", 1)[1].split(
            "elif self.character == 'Pacheco'", 1
        )[0]
        self.assertIn("Hello! My name is Dr. Nuno Alves!", nuno_branch)
        self.assertIn("graphics/dialogues/Nuno.jpg", nuno_branch)
        self.assertIn("get_dialogue_text_surface(self.font_nome, 'Dr. Alves')", nuno_branch)
        self.assertNotIn("Dr. Melo", nuno_branch)


if __name__ == "__main__":
    unittest.main()
