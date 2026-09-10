import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW_PATH = ROOT / "code" / "window.py"


class EcoliSearchPerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WINDOW_PATH.read_text(encoding="utf-8")

    def _block(self, start_marker, end_marker):
        start = self.source.index(start_marker)
        end = self.source.index(end_marker, start)
        return self.source[start:end]

    def test_gene_search_does_not_filter_on_every_keystroke(self):
        block = self._block(
            "gene_search_input = menu_genes.add.text_input(",
            "menu_genes.add.vertical_margin(10)",
        )
        self.assertNotIn("onchange=apply_gene_search", block)
        self.assertIn("onreturn=apply_gene_search", block)

    def test_environment_search_does_not_filter_on_every_keystroke(self):
        block = self._block(
            "reaction_search_input = menu_reactions.add.text_input(",
            "menu_reactions.add.vertical_margin(10)",
        )
        self.assertNotIn("onchange=apply_reaction_search", block)
        self.assertIn("onreturn=apply_reaction_search", block)

    def test_search_buttons_remain_available(self):
        self.assertIn("menu_genes.add.button('Search', apply_gene_search", self.source)
        self.assertIn("'Search',\n                apply_reaction_search", self.source)

    def test_help_text_explains_when_filtering_runs(self):
        self.assertIn("Type your search, then press Enter or use Search.", self.source)


if __name__ == '__main__':
    unittest.main()
