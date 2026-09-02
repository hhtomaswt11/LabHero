import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"


class MissionMenuHorizontalOverflowTests(unittest.TestCase):
    def test_all_mission_menus_disable_horizontal_overflow(self):
        failures = []
        menu_count = 0

        for mission_path in sorted(CODE.glob("mission[0-9][0-9].py")):
            tree = ast.parse(mission_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (
                    isinstance(func, ast.Attribute)
                    and func.attr == "Menu"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "pygame_menu"
                ):
                    continue

                menu_count += 1
                overflow = next(
                    (kw.value for kw in node.keywords if kw.arg == "overflow"),
                    None,
                )
                if overflow is None:
                    failures.append(
                        f"{mission_path.name}:{node.lineno} missing overflow=(False, True)"
                    )
                    continue

                ok = (
                    isinstance(overflow, ast.Tuple)
                    and len(overflow.elts) == 2
                    and isinstance(overflow.elts[0], ast.Constant)
                    and overflow.elts[0].value is False
                    and isinstance(overflow.elts[1], ast.Constant)
                    and overflow.elts[1].value is True
                )
                if not ok:
                    failures.append(
                        f"{mission_path.name}:{node.lineno} has unexpected overflow setting"
                    )

        self.assertGreater(menu_count, 150)
        self.assertEqual([], failures, "\n".join(failures))

    def test_fix_is_scoped_to_mission_modules(self):
        # The global async runner is intentionally untouched; Books, simulator,
        # Settings and other menus keep their existing scrolling behaviour.
        source = (CODE / "async_menu.py").read_text(encoding="utf-8")
        self.assertNotIn("overflow=(False, True)", source)


if __name__ == "__main__":
    unittest.main()
