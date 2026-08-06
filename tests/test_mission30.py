"""Regression tests for Mission 30 redundancy-breakdown threshold.

Run from the project root with:
    python3 tests/test_mission30.py
"""
from __future__ import annotations

import gzip
import json
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

try:
    import pygame  # noqa: F401
except ModuleNotFoundError:
    pygame_stub = types.ModuleType('pygame')
    pygame_stub.Vector2 = lambda *args: tuple(args)
    sys.modules['pygame'] = pygame_stub

try:
    import pygame_menu  # noqa: F401
except ModuleNotFoundError:
    class _Theme:
        def copy(self):
            return _Theme()
    pygame_menu_stub = types.ModuleType('pygame_menu')
    pygame_menu_stub.themes = types.SimpleNamespace(THEME_GREEN=_Theme())
    pygame_menu_stub.font = types.SimpleNamespace(FONT_MUNRO='munro')
    pygame_menu_stub.widgets = types.SimpleNamespace(MENUBAR_STYLE_SIMPLE='simple')
    sys.modules['pygame_menu'] = pygame_menu_stub

_original_platform = sys.platform
try:
    import mewpy  # noqa: F401
    import cobra  # noqa: F401
except ModuleNotFoundError:
    sys.platform = 'emscripten'

import simulation  # noqa: E402
sys.platform = _original_platform


