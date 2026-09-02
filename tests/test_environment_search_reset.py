import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WINDOW_PATH = ROOT / 'code' / 'window.py'


def _load_search_helpers():
    source = WINDOW_PATH.read_text(encoding='utf-8')
    tree = ast.parse(source)
    wanted = {'_normalise_gene_search_text', '_reaction_matches_search'}
    nodes = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    namespace = {}
    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(WINDOW_PATH), 'exec'), namespace)
    return namespace


class EnvironmentalSearchResetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WINDOW_PATH.read_text(encoding='utf-8')
        cls.helpers = _load_search_helpers()

    def test_reaction_search_matches_id_and_name(self):
        matches = self.helpers['_reaction_matches_search']
        self.assertTrue(matches('EX_o2_e', 'Oxygen exchange', 'EX_o2_e'))
        self.assertTrue(matches('EX_o2_e', 'Oxygen exchange', 'oxygen'))
        self.assertTrue(matches('EX_ac_e', 'Acetate exchange', 'acetate'))
        self.assertFalse(matches('EX_ac_e', 'Acetate exchange', 'oxygen'))

    def test_reaction_search_is_case_and_punctuation_tolerant(self):
        matches = self.helpers['_reaction_matches_search']
        self.assertTrue(matches('EX_glc__D_e', 'D-Glucose exchange', 'd glucose'))
        self.assertTrue(matches('EX_glc__D_e', 'D-Glucose exchange', 'GLC D'))
        self.assertTrue(matches('EX_akg_e', '2-Oxoglutarate exchange', '2 oxoglutarate'))

    def test_small_model_environment_has_gene_style_search_controls(self):
        self.assertIn("'Search exchange: '", self.source)
        self.assertIn("'Search / Refresh'", self.source)
        self.assertIn("'Clear Search'", self.source)
        self.assertIn("'Reset Environment'", self.source)
        self.assertIn("textinput_id='reaction_search'", self.source)

    def test_search_filters_the_complete_reaction_block(self):
        self.assertIn("'widgets': (", self.source)
        self.assertIn("label_widget,", self.source)
        self.assertIn("lb_widget,", self.source)
        self.assertIn("ub_widget,", self.source)
        self.assertIn("margin_widget,", self.source)
        self.assertIn("for widget in entry['widgets']:", self.source)
        self.assertIn("widget.hide()", self.source)
        self.assertIn("widget.show()", self.source)

    def test_reset_restores_each_models_actual_default_bound_state(self):
        self.assertIn(
            "default_lb_bool = bool(REACTIONS.lb.iloc[i] != 0)",
            self.source,
        )
        self.assertIn(
            "default_ub_bool = bool(REACTIONS.ub.iloc[i] != 0)",
            self.source,
        )
        self.assertIn(
            "reaction_default_states[reaction_id] = (",
            self.source,
        )
        self.assertIn("entry['lb'].set_value(default_lb)", self.source)
        self.assertIn("entry['ub'].set_value(default_ub)", self.source)
        self.assertNotIn(
            "for widget in reaction_widgets.values():\n                    widget.set_value(True)",
            self.source,
        )

    def test_reset_also_clears_filter_and_returns_all_reactions(self):
        reset_start = self.source.index('def reset_reaction_toggles')
        reset_end = self.source.index("reaction_search_input = menu_reactions.add.text_input", reset_start)
        reset_body = self.source[reset_start:reset_end]
        self.assertIn("reaction_search_input.set_value('')", reset_body)
        self.assertIn("apply_reaction_search('')", reset_body)
        self.assertIn(
            "'Environment restored to the model-default bounds.'",
            reset_body,
        )


    def test_search_field_is_excluded_from_saved_scientific_environment_payload(self):
        self.assertIn('def _build_clean_reaction_data', self.source)
        self.assertIn(
            "data_reac = _build_clean_reaction_data(",
            self.source,
        )
        clean_start = self.source.index('def _build_clean_reaction_data')
        clean_end = self.source.index('def _build_environmental_summary', clean_start)
        clean_body = self.source[clean_start:clean_end]
        self.assertIn("lb_key = f'reaction_{i}_lb'", clean_body)
        self.assertIn("ub_key = f'reaction_{i}_ub'", clean_body)
        self.assertNotIn('reaction_search', clean_body)


    def test_search_widget_does_not_replace_scientific_reaction_toggle_ids(self):
        self.assertIn("toggleswitch_id=f'reaction_{i}_lb'", self.source)
        self.assertIn("toggleswitch_id=f'reaction_{i}_ub'", self.source)


if __name__ == '__main__':
    unittest.main()
