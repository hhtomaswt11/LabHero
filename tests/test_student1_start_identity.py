
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
        self.assertEqual(alves[0].get("gid"), "241")

    def test_secondary_character_gid_resolves_to_start_png(self):
        root = ET.parse(ROOT / "data" / "map_lb.tmx").getroot()
        secondary = next(
            ts for ts in root.findall("tileset")
            if ts.get("source") == "Tilesets/Secondary Characters.tsx"
        )
        self.assertEqual(int(secondary.get("firstgid")), 209)
        tileset = ET.parse(ROOT / "data" / "Tilesets" / "Secondary Characters.tsx").getroot()
        tile = tileset.find("./tile[@id='32']")
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
        self.assertIn("register your name with Dr. Alves", source)

    def test_settings_no_longer_edits_student_name(self):
        source = (ROOT / "code" / "menu_2.py").read_text(encoding="utf-8")
        self.assertNotIn("menu.add.text_input('Name: '", source)
        self.assertIn("Student:", source)
        self.assertIn("self.font_path = get_resource_path('font/LycheeSoda.ttf')", source)
        self.assertIn("font_name=self.font_path", source)
        self.assertNotIn("font_name=font_path", source)

    def test_alves_uses_new_portrait(self):
        source = (ROOT / "code" / "dialogues.py").read_text(encoding="utf-8")
        self.assertIn("self.character == 'Alves'", source)
        self.assertIn("graphics/dialogues/alves.jpg", source)


if __name__ == "__main__":
    unittest.main()