class Mission30RegressionTests(unittest.TestCase):
    EXPECTED = {
        'wild_type': {
            -30.0: ('ok', 0.873921507, 10.0, 21.799493, 518.422086, 48),
            -10.0: ('ok', 0.559050600, 10.0, 10.0, 382.882465, 50),
            -5.0: ('ok', 0.391648451, 10.0, 5.0, 344.364389, 51),
            -2.0: ('ok', 0.283657150, 10.0, 2.0, 335.967153, 51),
        },
        'single_b1723': {},
        'single_b3916': {},
        'double': {
            -30.0: ('ok', 0.704036948, 10.0, 27.526331, 680.110499, 44),
            -10.0: ('ok', 0.247524823, 3.515793, 10.0, 243.625141, 45),
            -5.0: ('ok', 0.075712128, 1.539675, 5.0, 120.731800, 46),
            -2.0: ('infeasible', None, None, None, None, None),
        },
    }
    EXPECTED['single_b1723'] = dict(EXPECTED['wild_type'])
    EXPECTED['single_b3916'] = dict(EXPECTED['wild_type'])

    def _genes(self, curve_type):
        genes = simulation._build_active_genes_data()
        for gene_id in simulation.MISSION30_CURVE_GENES[curve_type]:
            genes[gene_id] = False
        return genes

    def _reactions(self, *, changed=False, incomplete=False):
        reactions = simulation._build_default_reactions_data()
        if changed:
            index = list(simulation.REACTIONS.index).index('EX_glc__D_e')
            reactions[f'reaction_{index}_lb'] = not reactions[f'reaction_{index}_lb']
        if incomplete:
            reactions.pop(next(iter(reactions)))
        return reactions

    def _row(self, curve_type, bound):
        status, growth, glucose, oxygen, total, active = self.EXPECTED[curve_type][float(bound)]
        if status == 'infeasible':
            return simulation._bound_sweep_infeasible_row(bound)
        return {
            'bound_value': float(bound),
            'status': 'ok',
            'objective_result': growth,
            'growth_value': growth,
            'tested_reaction_raw_flux': -oxygen,
            'tested_reaction_uptake': oxygen,
            'oxygen_raw_flux': -oxygen,
            'oxygen_uptake': oxygen,
            'tracked_flux_values': {},
            'exchange_raw_fluxes': {
                'EX_glc__D_e': -glucose,
                'EX_o2_e': -oxygen,
            },
            'exchange_uptake_fluxes': {
                'EX_glc__D_e': glucose,
                'EX_o2_e': oxygen,
            },
            'exchange_secretion_fluxes': {
                'EX_glc__D_e': 0.0,
                'EX_o2_e': 0.0,
            },
            'method_diagnostics': {
                'method': simulation.MISSION30_METHOD,
                'objective_reaction': simulation.MISSION30_GROWTH_OBJECTIVE,
                'primary_objective_flux': growth,
                'method_score': total,
                'method_score_name': simulation.MISSION30_EXPECTED_SCORE_NAME,
                'total_absolute_flux': total,
                'active_reaction_count': active,
            },
        }

    def _sweep(self, curve_type, *, method=None, objective=None, genes=None,
               reactions=None, reaction_id=None, bound=None, preset=None,
               values=None, rows=None):
        genes = genes if genes is not None else self._genes(curve_type)
        knocked = sorted(gene_id for gene_id, active in genes.items() if not active)
        values = list(simulation.MISSION30_SWEEP_VALUES if values is None else values)
        rows = [self._row(curve_type, value) for value in values] if rows is None else rows
        return {
            'sweep_id': 'bound_sweep',
            'check_version': 3,
            'method': method or simulation.MISSION30_METHOD,
            'objective': objective or simulation.MISSION30_GROWTH_OBJECTIVE,
            'knocked_out_genes': knocked,
            'environment_changed': False,
            'base_genes': genes,
            'base_reactions': reactions if reactions is not None else self._reactions(),
            'variable': f'{simulation.MISSION30_SWEEP_REACTION}:lower',
            'preset': preset or simulation.MISSION30_SWEEP_PRESET,
            'expected_preset': 'oxygen_transition',
            'preset_matches_variable': False,
            'reaction_id': reaction_id or simulation.MISSION30_SWEEP_REACTION,
            'reaction_name': 'O2 exchange',
            'bound': bound or simulation.MISSION30_SWEEP_BOUND,
            'bound_label': 'lower bound',
            'values': values,
            'tracked_fluxes': [],
            'selected_production_fluxes': [],
            'rows': rows,
        }

    def _record(self, curve_type, existing=None, **kwargs):
        disabled = [simulation.MISSION30_TARGET_REACTION] if curve_type == 'double' else []
        with (
            patch.object(simulation, 'save_mission30_redundancy_threshold_check'),
            patch.object(simulation, '_mission30_disabled_reactions', return_value=disabled),
        ):
            return simulation._build_mission30_data(
                self._sweep(curve_type, **kwargs),
                existing_report={} if existing is None else existing,
            )

    def _complete(self, order=None):
        report = None
        for curve_type in (order or simulation.MISSION30_CURVE_ORDER):
            report = self._record(curve_type, existing=report)
        return report

    def test_constants_and_unlock(self):
        self.assertEqual(simulation.MISSION30_METHOD, 'pFBA')
        self.assertEqual(simulation.MISSION30_SWEEP_VALUES, [-30.0, -10.0, -5.0, -2.0])
        self.assertFalse(simulation.is_mission30_unlocked(['28']))
        self.assertTrue(simulation.is_mission30_unlocked(['29']))

    def test_curves_accumulate_in_any_order(self):
        report = self._complete(['double', 'single_b3916', 'wild_type', 'single_b1723'])
        self.assertEqual(report['recorded_curve_count'], 4)
        self.assertEqual(report['missing_curves'], [])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['threshold_supported'])
        self.assertEqual(report['threshold_bound'], -2.0)

    def test_expected_relationship(self):
        report = self._complete()
        retention = report['double_retention_by_bound']
        self.assertAlmostEqual(retention['-30.0'], 0.805606616, delta=1e-5)
        self.assertAlmostEqual(retention['-10.0'], 0.442754, delta=1e-5)
        self.assertAlmostEqual(retention['-5.0'], 0.193312, delta=1e-5)
        self.assertIsNone(retention['-2.0'])
        self.assertTrue(report['single_curves_match_wild_type'])
        self.assertTrue(report['double_retention_decreases'])
        self.assertTrue(report['double_infeasible_only_at_threshold'])
        self.assertTrue(report['controls_viable_at_threshold'])
        self.assertTrue(report['gpr_pattern_supported'])

    def test_one_curve_is_incomplete(self):
        report = self._record('wild_type')
        self.assertEqual(report['recorded_curve_count'], 1)
        self.assertFalse(report['evidence_ready'])
        self.assertIn('double', report['missing_curves'])

    def test_wrong_method_objective_and_genotype_rejected(self):
        report = self._record('wild_type', method='FBA')
        self.assertFalse(report['current_curve_recorded'])
        self.assertTrue(any('pFBA' in issue for issue in report['current_issues']))
        report = self._record('wild_type', objective='EX_ac_e')
        self.assertFalse(report['current_curve_recorded'])
        genes = self._genes('double')
        genes['b0118'] = False
        report = self._record('double', genes=genes)
        self.assertFalse(report['current_curve_recorded'])
        self.assertTrue(any('exact' in issue.lower() for issue in report['current_issues']))

    def test_wrong_variable_bound_preset_and_values_rejected(self):
        report = self._record('wild_type', reaction_id='EX_nh4_e')
        self.assertFalse(report['current_curve_recorded'])
        report = self._record('wild_type', bound='upper')
        self.assertFalse(report['current_curve_recorded'])
        report = self._record('wild_type', preset='oxygen_transition')
        self.assertFalse(report['current_curve_recorded'])
        report = self._record('wild_type', values=[-30, -10, -5, 0], rows=[
            self._row('wild_type', -30), self._row('wild_type', -10),
            self._row('wild_type', -5), self._row('wild_type', -2),
        ])
        self.assertFalse(report['current_curve_recorded'])

    def test_environment_and_payload_must_be_complete(self):
        report = self._record('wild_type', reactions=self._reactions(changed=True))
        self.assertFalse(report['current_curve_recorded'])
        report = self._record('wild_type', reactions=self._reactions(incomplete=True))
        self.assertFalse(report['current_curve_recorded'])
        genes = self._genes('wild_type')
        genes.pop(next(iter(genes)))
        report = self._record('wild_type', genes=genes)
        self.assertFalse(report['current_curve_recorded'])

    def test_duplicate_missing_and_out_of_order_rows(self):
        rows = [self._row('wild_type', value) for value in reversed(simulation.MISSION30_SWEEP_VALUES)]
        report = self._record('wild_type', rows=rows)
        self.assertTrue(report['current_curve_recorded'])
        rows = [self._row('wild_type', -30), self._row('wild_type', -10), self._row('wild_type', -5)]
        report = self._record('wild_type', rows=rows)
        self.assertFalse(report['current_curve_recorded'])
        rows = [self._row('wild_type', -30), self._row('wild_type', -10), self._row('wild_type', -5), self._row('wild_type', -5)]
        report = self._record('wild_type', rows=rows)
        self.assertFalse(report['current_curve_recorded'])

    def test_infeasible_is_not_zero(self):
        rows = [self._row('double', value) for value in simulation.MISSION30_SWEEP_VALUES]
        rows[-1]['growth_value'] = 0.0
        rows[-1]['objective_result'] = 0.0
        report = self._record('double', rows=rows)
        self.assertFalse(report['current_curve_recorded'])
        self.assertTrue(any('fabricated' in issue.lower() for issue in report['current_issues']))

        rows = [self._row('double', value) for value in simulation.MISSION30_SWEEP_VALUES]
        rows[-1] = self._row('wild_type', -2)
        rows[-1]['growth_value'] = 0.0
        rows[-1]['objective_result'] = 0.0
        report = self._record('double', rows=rows)
        self.assertFalse(report['current_curve_recorded'])
        self.assertTrue(any('INFEASIBLE' in issue for issue in report['current_issues']))

    def test_infeasible_control_curve_rejected(self):
        rows = [self._row('wild_type', value) for value in simulation.MISSION30_SWEEP_VALUES]
        rows[-1] = simulation._bound_sweep_infeasible_row(-2)
        report = self._record('wild_type', rows=rows)
        self.assertFalse(report['current_curve_recorded'])

    def test_missing_numeric_and_diagnostics_rejected(self):
        rows = [self._row('wild_type', value) for value in simulation.MISSION30_SWEEP_VALUES]
        rows[1]['exchange_raw_fluxes'].pop('EX_o2_e')
        report = self._record('wild_type', rows=rows)
        self.assertFalse(report['current_curve_recorded'])
        rows = [self._row('wild_type', value) for value in simulation.MISSION30_SWEEP_VALUES]
        rows[0]['method_diagnostics'] = {}
        report = self._record('wild_type', rows=rows)
        self.assertFalse(report['current_curve_recorded'])

    def test_invalid_attempt_preserves_complete_evidence(self):
        complete = self._complete()
        invalid = self._record('wild_type', existing=complete, preset='oxygen_transition')
        self.assertFalse(invalid['current_curve_recorded'])
        self.assertEqual(invalid['recorded_curve_count'], 4)
        self.assertTrue(invalid['evidence_ready'])
        text = simulation.build_mission30_redundancy_threshold_report_text(invalid)
        self.assertIn('Previously valid Mission 30 threshold evidence remains available', text)

    def test_answer_validation(self):
        report = self._complete()
        for answer in ('-2', 'LB -2', 'minus two', 'lower bound -2', 'menos dois'):
            self.assertTrue(simulation.mission30_answer_matches(answer, report), answer)
        for answer in ('0', '-5', 'anaerobic', 'b1723', 'PFK'):
            self.assertFalse(simulation.mission30_answer_matches(answer, report), answer)

    def test_report_is_status_aware_and_not_answer_explicit(self):
        text = simulation.build_mission30_redundancy_threshold_report_text(self._complete())
        self.assertIn('INFEASIBLE', text)
        self.assertIn('Evidence complete', text)
        self.assertIn('must not be rewritten as measured growth 0.000', text)
        self.assertNotIn('The answer is -2', text)
        self.assertNotIn('Submit -2', text)

    def test_report_is_json_serialisable(self):
        json.dumps(self._complete())

    def test_bound_sweep_preset_is_preserved(self):
        config = simulation._normalise_sweep_config({
            'sweep_variable': ((f'{simulation.MISSION30_SWEEP_REACTION}:lower', 2),),
            'sweep_values': ((simulation.MISSION30_SWEEP_PRESET, 5),),
        })
        self.assertEqual(config['preset'], simulation.MISSION30_SWEEP_PRESET)
        self.assertEqual(config['values'], simulation.MISSION30_SWEEP_VALUES)

    def test_dr_li_progression_and_window_wiring(self):
        mission29 = (PROJECT_ROOT / 'code' / 'mission29.py').read_text()
        mission30 = (PROJECT_ROOT / 'code' / 'mission30.py').read_text()
        window = (PROJECT_ROOT / 'code' / 'window.py').read_text()
        self.assertIn('Mission30_info', mission29)
        self.assertIn('self.menu30', mission29)
        self.assertIn("elif '29' in self.missions_completed", mission29)
        self.assertIn('graphics/dialogues/li.jpg', mission29)
        self.assertIn('Redundancy Breakdown Threshold', mission30)
        self.assertIn("('30', [MISSION30_GENE_A, MISSION30_GENE_B])", window)
        self.assertIn('run_mission30_redundancy_threshold_check', window)
        self.assertIn("label_id='mission30_redundancy_threshold_check'", window)
        self.assertIn('PFK redundancy threshold: -30, -10, -5, -2', window)

    def test_save_load_contract_exists(self):
        source = (PROJECT_ROOT / 'code' / 'save_load.py').read_text()
        self.assertIn('save_mission30_redundancy_threshold_check', source)
        self.assertIn('load_mission30_redundancy_threshold_check', source)
        self.assertIn('clear_mission30_redundancy_threshold_check', source)

    def test_documentation_exists(self):
        text = (PROJECT_ROOT / 'data' / 'missions' / 'mission30.md').read_text()
        self.assertIn('Redundancy Breakdown Threshold', text)
        self.assertIn('Dr. Li', text)
        self.assertIn('INFEASIBLE', text)
        self.assertIn('b1723', text)
        self.assertIn('b3916', text)

    def test_independent_growth_and_pfba_values(self):
        try:
            import numpy as np
            from scipy.optimize import linprog
        except Exception as exc:
            self.skipTest(f'SciPy unavailable: {exc}')

        model_path = PROJECT_ROOT / 'data' / 'models' / 'e_coli_core.xml.gz'
        ns = {
            'sbml': 'http://www.sbml.org/sbml/level3/version1/core',
            'fbc': 'http://www.sbml.org/sbml/level3/version1/fbc/version2',
        }
        with gzip.open(model_path, 'rb') as handle:
            root = ET.parse(handle).getroot()
        model = root.find('sbml:model', ns)
        species = [item.attrib['id'] for item in model.find('sbml:listOfSpecies', ns)]
        species_index = {item: index for index, item in enumerate(species)}
        parameters = {
            item.attrib['id']: float(item.attrib['value'])
            for item in model.find('sbml:listOfParameters', ns)
        }
        reaction_elements = list(model.find('sbml:listOfReactions', ns))
        reactions = [item.attrib['id'] for item in reaction_elements]
        reaction_index = {item: index for index, item in enumerate(reactions)}
        matrix = np.zeros((len(species), len(reactions)))
        bounds = []
        for column, reaction in enumerate(reaction_elements):
            bounds.append((
                parameters[reaction.attrib[f"{{{ns['fbc']}}}lowerFluxBound"]],
                parameters[reaction.attrib[f"{{{ns['fbc']}}}upperFluxBound"]],
            ))
            reactants = reaction.find('sbml:listOfReactants', ns)
            if reactants is not None:
                for item in reactants:
                    matrix[species_index[item.attrib['species']], column] -= float(item.attrib.get('stoichiometry', '1'))
            products = reaction.find('sbml:listOfProducts', ns)
            if products is not None:
                for item in products:
                    matrix[species_index[item.attrib['species']], column] += float(item.attrib.get('stoichiometry', '1'))

        biomass = reaction_index['R_BIOMASS_Ecoli_core_w_GAM']
        oxygen = reaction_index['R_EX_o2_e']
        objective = np.zeros(len(reactions))
        objective[biomass] = -1.0

        for curve_type in simulation.MISSION30_CURVE_ORDER:
            for bound_value in simulation.MISSION30_SWEEP_VALUES:
                current = list(bounds)
                current[oxygen] = (bound_value, current[oxygen][1])
                if curve_type == 'double':
                    current[reaction_index['R_PFK']] = (0.0, 0.0)
                result = linprog(
                    objective,
                    A_eq=matrix,
                    b_eq=np.zeros(len(species)),
                    bounds=current,
                    method='highs',
                )
                expected = self.EXPECTED[curve_type][bound_value]
                if expected[0] == 'infeasible':
                    self.assertFalse(result.success)
                    continue
                self.assertTrue(result.success)
                self.assertAlmostEqual(result.x[biomass], expected[1], delta=1e-6)

                reaction_count = len(reactions)
                secondary_objective = np.concatenate([np.zeros(reaction_count), np.ones(reaction_count)])
                secondary_matrix = np.hstack([matrix, np.zeros((len(species), reaction_count))])
                biomass_row = np.zeros(2 * reaction_count)
                biomass_row[biomass] = 1.0
                secondary_matrix = np.vstack([secondary_matrix, biomass_row])
                secondary_rhs = np.append(np.zeros(len(species)), result.x[biomass])
                abs_constraints = []
                for index in range(reaction_count):
                    positive = np.zeros(2 * reaction_count)
                    positive[index] = 1.0
                    positive[reaction_count + index] = -1.0
                    abs_constraints.append(positive)
                    negative = np.zeros(2 * reaction_count)
                    negative[index] = -1.0
                    negative[reaction_count + index] = -1.0
                    abs_constraints.append(negative)
                secondary = linprog(
                    secondary_objective,
                    A_ub=np.array(abs_constraints),
                    b_ub=np.zeros(2 * reaction_count),
                    A_eq=secondary_matrix,
                    b_eq=secondary_rhs,
                    bounds=current + [(0.0, None)] * reaction_count,
                    method='highs',
                )
                self.assertTrue(secondary.success)
                fluxes = secondary.x[:reaction_count]
                self.assertAlmostEqual(sum(abs(value) for value in fluxes), expected[4], delta=1e-5)
                self.assertEqual(sum(abs(value) > 1e-9 for value in fluxes), expected[5])


if __name__ == '__main__':
    unittest.main()
