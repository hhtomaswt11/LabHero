import ast
import gzip
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_function_from_source(path, function_name, globals_dict=None):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    node = next(
        item for item in tree.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == function_name
    )
    module = ast.Module(body=[node], type_ignores=[])
    namespace = dict(globals_dict or {})
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace[function_name]


def _backend_reaction_names():
    model_path = ROOT / 'backend' / 'models' / 'e_coli_core.xml.gz'
    with gzip.open(model_path, 'rb') as handle:
        sbml = ET.parse(handle).getroot()

    names = {}
    for element in sbml.iter():
        if not element.tag.endswith('reaction'):
            continue
        raw_id = element.attrib.get('id')
        if not raw_id:
            continue
        reaction_id = raw_id[2:] if raw_id.startswith('R_') else raw_id
        names[reaction_id] = (element.attrib.get('name') or reaction_id).strip() or reaction_id
    return names


class ObjectiveReactionLabelTests(unittest.TestCase):
    def setUp(self):
        metadata_path = ROOT / 'data' / 'models' / 'e_coli_core_meta.json'
        self.metadata = json.loads(metadata_path.read_text(encoding='utf-8'))

    def test_all_ecoli_objectives_have_backend_model_names(self):
        table = self.metadata['reactions_all']
        reaction_ids = table['index']
        reaction_names = table['name']
        self.assertEqual(len(reaction_ids), len(reaction_names))
        self.assertEqual(len(reaction_ids), 95)

        backend_names = _backend_reaction_names()
        self.assertEqual(set(reaction_ids), set(backend_names))
        for reaction_id, reaction_name in zip(reaction_ids, reaction_names):
            self.assertEqual(reaction_name, backend_names[reaction_id])

    def test_known_objective_labels_are_human_readable(self):
        table = self.metadata['reactions_all']
        names = dict(zip(table['index'], table['name']))
        self.assertEqual(
            names['BIOMASS_Ecoli_core_w_GAM'],
            'Biomass Objective Function with GAM',
        )
        self.assertEqual(names['EX_glc__D_e'], 'D-Glucose exchange')
        self.assertEqual(names['PFK'], 'Phosphofructokinase')

    def test_model_registry_builds_name_plus_id_objective_labels(self):
        source = (ROOT / 'code' / 'model_registry.py').read_text(encoding='utf-8')
        self.assertIn("'objective_options': objective_options", source)
        self.assertIn("f'{reaction_name} ({reaction_id})'", source)

    def test_objective_dropdown_keeps_reaction_id_as_solver_value(self):
        source = (ROOT / 'code' / 'window.py').read_text(encoding='utf-8')
        self.assertIn("objective_labels.get(reaction_id, reaction_id)", source)
        self.assertIn("reaction_id,", source)
        self.assertIn("dropselect_id='objective'", source)

    def test_objective_dropdown_has_room_for_readable_labels(self):
        source = (ROOT / 'code' / 'window.py').read_text(encoding='utf-8')
        self.assertIn("'Objective reaction:'", source)
        self.assertIn('selection_box_width=850', source)
        self.assertIn('font_size=20', source)

    def test_objective_dropdown_extracts_internal_id_not_display_label(self):
        helper = _load_function_from_source(
            ROOT / 'code' / 'window.py',
            '_selected_menu_value',
            {'normalise_method_name': lambda value: value},
        )
        label = 'Biomass Objective Function with GAM (BIOMASS_Ecoli_core_w_GAM)'
        reaction_id = 'BIOMASS_Ecoli_core_w_GAM'
        for raw_value in (
            [(label, reaction_id)],
            [[label, reaction_id]],
            [(label, reaction_id), 0],
            (label, reaction_id),
        ):
            with self.subTest(raw_value=raw_value):
                self.assertEqual(
                    helper({'objective': raw_value}, 'objective'),
                    reaction_id,
                )
        self.assertEqual(
            helper({'method': [('Linear MOMA (lMOMA)', 'lmoma'), 2]}, 'method'),
            'lmoma',
        )

    def test_simulation_file_persists_canonical_method_and_objective_scalars(self):
        source = (ROOT / 'code' / 'window.py').read_text(encoding='utf-8')
        self.assertIn("saved_method_data = {'method': simulation_method}", source)
        self.assertIn("saved_objective_data = {'objective': objective_name}", source)
        self.assertIn(
            "save_simulation_file([saved_method_data, saved_objective_data, data_genes, data_reac, data_fluxes, {'model_id': self.model_id}])",
            source,
        )

    def test_legacy_saved_dropdown_reader_prefers_internal_value(self):
        helper = _load_function_from_source(
            ROOT / 'code' / 'simulation.py',
            '_saved_menu_scalar',
        )
        label = 'D-Glucose exchange (EX_glc__D_e)'
        reaction_id = 'EX_glc__D_e'
        self.assertEqual(
            helper({'objective': [(label, reaction_id), 7]}, 'objective'),
            reaction_id,
        )
        self.assertEqual(
            helper({'objective': 'BIOMASS_SC5_notrace'}, 'objective'),
            'BIOMASS_SC5_notrace',
        )

    def test_failed_simulation_result_shows_error_details(self):
        source = (ROOT / 'code' / 'window.py').read_text(encoding='utf-8')
        self.assertIn("objective_result.startswith(('Error:', 'Simulation error:'))", source)
        self.assertIn("text += f'\\n{objective_result}'", source)


if __name__ == '__main__':
    unittest.main()
