import gzip
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == '__main__':
    unittest.main()
