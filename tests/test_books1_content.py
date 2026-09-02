import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT_PATH = ROOT / "code" / "book_content.py"


def load_book_content():
    spec = importlib.util.spec_from_file_location("book_content_under_test", CONTENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Books1ContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = load_book_content()
        cls.books = {book["id"]: book for book in cls.content.BOOK_LIBRARY}

    def test_exact_six_runtime_books(self):
        self.assertEqual(
            tuple(self.books),
            (
                "how_to_play",
                "how_to_simulate",
                "brief_history",
                "intro_modelling",
                "ecoli",
                "eat_breathe_love",
            ),
        )

    def test_markdown_mirrors_match_runtime_books(self):
        expected = {
            "how_to_play": "How to Play.md",
            "how_to_simulate": "How to Simulate.md",
            "brief_history": "A Brief History of Microorganisms.md",
            "intro_modelling": "Intro to modelling.md",
            "ecoli": "E. coli Basics.md",
            "eat_breathe_love": "Eat, Breathe and Love.md",
        }
        directory = ROOT / "data" / "books"
        self.assertEqual(
            {path.name for path in directory.glob("*.md")},
            set(expected.values()),
        )
        for book_id, filename in expected.items():
            text = (directory / filename).read_text(encoding="utf-8")
            self.assertIn(self.books[book_id]["title"], text)
            for section_title, _ in self.books[book_id]["sections"]:
                self.assertIn(f"## {section_title}", text)

    def test_simulation_reference_covers_all_supported_methods(self):
        text = (ROOT / "data" / "books" / "How to Simulate.md").read_text(encoding="utf-8")
        for term in ("FBA", "pFBA", "lMOMA", "ROOM"):
            self.assertIn(term, text)

    def test_room_reference_keeps_mission33_contract_terms(self):
        text = (ROOT / "data" / "books" / "How to Simulate.md").read_text(encoding="utf-8")
        for term in ("pre-knockout", "same environment", "delta", "epsilon", "integer ROOM"):
            self.assertIn(term, text)

    def test_simulation_book_distinguishes_core_quantities(self):
        text = (ROOT / "data" / "books" / "How to Simulate.md").read_text(encoding="utf-8").lower()
        self.assertIn("primary objective flux", text)
        self.assertIn("predicted growth rate", text)
        self.assertIn("method score", text)
        self.assertIn("not automatically better", text)

    def test_bounds_are_described_as_permissions_not_forced_fluxes(self):
        text = (ROOT / "data" / "books" / "How to Simulate.md").read_text(encoding="utf-8").lower()
        self.assertIn("does not force", text)
        self.assertIn("actual exchange flux", text)
        self.assertIn("non-binding", text)

    def test_gpr_and_context_dependence_are_explicit(self):
        text = "\n".join(
            (ROOT / "data" / "books" / name).read_text(encoding="utf-8")
            for name in ("How to Simulate.md", "Intro to modelling.md", "E. coli Basics.md")
        )
        self.assertIn("GPR", text)
        self.assertIn("AND", text)
        self.assertIn("OR", text)
        self.assertIn("context dependent", text)

    def test_easy_and_normal_modes_are_documented(self):
        text = (ROOT / "data" / "books" / "How to Play.md").read_text(encoding="utf-8")
        self.assertIn("Normal contains all 40 missions", text)
        self.assertIn("Easy is the curated 11-mission", text)
        self.assertIn("5 points", text)
        self.assertIn("3 after one hint", text)

    def test_yeast_and_imm904_are_documented(self):
        text = (ROOT / "data" / "books" / "Eat, Breathe and Love.md").read_text(encoding="utf-8")
        self.assertIn("Saccharomyces cerevisiae", text)
        self.assertIn("iMM904", text)
        self.assertIn("Mission 36", text)

    def test_no_obsolete_unused_how_to_date_file(self):
        self.assertFalse((ROOT / "data" / "books" / "How to Date a Model.md").exists())

    def test_books_runtime_uses_canonical_content_module(self):
        source = (ROOT / "code" / "books.py").read_text(encoding="utf-8")
        book_ui = (ROOT / "code" / "book_ui.py").read_text(encoding="utf-8")
        self.assertIn("from book_content import BOOK_LIBRARY, BOOK_BY_ID", source)
        self.assertIn("for book in BOOK_LIBRARY:", source)
        self.assertIn("from book_ui import populate_book_menu", source)
        self.assertIn("for section_title, paragraphs in book['sections']:", book_ui)


if __name__ == "__main__":
    unittest.main()
