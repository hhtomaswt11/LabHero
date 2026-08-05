"""Regression tests for Mission 23 nutrient sensitivity curve.

Run from the project root with:
    python3 tests/test_mission23.py
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


class Mission23RegressionTests(unittest.TestCase):
    VALUES = [-5.0, -4.0, -2.0, -1.0]
    EXPECTED = {
        -5.0: {
            'growth': 0.873921507,
            'nh4': -4.765319,
            'glucose': -10.0,
            'oxygen': -21.799493,
            'phosphate': -3.214895,
            'acetate': 0.0,
            'co2': 22.809833,
            'total': 518.422086,
            'active': 48,
        },
        -4.0: {
            'growth': 0.733568,
            'nh4': -4.0,
            'glucose': -10.0,
            'oxygen': -15.685282,
            'phosphate': -2.698,
            'acetate': 6.124642,
            'co2': 16.533360,
            'total': 438.178773,
            'active': 52,
        },
        -2.0: {
            'growth': 0.366784,
            'nh4': -2.0,
            'glucose': -5.623591,
            'oxygen': -8.459904,
            'phosphate': -1.349,
            'acetate': 4.624462,
            'co2': 8.883943,
            'total': 246.860750,
            'active': 47,
        },
        -1.0: {
            'growth': 0.183392,
            'nh4': -1.0,
            'glucose': -3.277906,
            'oxygen': -5.162174,
            'phosphate': -0.6745,
            'acetate': 3.244453,
            'co2': 5.374194,
            'total': 151.863153,
            'active': 47,
        },
    }

    def _row(self, value, *, missing_medium=None, missing_tracked=None, diagnostics=None, status='ok'):
        data = self.EXPECTED[float(value)]
        raw = {
            'EX_nh4_e': data['nh4'],
            'EX_glc__D_e': data['glucose'],
            'EX_o2_e': data['oxygen'],
            'EX_pi_e': data['phosphate'],
        }
        tracked = {
            'EX_ac_e': data['acetate'],
            'EX_co2_e': data['co2'],
        }
        raw.pop(missing_medium, None)
        tracked.pop(missing_tracked, None)
        diag = {
            'method': simulation.MISSION23_METHOD,
            'objective_reaction': simulation.MISSION23_GROWTH_OBJECTIVE,
            'primary_objective_flux': data['growth'],
            'method_score': data['total'],
            'method_score_name': simulation.MISSION23_EXPECTED_SECONDARY_CRITERION,
            'total_absolute_flux': data['total'],
            'active_reaction_count': data['active'],
        }
        if diagnostics:
            diag.update(diagnostics)
        return {
            'bound_value': float(value),
            'status': status,
            'growth_value': data['growth'] if status == 'ok' else None,
            'exchange_raw_fluxes': raw if status == 'ok' else {},
            'tracked_flux_values': tracked if status == 'ok' else {},
            'method_diagnostics': diag if status == 'ok' else {},
        }

    def _sweep(self, *, rows=None, method=None, objective=None, genes=None, reactions=None,
               reaction_id=None, bound=None, values=None, selected=None, error=None):
        data = {
            'sweep_id': 'bound_sweep',
            'check_version': 3,
            'method': method or simulation.MISSION23_METHOD,
            'objective': objective or simulation.MISSION23_GROWTH_OBJECTIVE,
            'knocked_out_genes': list(genes or []),
            'environment_changed': False,
            'base_genes': simulation._build_active_genes_data(),
            'base_reactions': reactions or simulation._build_default_reactions_data(),
            'variable': 'EX_nh4_e:lower',
            'preset': 'ammonium_sensitivity',
            'reaction_id': reaction_id or simulation.MISSION23_SWEEP_REACTION,
            'reaction_name': simulation.MISSION23_SWEEP_REACTION_NAME,
            'bound': bound or simulation.MISSION23_SWEEP_BOUND,
            'bound_label': simulation.MISSION23_SWEEP_BOUND_LABEL,
            'values': list(values or self.VALUES),
            'tracked_fluxes': list(selected or simulation.MISSION23_REQUIRED_TRACKED_FLUXES),
            'selected_production_fluxes': list(selected or simulation.MISSION23_REQUIRED_TRACKED_FLUXES),
            'rows': rows if rows is not None else [self._row(value) for value in self.VALUES],
        }
        if error:
            data['error'] = error
        return data

    def _build(self, sweep=None, existing=None):
        with patch.object(simulation, 'save_mission23_comparison_check'):
            return simulation._build_mission23_data(
                self._sweep() if sweep is None else sweep,
                existing_report=existing,
            )

    def test_progression_and_redesign_constants(self):
        self.assertFalse(simulation.is_mission23_unlocked([]))
        self.assertFalse(simulation.is_mission23_unlocked(['21']))
        self.assertTrue(simulation.is_mission23_unlocked(['22']))
        self.assertEqual(simulation.MISSION23_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION23_METHOD, 'pFBA')
        self.assertEqual(simulation.MISSION23_SWEEP_REACTION, 'EX_nh4_e')
        self.assertEqual(simulation.MISSION23_SWEEP_VALUES, self.VALUES)
        self.assertEqual(simulation.MISSION23_REQUIRED_TRACKED_FLUXES, ['EX_ac_e', 'EX_co2_e'])
        self.assertFalse(hasattr(simulation, 'MISSION23_MIN_PRODUCTION_INCREASE'))
        self.assertFalse(hasattr(simulation, 'MISSION23_TARGET_OBJECTIVE'))

    def test_initial_state_is_json_serialisable(self):
        with patch.object(simulation, 'save_mission23_comparison_check'):
            report = simulation.initialise_mission23_nutrient_sensitivity_curve()
        self.assertEqual(report['recorded_point_count'], 0)
        self.assertEqual(report['missing_bound_values'], self.VALUES)
        self.assertFalse(report['evidence_ready'])
        json.dumps(report)

    def test_sweep_menu_normalises_ammonium_internal_values(self):
        menu_data = {
            'sweep_variable': [[('Ammonium lower bound (EX_nh4_e)', 'EX_nh4_e:lower')]],
            'sweep_values': [[('Ammonium sensitivity', 'ammonium_sensitivity')]],
        }
        config = simulation._normalise_sweep_config(menu_data)
        self.assertEqual(config['reaction_id'], 'EX_nh4_e')
        self.assertEqual(config['preset'], 'ammonium_sensitivity')
        self.assertEqual(config['values'], self.VALUES)

    def test_default_environment_reader_is_order_independent(self):
        reactions = simulation._build_default_reactions_data()
        expected = simulation._mission23_base_environment_status(reactions)
        self.assertTrue(expected['environment_default'])
        self.assertEqual(
            simulation._mission23_base_environment_status(dict(reversed(list(reactions.items())))),
            expected,
        )

    def test_incomplete_explicit_environment_is_rejected(self):
        reactions = simulation._build_default_reactions_data()
        reactions.pop('reaction_0_ub')
        report = self._build(self._sweep(reactions=reactions))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('payload is incomplete', ' '.join(report['current_issues']))

    def test_complete_sweep_records_four_points_and_supports_answer(self):
        report = self._build()
        self.assertTrue(report['current_sweep_valid'], report['current_issues'])
        self.assertTrue(report['current_sweep_recorded'])
        self.assertEqual(report['recorded_point_count'], 4)
        self.assertTrue(report['growth_trend'])
        self.assertTrue(report['ammonium_uptake_trend'])
        self.assertEqual(report['new_secretion_candidates'], ['EX_ac_e'])
        self.assertTrue(report['ready_to_deliver'])

    def test_visible_rows_preserve_scientific_values(self):
        report = self._build()
        rows = {row['bound_value']: row for row in report['sweep_rows']}
        self.assertAlmostEqual(rows[-5.0]['growth_value'], 0.873921507, delta=1e-6)
        self.assertAlmostEqual(rows[-5.0]['ammonium_uptake'], 4.765319, delta=1e-6)
        self.assertAlmostEqual(rows[-4.0]['tracked_flux_values']['EX_ac_e'], 6.124642, delta=1e-6)
        self.assertAlmostEqual(rows[-1.0]['tracked_flux_values']['EX_co2_e'], 5.374194, delta=1e-6)

    def test_rows_can_arrive_in_any_order(self):
        report = self._build(self._sweep(rows=[self._row(v) for v in reversed(self.VALUES)]))
        self.assertTrue(report['ready_to_deliver'], report['current_issues'])
        self.assertEqual(report['recorded_bound_values'], self.VALUES)

    def test_repeated_valid_sweep_updates_without_duplication(self):
        first = self._build()
        second = self._build(self._sweep(), existing=first)
        self.assertEqual(second['recorded_point_count'], 4)
        self.assertEqual(len(second['sweep_rows']), 4)

    def test_method_objective_gene_and_variable_guards(self):
        cases = [
            self._sweep(method='FBA'),
            self._sweep(objective='EX_ac_e'),
            self._sweep(genes=['b0728']),
            self._sweep(reaction_id='EX_o2_e'),
            self._sweep(bound='upper'),
        ]
        for sweep in cases:
            with self.subTest(sweep=sweep.get('method'), reaction=sweep.get('reaction_id'), bound=sweep.get('bound')):
                self.assertFalse(self._build(sweep)['current_sweep_valid'])

    def test_nondefault_base_environment_is_rejected(self):
        reactions = simulation._build_default_reactions_data()
        oxygen_index = list(simulation.REACTIONS.index).index('EX_o2_e')
        reactions[f'reaction_{oxygen_index}_lb'] = False
        report = self._build(self._sweep(reactions=reactions))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('model default', ' '.join(report['current_issues']))

    def test_exact_required_values_are_enforced(self):
        report = self._build(self._sweep(values=[-5, -4, -3, -1]))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('-5, -4, -2 and -1', ' '.join(report['current_issues']))

    def test_required_production_panel_must_be_selected(self):
        report = self._build(self._sweep(selected=['EX_ac_e']))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('EX_ac_e and EX_co2_e', ' '.join(report['current_issues']))

    def test_missing_and_infeasible_rows_are_not_treated_as_zero(self):
        missing = self._build(self._sweep(rows=[self._row(v) for v in self.VALUES[:-1]]))
        self.assertFalse(missing['current_sweep_valid'])
        infeasible_rows = [self._row(v) for v in self.VALUES]
        infeasible_rows[2] = self._row(-2, status='infeasible')
        infeasible = self._build(self._sweep(rows=infeasible_rows))
        self.assertFalse(infeasible['current_sweep_valid'])
        self.assertIn('did not return an optimal measurable result', ' '.join(infeasible['current_issues']))

    def test_missing_medium_flux_is_rejected(self):
        rows = [self._row(v) for v in self.VALUES]
        rows[1] = self._row(-4, missing_medium='EX_pi_e')
        report = self._build(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('Exchange Flux evidence is incomplete', ' '.join(report['current_issues']))

    def test_missing_production_flux_is_rejected(self):
        rows = [self._row(v) for v in self.VALUES]
        rows[1] = self._row(-4, missing_tracked='EX_co2_e')
        report = self._build(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('Production Flux evidence is incomplete', ' '.join(report['current_issues']))

    def test_pfba_diagnostics_are_required_and_separate_from_biomass(self):
        rows = [self._row(v) for v in self.VALUES]
        rows[0] = self._row(-5, diagnostics={'method_score_name': 'primary_objective_flux'})
        report = self._build(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('secondary criterion is missing', ' '.join(report['current_issues']))

    def test_primary_flux_must_match_biomass(self):
        rows = [self._row(v) for v in self.VALUES]
        rows[0] = self._row(-5, diagnostics={'primary_objective_flux': 0.2})
        report = self._build(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('does not match biomass', ' '.join(report['current_issues']))

    def test_method_score_must_match_total_absolute_flux(self):
        rows = [self._row(v) for v in self.VALUES]
        rows[0] = self._row(-5, diagnostics={'method_score': 100.0})
        report = self._build(self._sweep(rows=rows))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('does not match total absolute flux', ' '.join(report['current_issues']))

    def test_invalid_later_sweep_preserves_valid_evidence(self):
        valid = self._build()
        invalid = self._build(self._sweep(method='FBA'), existing=valid)
        self.assertFalse(invalid['current_sweep_recorded'])
        self.assertTrue(invalid['evidence_ready'])
        self.assertTrue(invalid['ready_to_deliver'])
        text = simulation.build_mission23_nutrient_sensitivity_report_text(invalid)
        self.assertIn('Latest sweep was not recorded', text)
        self.assertIn('Previously valid Mission 23 evidence remains available', text)
        self.assertIn('Evidence complete', text)

    def test_explicit_empty_sweep_does_not_load_old_bound_sweep(self):
        with patch.object(simulation, 'load_bound_sweep', side_effect=AssertionError('must not load')):
            with patch.object(simulation, 'load_mission23_comparison_check', return_value={}):
                with patch.object(simulation, 'save_mission23_comparison_check'):
                    report = simulation.run_mission23_sensitivity_check({})
        self.assertFalse(report['evidence_ready'])

    def test_answer_aliases_are_accepted(self):
        report = self._build()
        for answer in ('acetate', 'acetato', 'EX_ac_e', 'acetate exchange'):
            with self.subTest(answer=answer):
                self.assertTrue(simulation.mission23_answer_matches(answer, report))

    def test_wrong_or_additional_candidate_is_rejected(self):
        report = self._build()
        for answer in ('CO2', 'EX_co2_e', 'acetate and CO2', 'ammonium', 'oxygen', 'both'):
            with self.subTest(answer=answer):
                self.assertFalse(simulation.mission23_answer_matches(answer, report))

    def test_report_shows_evidence_without_declaring_the_answer(self):
        text = simulation.build_mission23_nutrient_sensitivity_report_text(self._build())
        self.assertIn('Sweep points recorded: 4/4', text)
        self.assertIn('Evidence complete', text)
        self.assertNotIn('Acetate is the answer', text)
        self.assertNotIn('Expected new secretion', text)

    def test_state_is_json_serialisable(self):
        json.dumps(self._build())

    def test_opening_report_is_informative_without_repeating_menu_title(self):
        text = simulation.build_mission23_nutrient_sensitivity_report_text({})
        self.assertNotIn('Mission 23 Nutrient Sensitivity Curve', text)
        self.assertIn('controlled four-point sensitivity experiment', text)
        self.assertIn('varying only ammonium uptake capacity', text)
        self.assertIn('pFBA diagnostics', text)

    def test_default_bound_toggles_use_native_python_booleans(self):
        reactions = simulation._build_default_reactions_data()
        self.assertTrue(reactions)
        self.assertTrue(all(type(value) is bool for value in reactions.values()))
        json.dumps(reactions)

    def test_validator_and_remote_wrapper_launch_no_solver_or_http_request(self):
        source = inspect.getsource(simulation.run_mission23_sensitivity_check)
        source += inspect.getsource(simulation._build_mission23_data)
        source += inspect.getsource(simulation.run_mission23_sensitivity_check_remote)
        self.assertNotIn('simul.simulate', source)
        self.assertNotIn('_http_post_json', source)
        self.assertNotIn('run_bound_sweep(', source)

    def test_remote_bound_sweep_reuses_existing_simulate_contract_four_times(self):
        responses = []
        for value in self.VALUES:
            data = self.EXPECTED[value]
            fluxes = {
                simulation.MISSION23_GROWTH_OBJECTIVE: data['growth'],
                'EX_nh4_e': data['nh4'],
                'EX_glc__D_e': data['glucose'],
                'EX_o2_e': data['oxygen'],
                'EX_pi_e': data['phosphate'],
                'EX_ac_e': data['acetate'],
                'EX_co2_e': data['co2'],
            }
            responses.append({
                'status': 'ok',
                'method': 'pFBA',
                'objective': simulation.MISSION23_GROWTH_OBJECTIVE,
                'objective_reaction': simulation.MISSION23_GROWTH_OBJECTIVE,
                'primary_objective_flux': data['growth'],
                'method_score': data['total'],
                'method_score_name': 'total_absolute_flux',
                'total_absolute_flux': data['total'],
                'active_reaction_count': data['active'],
                'fluxes': fluxes,
            })
        with patch.object(simulation, '_read_simulation_file', return_value=(
            'pFBA', simulation.MISSION23_GROWTH_OBJECTIVE,
            simulation._build_active_genes_data(), simulation._build_default_reactions_data(),
        )):
            with patch.object(simulation, '_read_selected_production_fluxes', return_value=['EX_ac_e', 'EX_co2_e']):
                with patch.object(simulation, '_build_request_payload', return_value={
                    'method': 'pFBA', 'objective': simulation.MISSION23_GROWTH_OBJECTIVE,
                    'gene_knockouts': [], 'env_conditions': simulation._build_default_env_conditions_payload(),
                }):
                    with patch.object(simulation, '_http_post_json', side_effect=responses) as post:
                        with patch.object(simulation, 'save_bound_sweep'):
                            data = simulation.run_bound_sweep_remote('/api', {
                                'sweep_variable': [[('NH4', 'EX_nh4_e:lower')]],
                                'sweep_values': [[('NH4 values', 'ammonium_sensitivity')]],
                            })
        self.assertEqual(post.call_count, 4)
        self.assertEqual(len(data['rows']), 4)
        self.assertTrue(all(row['status'] == 'ok' for row in data['rows']))

    def test_window_integrates_local_and_browser_sweeps(self):
        source = (CODE_DIR / 'window.py').read_text()
        self.assertIn("('Ammonium lower bound (EX_nh4_e)', 'EX_nh4_e:lower')", source)
        self.assertIn("('Ammonium sensitivity: -5, -4, -2, -1', 'ammonium_sensitivity')", source)
        self.assertIn('run_bound_sweep_remote(', source)
        self.assertIn('run_mission23_sensitivity_check_remote(', source)
        self.assertIn('return build_mission23_nutrient_sensitivity_report_text(report_data)', source)

    def test_mission_ui_has_gating_idempotence_and_direct_answer_guards(self):
        source = (CODE_DIR / 'mission23.py').read_text()
        self.assertIn('is_mission23_unlocked', source)
        self.assertIn("if '23' in self.missions_activated", source)
        self.assertIn('initialise_mission23_nutrient_sensitivity_curve', source)
        self.assertIn('normalise_mission23_answer', source)
        self.assertIn('mission23_answer_matches', source)
        self.assertIn('Dr. Luna', source)
        self.assertNotIn('Deliver Objective Comparison', source)

    def test_old_objective_comparison_recipe_is_removed(self):
        source = inspect.getsource(simulation._build_mission23_data)
        source += (CODE_DIR / 'mission23.py').read_text()
        self.assertNotIn('MISSION23_TARGET_OBJECTIVE', source)
        self.assertNotIn('MISSION23_MIN_PRODUCTION_INCREASE', source)
        self.assertNotIn('growth objective vs ethanol objective', source.lower())

    def test_independent_pfba_values_for_four_ammonium_points(self):
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

        biomass_index = reaction_index['R_BIOMASS_Ecoli_core_w_GAM']
        nh4_index = reaction_index['R_EX_nh4_e']
        count = len(reactions)

        def solve(bound_value):
            current_bounds = list(bounds)
            current_bounds[nh4_index] = (bound_value, current_bounds[nh4_index][1])
            objective = np.zeros(count)
            objective[biomass_index] = -1.0
            primary = linprog(objective, A_eq=matrix, b_eq=np.zeros(len(species)), bounds=current_bounds, method='highs')
            self.assertTrue(primary.success)
            optimum = primary.x[biomass_index]

            pfba_objective = np.concatenate([np.zeros(count), np.ones(count)])
            equality = np.hstack([matrix, np.zeros((matrix.shape[0], count))])
            biomass_equality = np.zeros((1, count * 2))
            biomass_equality[0, biomass_index] = 1.0
            equality = np.vstack([equality, biomass_equality])
            equality_rhs = np.concatenate([np.zeros(len(species)), [optimum]])
            inequalities = np.vstack([
                np.hstack([np.eye(count), -np.eye(count)]),
                np.hstack([-np.eye(count), -np.eye(count)]),
            ])
            pfba = linprog(
                pfba_objective,
                A_ub=inequalities,
                b_ub=np.zeros(count * 2),
                A_eq=equality,
                b_eq=equality_rhs,
                bounds=current_bounds + [(0.0, None)] * count,
                method='highs',
            )
            self.assertTrue(pfba.success)
            fluxes = pfba.x[:count]
            return fluxes, float(sum(abs(float(v)) for v in fluxes)), sum(abs(float(v)) > 1e-7 for v in fluxes)

        flux_ids = {
            'growth': 'R_BIOMASS_Ecoli_core_w_GAM',
            'nh4': 'R_EX_nh4_e',
            'glucose': 'R_EX_glc__D_e',
            'oxygen': 'R_EX_o2_e',
            'acetate': 'R_EX_ac_e',
            'co2': 'R_EX_co2_e',
        }
        for value in self.VALUES:
            with self.subTest(bound=value):
                fluxes, total, active = solve(value)
                expected = self.EXPECTED[value]
                for key, reaction_id in flux_ids.items():
                    self.assertAlmostEqual(fluxes[reaction_index[reaction_id]], expected[key], delta=1e-5)
                self.assertAlmostEqual(total, expected['total'], delta=1e-3)
                self.assertEqual(active, expected['active'])

    def test_backend_pfba_sweep_contract_when_dependencies_exist(self):
        backend_dir = PROJECT_ROOT / 'backend'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        try:
            from app.schemas import SimulateRequest
            from app.simulator import simulate as backend_simulate
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'Backend MEWpy/COBRApy unavailable: {exc}')

        default_env = simulation._build_default_env_conditions_payload()
        for value in self.VALUES:
            env = {key: list(bounds) for key, bounds in default_env.items()}
            env['EX_nh4_e'][0] = value
            response = backend_simulate(SimulateRequest(
                method='pFBA',
                objective=simulation.MISSION23_GROWTH_OBJECTIVE,
                gene_knockouts=[],
                env_conditions=env,
            ))
            self.assertEqual(response.status, 'ok', response.message)
            expected = self.EXPECTED[value]
            self.assertAlmostEqual(float(response.primary_objective_flux), expected['growth'], delta=1e-3)
            self.assertEqual(response.method_score_name, 'total_absolute_flux')
            self.assertAlmostEqual(float(response.total_absolute_flux), expected['total'], delta=1e-2)
            self.assertEqual(int(response.active_reaction_count), expected['active'])
            self.assertAlmostEqual(float(response.fluxes['EX_ac_e']), expected['acetate'], delta=1e-3)
            self.assertAlmostEqual(float(response.fluxes['EX_co2_e']), expected['co2'], delta=1e-3)


if __name__ == '__main__':
    unittest.main()
