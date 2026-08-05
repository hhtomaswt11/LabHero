"""Regression tests for Mission 26 genotype-environment interaction curves.

Run from the project root with:
    python3 tests/test_mission26.py
"""
from __future__ import annotations

import gzip
import inspect
import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import simulation  # noqa: E402


class Mission26RegressionTests(unittest.TestCase):
    EXPECTED = {
        'wild_type': {
            -25.0: (0.873921507, -21.799493, -10.0),
            -10.0: (0.559050600, -10.0, -10.0),
            -1.0: (0.247660050, -1.0, -10.0),
            0.0: (0.211662950, 0.0, -10.0),
        },
        'knockout': {
            -25.0: (0.870744806, -21.938351, -10.0),
            -10.0: (0.530246853, -10.0, -10.0),
            -1.0: (0.232011700, -1.0, -10.0),
            0.0: (0.0, 0.0, -3.356),
        },
    }

    def _genes(self, sweep_type='wild_type', extra=None):
        genes = simulation._build_active_genes_data()
        if sweep_type == 'knockout':
            genes[simulation.MISSION26_TARGET_GENE] = False
        for gene_id in extra or []:
            genes[gene_id] = False
        return genes

    def _reactions(self, *, extra_change=None, incomplete=False):
        reactions = simulation._build_default_reactions_data()
        if extra_change:
            reaction_id, bound = extra_change
            index = list(simulation.REACTIONS.index).index(reaction_id)
            key = f'reaction_{index}_{bound}'
            reactions[key] = not bool(reactions[key])
        if incomplete:
            reactions.pop(next(iter(reactions)))
        return reactions

    def _row(self, sweep_type, bound_value, *, growth=None, oxygen=None, glucose=None,
             status='ok', diagnostics=None, missing_exchange=None,
             tested_uptake=None):
        expected_growth, expected_oxygen, expected_glucose = self.EXPECTED[sweep_type][float(bound_value)]
        growth = expected_growth if growth is None else growth
        oxygen = expected_oxygen if oxygen is None else oxygen
        glucose = expected_glucose if glucose is None else glucose
        raw = {
            simulation.MISSION26_GLUCOSE_REACTION: glucose,
            simulation.MISSION26_OXYGEN_REACTION: oxygen,
        }
        if missing_exchange:
            raw.pop(missing_exchange, None)
        diag = {
            'method': simulation.MISSION26_METHOD,
            'objective_reaction': simulation.MISSION26_GROWTH_OBJECTIVE,
            'primary_objective_flux': growth,
            'method_score': growth,
            'method_score_name': simulation.MISSION26_EXPECTED_SCORE_NAME,
            'total_absolute_flux': 300.0 + abs(float(bound_value)),
            'active_reaction_count': 40,
        }
        if diagnostics:
            diag.update(diagnostics)
        return {
            'bound_value': float(bound_value),
            'status': status,
            'objective_result': growth,
            'growth_value': growth,
            'tested_reaction_uptake': max(-oxygen, 0.0) if tested_uptake is None else tested_uptake,
            'oxygen_uptake': max(-oxygen, 0.0),
            'exchange_raw_fluxes': raw,
            'exchange_uptake_fluxes': {
                key: max(-value, 0.0) for key, value in raw.items()
            },
            'exchange_secretion_fluxes': {
                key: max(value, 0.0) for key, value in raw.items()
            },
            'tracked_flux_values': {},
            'method_diagnostics': diag,
        }

    def _sweep(self, sweep_type='wild_type', *, values=None, rows=None, method=None,
               objective=None, genes=None, reactions=None, reaction_id=None,
               bound=None, error=None):
        values = list(simulation.MISSION26_SWEEP_VALUES if values is None else values)
        rows = [self._row(sweep_type, value) for value in values] if rows is None else rows
        data = {
            'sweep_id': 'bound_sweep',
            'check_version': 3,
            'method': method or simulation.MISSION26_METHOD,
            'objective': objective or simulation.MISSION26_GROWTH_OBJECTIVE,
            'knocked_out_genes': (
                [simulation.MISSION26_TARGET_GENE] if sweep_type == 'knockout' else []
            ) if genes is None else genes,
            'environment_changed': False,
            'base_genes': self._genes(sweep_type),
            'base_reactions': reactions if reactions is not None else self._reactions(),
            'reaction_id': reaction_id or simulation.MISSION26_SWEEP_REACTION,
            'bound': bound or simulation.MISSION26_SWEEP_BOUND,
            'values': values,
            'rows': rows,
            'selected_production_fluxes': [],
            'tracked_fluxes': [],
        }
        if error:
            data['error'] = error
        return data

    def _record(self, sweep_data, existing=None):
        with patch.object(simulation, 'save_mission26_bound_sweep_check'):
            return simulation._build_mission26_data(
                sweep_data=sweep_data,
                existing_report={} if existing is None else existing,
            )

    def _complete(self, order=('wild_type', 'knockout')):
        report = {}
        for sweep_type in order:
            report = self._record(self._sweep(sweep_type), existing=report)
        return report

    def test_constants_and_progression(self):
        self.assertEqual(simulation.MISSION26_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION26_METHOD, 'FBA')
        self.assertEqual(simulation.MISSION26_TARGET_GENE, 'b3956')
        self.assertEqual(simulation.MISSION26_TARGET_GENE_NAME, 'ppc')
        self.assertEqual(simulation.MISSION26_SWEEP_VALUES, [-25.0, -10.0, -1.0, 0.0])
        self.assertFalse(simulation.is_mission26_unlocked([]))
        self.assertFalse(simulation.is_mission26_unlocked(['24']))
        self.assertTrue(simulation.is_mission26_unlocked(['25']))

    def test_sweep_menu_preserves_wrong_preset_and_rejects_visible_values(self):
        menu_data = {
            'sweep_variable': [[('Oxygen lower bound (EX_o2_e)', 'EX_o2_e:lower')]],
            'sweep_values': [[('Ammonium sensitivity', 'ammonium_sensitivity')]],
        }
        config = simulation._normalise_sweep_config(menu_data)
        self.assertEqual(config['reaction_id'], simulation.MISSION26_SWEEP_REACTION)
        self.assertEqual(config['preset'], 'ammonium_sensitivity')
        self.assertEqual(config['expected_preset'], 'oxygen_transition')
        self.assertFalse(config['preset_matches_variable'])
        self.assertEqual(config['values'], simulation.MISSION23_SWEEP_VALUES)

        valid = self._complete()
        wrong = self._sweep(
            'knockout',
            values=config['values'],
            rows=[],
        )
        wrong.update({
            'variable': config['variable'],
            'preset': config['preset'],
            'expected_preset': config['expected_preset'],
            'preset_matches_variable': config['preset_matches_variable'],
        })
        invalid = self._record(wrong, existing=valid)
        self.assertFalse(invalid['current_sweep_recorded'])
        self.assertEqual(invalid['recorded_sweep_count'], 2)
        self.assertTrue(invalid['evidence_ready'])
        self.assertIn('four oxygen lower-bound values', ' '.join(invalid['current_issues']))
        text = simulation.build_mission26_interaction_report_text(invalid)
        self.assertIn('Latest sweep was not recorded', text)
        self.assertIn('Previously valid Mission 26 curve evidence remains available', text)

    def test_initial_state_contains_two_empty_curves(self):
        with patch.object(simulation, 'save_mission26_bound_sweep_check'):
            report = simulation.initialise_mission26_interaction_curves()
        self.assertEqual(report['recorded_sweep_count'], 0)
        self.assertEqual(report['missing_sweeps'], ['wild_type', 'knockout'])
        self.assertFalse(report['evidence_ready'])

    def test_two_valid_curves_complete_relationship(self):
        report = self._complete()
        self.assertEqual(report['recorded_sweep_count'], 2)
        self.assertTrue(report['curves_complete'])
        self.assertTrue(report['matched_points_complete'])
        self.assertTrue(report['interaction_threshold_supported'])
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['threshold_bound'], 0.0)
        self.assertAlmostEqual(report['growth_retention_by_bound']['-25.0'], 0.996365, delta=1e-5)
        self.assertAlmostEqual(report['growth_retention_by_bound']['-10.0'], 0.94848, delta=1e-5)
        self.assertAlmostEqual(report['growth_retention_by_bound']['-1.0'], 0.93682, delta=1e-5)
        self.assertEqual(report['growth_retention_by_bound']['0.0'], 0.0)

    def test_curves_can_arrive_in_any_order(self):
        report = self._complete(('knockout', 'wild_type'))
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['missing_sweeps'], [])

    def test_one_curve_is_incomplete(self):
        report = self._record(self._sweep('wild_type'))
        self.assertEqual(report['recorded_sweep_count'], 1)
        self.assertEqual(report['missing_sweeps'], ['knockout'])
        self.assertFalse(report['evidence_ready'])

    def test_repeated_curve_replaces_without_duplication(self):
        report = self._complete()
        repeated = self._record(self._sweep('knockout'), existing=report)
        self.assertEqual(repeated['recorded_sweep_count'], 2)
        self.assertEqual(repeated['current_sweep_type'], 'knockout')

    def test_wrong_method_or_objective_is_rejected(self):
        self.assertFalse(self._record(self._sweep(method='pFBA'))['current_sweep_valid'])
        self.assertFalse(self._record(self._sweep(objective='EX_ac_e'))['current_sweep_valid'])

    def test_genotype_must_be_wild_type_or_single_target_knockout(self):
        wrong = self._sweep('wild_type', genes=['b0728'])
        report = self._record(wrong)
        self.assertFalse(report['current_sweep_valid'])
        two = self._sweep('knockout', genes=['b3956', 'b0728'])
        report = self._record(two)
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('either every gene active or only', ' '.join(report['current_issues']))

    def test_explicit_base_gene_payload_must_match_knockout_list(self):
        data = self._sweep('wild_type')
        data['base_genes'][simulation.MISSION26_TARGET_GENE] = False
        report = self._record(data)
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('does not match', ' '.join(report['current_issues']))
        data = self._sweep('wild_type')
        data['base_genes'].pop(next(iter(data['base_genes'])))
        report = self._record(data)
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('base-gene payload is incomplete', ' '.join(report['current_issues']))

    def test_environment_is_key_order_independent(self):
        reordered = dict(reversed(list(self._reactions().items())))
        report = self._record(self._sweep(reactions=reordered))
        self.assertTrue(report['current_sweep_valid'])

    def test_incomplete_or_changed_base_environment_is_rejected(self):
        report = self._record(self._sweep(reactions=self._reactions(incomplete=True)))
        self.assertFalse(report['current_sweep_valid'])
        changed = self._reactions(extra_change=('EX_nh4_e', 'lb'))
        report = self._record(self._sweep(reactions=changed))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('model default', ' '.join(report['current_issues']))

    def test_wrong_reaction_or_bound_is_rejected(self):
        self.assertFalse(self._record(self._sweep(reaction_id='EX_nh4_e'))['current_sweep_valid'])
        self.assertFalse(self._record(self._sweep(bound='upper'))['current_sweep_valid'])

    def test_exact_four_bound_values_are_required(self):
        report = self._record(self._sweep(values=[-25.0, -10.0, -1.0]))
        self.assertFalse(report['current_sweep_valid'])
        rows = [self._row('wild_type', value) for value in simulation.MISSION26_SWEEP_VALUES]
        rows[-1]['bound_value'] = -0.5
        report = self._record(self._sweep(values=[-25.0, -10.0, -1.0, -0.5], rows=rows))
        self.assertFalse(report['current_sweep_valid'])

    def test_rows_may_be_desordered_but_are_normalised(self):
        rows = [self._row('wild_type', value) for value in (0.0, -1.0, -25.0, -10.0)]
        report = self._record(self._sweep(rows=rows))
        self.assertTrue(report['current_sweep_valid'])
        self.assertEqual(
            [row['bound_value'] for row in report['wild_type_sweep_rows']],
            simulation.MISSION26_SWEEP_VALUES,
        )

    def test_duplicate_or_missing_row_is_rejected(self):
        rows = [self._row('wild_type', value) for value in simulation.MISSION26_SWEEP_VALUES]
        rows[-1] = self._row('wild_type', -1.0)
        report = self._record(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('Duplicate', ' '.join(report['current_issues']))
        self.assertIn('Missing', ' '.join(report['current_issues']))

    def test_non_ok_row_is_rejected(self):
        rows = [self._row('wild_type', value) for value in simulation.MISSION26_SWEEP_VALUES]
        rows[1] = self._row('wild_type', -10.0, status='infeasible')
        report = self._record(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])

    def test_growth_missing_is_not_converted_to_zero(self):
        rows = [self._row('knockout', value) for value in simulation.MISSION26_SWEEP_VALUES]
        rows[-1]['growth_value'] = None
        rows[-1]['method_diagnostics']['primary_objective_flux'] = None
        rows[-1]['method_diagnostics']['method_score'] = None
        report = self._record(self._sweep('knockout', rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('Biomass is missing', ' '.join(report['current_issues']))

    def test_visible_objective_and_oxygen_fields_must_match_exchange_evidence(self):
        rows = [self._row('wild_type', value) for value in simulation.MISSION26_SWEEP_VALUES]
        rows[0]['objective_result'] = 0.5
        report = self._record(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('objective result does not match', ' '.join(report['current_issues']))
        rows = [self._row('wild_type', value) for value in simulation.MISSION26_SWEEP_VALUES]
        rows[1]['oxygen_uptake'] = 8.0
        report = self._record(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('oxygen-uptake field does not match', ' '.join(report['current_issues']))

    def test_numeric_glucose_and_oxygen_are_required(self):
        rows = [self._row('wild_type', value) for value in simulation.MISSION26_SWEEP_VALUES]
        rows[0] = self._row('wild_type', -25.0, missing_exchange=simulation.MISSION26_OXYGEN_REACTION)
        report = self._record(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('exchange evidence is incomplete', ' '.join(report['current_issues']))

    def test_positive_growth_rows_require_default_glucose_uptake(self):
        rows = [self._row('wild_type', value) for value in simulation.MISSION26_SWEEP_VALUES]
        rows[1] = self._row('wild_type', -10.0, glucose=-9.0)
        report = self._record(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('model-default glucose uptake', ' '.join(report['current_issues']))

    def test_zero_growth_row_allows_alternative_glucose_optimum_within_capacity(self):
        report = self._record(self._sweep('knockout'))
        self.assertTrue(report['current_sweep_valid'])
        zero_row = report['knockout_sweep_rows'][-1]
        self.assertEqual(zero_row['growth_value'], 0.0)
        self.assertAlmostEqual(zero_row['glucose_uptake'], 3.356, delta=1e-6)

    def test_first_point_must_be_nonbinding(self):
        rows = [self._row('wild_type', value) for value in simulation.MISSION26_SWEEP_VALUES]
        rows[0] = self._row('wild_type', -25.0, oxygen=-25.0)
        report = self._record(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('non-binding', ' '.join(report['current_issues']))

    def test_tighter_points_must_reach_tested_oxygen_capacity(self):
        rows = [self._row('wild_type', value) for value in simulation.MISSION26_SWEEP_VALUES]
        rows[1] = self._row('wild_type', -10.0, oxygen=-8.0)
        report = self._record(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('reach the tested capacity', ' '.join(report['current_issues']))

    def test_tested_uptake_must_match_exchange_evidence(self):
        rows = [self._row('wild_type', value) for value in simulation.MISSION26_SWEEP_VALUES]
        rows[2] = self._row('wild_type', -1.0, tested_uptake=0.0)
        report = self._record(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])

    def test_fba_diagnostics_are_required_and_consistent(self):
        rows = [self._row('wild_type', value) for value in simulation.MISSION26_SWEEP_VALUES]
        rows[0] = self._row('wild_type', -25.0, diagnostics={'method_score_name': 'total_absolute_flux'})
        report = self._record(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        rows[0] = self._row('wild_type', -25.0, diagnostics={'primary_objective_flux': 0.5})
        report = self._record(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])

    def test_relationship_requires_retention_at_positive_oxygen(self):
        report = self._complete()
        altered = dict(report)
        altered['knockout_sweep'] = dict(report['knockout_sweep'])
        altered['knockout_sweep']['rows'] = [dict(row) for row in report['knockout_sweep']['rows']]
        altered['knockout_sweep']['rows'][2]['growth_value'] = 0.01
        rebuilt = self._record(self._sweep('wild_type'), existing=altered)
        self.assertFalse(rebuilt['interaction_threshold_supported'])

    def test_relationship_requires_wild_type_viability_and_knockout_collapse_at_zero(self):
        rows = [self._row('knockout', value) for value in simulation.MISSION26_SWEEP_VALUES]
        rows[-1] = self._row('knockout', 0.0, growth=0.1)
        report = self._record(self._sweep('wild_type'))
        report = self._record(self._sweep('knockout', rows=rows), existing=report)
        self.assertFalse(report['interaction_threshold_supported'])

    def test_invalid_later_sweep_preserves_complete_evidence(self):
        valid = self._complete()
        invalid = self._record(self._sweep(method='pFBA'), existing=valid)
        self.assertFalse(invalid['current_sweep_recorded'])
        self.assertEqual(invalid['recorded_sweep_count'], 2)
        self.assertTrue(invalid['evidence_ready'])
        text = simulation.build_mission26_interaction_report_text(invalid)
        self.assertIn('Latest sweep was not recorded', text)
        self.assertIn('Previously valid Mission 26 curve evidence remains available', text)

    def test_visible_sweep_wrapper_preserves_previous_curve(self):
        existing = self._record(self._sweep('wild_type'))
        with patch.object(simulation, 'load_mission26_bound_sweep_check', return_value=existing):
            with patch.object(simulation, 'save_mission26_bound_sweep_check'):
                report = simulation.run_mission26_interaction_curve_check(self._sweep('knockout'))
        self.assertTrue(report['evidence_ready'])

    def test_answer_aliases_are_accepted(self):
        report = self._complete()
        for answer in (
            '0', '0.0', 'LB 0', 'lower bound 0', 'zero',
            'complete oxygen block', 'oxygen blocked', 'full block',
            'bloqueio completo', 'oxigénio bloqueado',
        ):
            with self.subTest(answer=answer):
                self.assertTrue(simulation.mission26_answer_matches(answer, report))

    def test_wrong_answers_are_rejected(self):
        report = self._complete()
        for answer in ('-25', '-10', '-10.0', '10', '10.0', '-1', 'anaerobic', 'aerobic', 'b3956', 'ppc', ''):
            with self.subTest(answer=answer):
                self.assertFalse(simulation.mission26_answer_matches(answer, report))

    def test_report_exposes_curves_without_declaring_answer(self):
        text = simulation.build_mission26_interaction_report_text(self._complete())
        self.assertIn('Curves recorded: 2/2', text)
        self.assertIn('Evidence complete', text)
        self.assertIn('99.6%', text)
        self.assertIn('94.8%', text)
        self.assertIn('93.7%', text)
        self.assertIn('0.0%', text)
        self.assertNotIn('The answer is zero', text)
        self.assertNotIn('Submit 0', text)
        self.assertNotIn('LB 0 is the answer', text)

    def test_state_is_json_serialisable(self):
        json.dumps(self._complete())

    def test_validator_and_remote_wrapper_launch_no_solver_or_http(self):
        source = inspect.getsource(simulation._mission26_validate_sweep)
        source += inspect.getsource(simulation._build_mission26_data)
        source += inspect.getsource(simulation.run_mission26_interaction_curve_check)
        source += inspect.getsource(simulation.run_mission26_interaction_curve_check_remote)
        self.assertNotIn('simul.simulate', source)
        self.assertNotIn('_http_post_json', source)
        self.assertNotIn('run_bound_sweep(', source)

    def test_window_integrates_visible_local_and_remote_sweeps_and_highlight(self):
        source = (CODE_DIR / 'window.py').read_text()
        self.assertIn("('26', [MISSION26_TARGET_GENE])", source)
        self.assertIn('run_mission26_interaction_curve_check_remote', source)
        self.assertIn('run_mission26_interaction_curve_check(bound_sweep_data)', source)
        self.assertIn('return build_mission26_interaction_report_text(report_data)', source)

    def test_smith_tiled_entry_routes_mission25_then_mission26(self):
        source = (CODE_DIR / 'mission25.py').read_text()
        self.assertIn('from mission26 import Mission26_info', source)
        self.assertIn('self.menu26 = Mission26_info', source)
        self.assertIn("elif '25' in self.missions_completed", source)
        self.assertIn('menu_to_open=self.menu26', source)
        self.assertIn('Dr. Smith', source)
        self.assertNotIn('buttons=False)\n        elif \'25\' in self.missions_activated', source)

    def test_mission26_ui_has_gating_answer_guards_and_correct_scientist(self):
        source = (CODE_DIR / 'mission26.py').read_text()
        self.assertIn('is_mission26_unlocked', source)
        self.assertIn('initialise_mission26_interaction_curves', source)
        self.assertIn('mission26_answer_matches', source)
        self.assertIn('Genotype-Environment Interaction Curve', source)
        self.assertIn('Complete Mission 25', source)
        self.assertIn('Dr. Smith', source)
        self.assertNotIn('Dr. Luna', source)
        self.assertNotIn('Mission27_info', source)
        self.assertNotIn('Mission28_info', source)

    def test_documentation_matches_redesign(self):
        documentation = (PROJECT_ROOT / 'data' / 'missions' / 'mission26.md').read_text()
        self.assertIn('Dr. Smith', documentation)
        self.assertIn('b3956', documentation)
        self.assertIn('-25', documentation)
        self.assertIn('-10', documentation)
        self.assertIn('-1', documentation)
        self.assertNotIn('Dr. Luna', documentation)
        self.assertNotIn('Oxygen Sensitivity Sweep', documentation)

    def test_ppc_gpr_is_single_b3956_gene(self):
        model_path = PROJECT_ROOT / 'data' / 'models' / 'e_coli_core.xml.gz'
        ns = {
            'sbml': 'http://www.sbml.org/sbml/level3/version1/core',
            'fbc': 'http://www.sbml.org/sbml/level3/version1/fbc/version2',
        }
        with gzip.open(model_path, 'rb') as handle:
            root = ET.parse(handle).getroot()
        reaction = next(
            item for item in root.findall('.//sbml:reaction', ns)
            if item.attrib.get('id') == 'R_PPC'
        )
        refs = reaction.findall('.//fbc:geneProductRef', ns)
        self.assertEqual([item.attrib[f"{{{ns['fbc']}}}geneProduct"] for item in refs], ['G_b3956'])

    def test_independent_fba_values_for_both_curves(self):
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
        ppc = reaction_index['R_PPC']
        glucose = reaction_index['R_EX_glc__D_e']
        objective = np.zeros(len(reactions))
        objective[biomass] = -1.0

        for sweep_type, rows in self.EXPECTED.items():
            for bound_value, expected in rows.items():
                with self.subTest(curve=sweep_type, bound=bound_value):
                    current_bounds = list(bounds)
                    current_bounds[oxygen] = (bound_value, current_bounds[oxygen][1])
                    if sweep_type == 'knockout':
                        current_bounds[ppc] = (0.0, 0.0)
                    result = linprog(
                        objective,
                        A_eq=matrix,
                        b_eq=np.zeros(len(species)),
                        bounds=current_bounds,
                        method='highs',
                    )
                    self.assertTrue(result.success)
                    self.assertAlmostEqual(result.x[biomass], expected[0], delta=1e-6)
                    self.assertAlmostEqual(result.x[oxygen], expected[1], delta=1e-5)
                    if expected[0] > 1e-6:
                        self.assertAlmostEqual(result.x[glucose], -10.0, delta=1e-5)

    def test_backend_contract_when_dependencies_exist(self):
        backend_dir = PROJECT_ROOT / 'backend'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        try:
            from app.schemas import SimulateRequest
            from app.simulator import simulate as backend_simulate
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'Backend MEWpy/COBRApy unavailable: {exc}')

        default_env = simulation._build_default_env_conditions_payload()
        for sweep_type, rows in self.EXPECTED.items():
            for bound_value, expected in rows.items():
                env = {reaction: list(bounds) for reaction, bounds in default_env.items()}
                env[simulation.MISSION26_OXYGEN_REACTION][0] = bound_value
                knockouts = [simulation.MISSION26_TARGET_GENE] if sweep_type == 'knockout' else []
                response = backend_simulate(SimulateRequest(
                    method=simulation.MISSION26_METHOD,
                    objective=simulation.MISSION26_GROWTH_OBJECTIVE,
                    gene_knockouts=knockouts,
                    env_conditions=env,
                ))
                self.assertEqual(response.status, 'ok', response.message)
                self.assertAlmostEqual(float(response.primary_objective_flux), expected[0], delta=1e-3)
                self.assertEqual(response.method_score_name, 'primary_objective_flux')
                self.assertAlmostEqual(float(response.fluxes[simulation.MISSION26_OXYGEN_REACTION]), expected[1], delta=1e-3)


if __name__ == '__main__':
    unittest.main()
