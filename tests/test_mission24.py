"""Regression tests for Mission 24 export-capacity thresholds.

Run from the project root with:
    python3 tests/test_mission24.py
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


class Mission24RegressionTests(unittest.TestCase):
    VALUES = [25.0, 20.0, 10.0, 0.0]
    EXPECTED = {
        25.0: {
            'growth': 0.873921507,
            'glucose': -10.0,
            'oxygen': -21.799493,
            'co2': 22.809833,
            'formate': 0.0,
            'acetate': 0.0,
            'total': 518.422086,
            'active': 48,
        },
        20.0: {
            'growth': 0.842120354,
            'glucose': -10.0,
            'oxygen': -21.107998,
            'co2': 20.0,
            'formate': 4.163147,
            'acetate': 0.0,
            'total': 516.338131,
            'active': 51,
        },
        10.0: {
            'growth': 0.681851508,
            'glucose': -10.0,
            'oxygen': -15.868330,
            'co2': 10.0,
            'formate': 13.313238,
            'acetate': 3.835115,
            'total': 463.432427,
            'active': 55,
        },
        0.0: {
            'growth': 0.461669614,
            'glucose': -10.0,
            'oxygen': -7.484524,
            'co2': 0.0,
            'formate': 16.036520,
            'acetate': 12.158449,
            'total': 370.683878,
            'active': 50,
        },
    }

    def _row(self, value, *, missing_medium=None, missing_tracked=None,
             missing_raw_co2=False, diagnostics=None, status='ok'):
        data = self.EXPECTED[float(value)]
        raw = {
            'EX_glc__D_e': data['glucose'],
            'EX_o2_e': data['oxygen'],
            'EX_co2_e': data['co2'],
        }
        tracked = {
            'EX_co2_e': data['co2'],
            'EX_for_e': data['formate'],
            'EX_ac_e': data['acetate'],
        }
        raw.pop(missing_medium, None)
        tracked.pop(missing_tracked, None)
        if missing_raw_co2:
            raw.pop('EX_co2_e', None)
        diag = {
            'method': simulation.MISSION24_METHOD,
            'objective_reaction': simulation.MISSION24_GROWTH_OBJECTIVE,
            'primary_objective_flux': data['growth'],
            'method_score': data['total'],
            'method_score_name': simulation.MISSION24_EXPECTED_SECONDARY_CRITERION,
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

    def _sweep(self, *, rows=None, method=None, objective=None, genes=None,
               reactions=None, reaction_id=None, bound=None, values=None,
               selected=None, error=None):
        data = {
            'sweep_id': 'bound_sweep',
            'check_version': 3,
            'method': method or simulation.MISSION24_METHOD,
            'objective': objective or simulation.MISSION24_GROWTH_OBJECTIVE,
            'knocked_out_genes': list(genes or []),
            'environment_changed': False,
            'base_genes': simulation._build_active_genes_data(),
            'base_reactions': reactions or simulation._build_default_reactions_data(),
            'variable': 'EX_co2_e:upper',
            'preset': 'co2_export_capacity',
            'reaction_id': reaction_id or simulation.MISSION24_SWEEP_REACTION,
            'reaction_name': simulation.MISSION24_SWEEP_REACTION_NAME,
            'bound': bound or simulation.MISSION24_SWEEP_BOUND,
            'bound_label': simulation.MISSION24_SWEEP_BOUND_LABEL,
            'values': list(self.VALUES if values is None else values),
            'tracked_fluxes': list(selected or simulation.MISSION24_REQUIRED_TRACKED_FLUXES),
            'selected_production_fluxes': list(selected or simulation.MISSION24_REQUIRED_TRACKED_FLUXES),
            'rows': rows if rows is not None else [self._row(value) for value in self.VALUES],
        }
        if error:
            data['error'] = error
        return data

    def _build(self, sweep=None, existing=None):
        with patch.object(simulation, 'save_mission24_comparison_check'):
            return simulation._build_mission24_data(
                self._sweep() if sweep is None else sweep,
                {} if existing is None else existing,
            )

    def test_constants_define_new_upper_bound_sweep(self):
        self.assertEqual(simulation.MISSION24_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION24_METHOD, 'pFBA')
        self.assertEqual(simulation.MISSION24_SWEEP_REACTION, 'EX_co2_e')
        self.assertEqual(simulation.MISSION24_SWEEP_BOUND, 'upper')
        self.assertEqual(simulation.MISSION24_SWEEP_VALUES, self.VALUES)
        self.assertEqual(
            simulation.MISSION24_REQUIRED_TRACKED_FLUXES,
            ['EX_co2_e', 'EX_for_e', 'EX_ac_e'],
        )

    def test_sweep_menu_preserves_mismatched_recognised_preset_values(self):
        menu_data = {
            'sweep_variable': [[('CO2 upper bound (EX_co2_e)', 'EX_co2_e:upper')]],
            'sweep_values': [[('Ammonium sensitivity', 'ammonium_sensitivity')]],
        }
        config = simulation._normalise_sweep_config(menu_data)
        self.assertEqual(config['reaction_id'], 'EX_co2_e')
        self.assertEqual(config['preset'], 'ammonium_sensitivity')
        self.assertEqual(config['expected_preset'], 'co2_export_capacity')
        self.assertFalse(config['preset_matches_variable'])
        self.assertEqual(config['values'], simulation.MISSION23_SWEEP_VALUES)

        valid = self._build()
        invalid_sweep = self._sweep(values=config['values'], rows=[])
        invalid_sweep.update({
            'variable': config['variable'],
            'preset': config['preset'],
            'expected_preset': config['expected_preset'],
            'preset_matches_variable': config['preset_matches_variable'],
        })
        invalid = self._build(invalid_sweep, existing=valid)
        self.assertFalse(invalid['current_sweep_recorded'])
        self.assertTrue(invalid['evidence_ready'])
        self.assertIn('four required CO2', ' '.join(invalid['current_issues']))

    def test_valid_sweep_records_complete_relationship(self):
        report = self._build()
        self.assertTrue(report['current_sweep_valid'])
        self.assertTrue(report['current_sweep_recorded'])
        self.assertEqual(report['recorded_point_count'], 4)
        self.assertTrue(report['all_points_recorded'])
        self.assertTrue(report['growth_trend'])
        self.assertTrue(report['oxygen_uptake_trend'])
        self.assertTrue(report['co2_export_trend'])
        self.assertTrue(report['formate_onset'])
        self.assertTrue(report['acetate_onset'])
        self.assertEqual(report['first_compensatory_candidates'], ['EX_for_e'])
        self.assertTrue(report['relationship_supported'])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['ready_to_deliver'])

    def test_rows_can_arrive_in_any_order(self):
        report = self._build(self._sweep(rows=[self._row(v) for v in reversed(self.VALUES)]))
        self.assertTrue(report['evidence_ready'])
        self.assertEqual([row['bound_value'] for row in report['sweep_rows']], self.VALUES)

    def test_repeated_sweep_replaces_points_without_duplication(self):
        first = self._build()
        second = self._build(self._sweep(), existing=first)
        self.assertEqual(second['recorded_point_count'], 4)
        self.assertEqual(len(second['sweep_rows']), 4)

    def test_wrong_method_objective_or_gene_is_rejected(self):
        cases = [
            self._sweep(method='FBA'),
            self._sweep(objective='EX_co2_e'),
            self._sweep(genes=['b0728']),
        ]
        for sweep in cases:
            with self.subTest(sweep=sweep.get('method')):
                self.assertFalse(self._build(sweep)['current_sweep_valid'])

    def test_base_environment_is_key_order_independent(self):
        defaults = simulation._build_default_reactions_data()
        reordered = dict(reversed(list(defaults.items())))
        self.assertTrue(self._build(self._sweep(reactions=reordered))['current_sweep_valid'])

    def test_explicit_incomplete_environment_is_rejected(self):
        defaults = simulation._build_default_reactions_data()
        defaults.pop(next(iter(defaults)))
        report = self._build(self._sweep(reactions=defaults))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('payload is incomplete', ' '.join(report['current_issues']))

    def test_wrong_variable_bound_or_values_is_rejected(self):
        cases = [
            self._sweep(reaction_id='EX_nh4_e'),
            self._sweep(bound='lower'),
            self._sweep(values=[25.0, 20.0, 10.0]),
        ]
        for sweep in cases:
            with self.subTest(reaction=sweep.get('reaction_id'), bound=sweep.get('bound')):
                self.assertFalse(self._build(sweep)['current_sweep_valid'])

    def test_full_selected_panel_is_required(self):
        report = self._build(self._sweep(selected=['EX_co2_e', 'EX_for_e']))
        self.assertFalse(report['current_sweep_valid'])
        self.assertIn('Select EX_co2_e', ' '.join(report['current_issues']))

    def test_missing_or_infeasible_row_is_rejected(self):
        missing = self._build(self._sweep(rows=[self._row(v) for v in self.VALUES[:-1]]))
        self.assertFalse(missing['current_sweep_valid'])
        rows = [self._row(v) for v in self.VALUES]
        rows[2] = self._row(10.0, status='infeasible')
        infeasible = self._build(self._sweep(rows=rows))
        self.assertFalse(infeasible['current_sweep_valid'])
        self.assertIn('did not return an optimal measurable result', ' '.join(infeasible['current_issues']))

    def test_missing_exchange_or_production_value_is_rejected(self):
        rows = [self._row(v) for v in self.VALUES]
        rows[1] = self._row(20.0, missing_medium='EX_o2_e')
        self.assertIn('Exchange Flux evidence is incomplete', ' '.join(self._build(self._sweep(rows=rows))['current_issues']))
        rows = [self._row(v) for v in self.VALUES]
        rows[1] = self._row(20.0, missing_tracked='EX_for_e')
        self.assertIn('Production Flux evidence is incomplete', ' '.join(self._build(self._sweep(rows=rows))['current_issues']))

    def test_signed_co2_flux_is_required_and_must_match_tracked_value(self):
        rows = [self._row(v) for v in self.VALUES]
        rows[0] = self._row(25.0, missing_raw_co2=True)
        report = self._build(self._sweep(rows=rows))
        self.assertIn('signed CO2 exchange flux is missing', ' '.join(report['current_issues']))

        rows = [self._row(v) for v in self.VALUES]
        rows[0]['exchange_raw_fluxes']['EX_co2_e'] = 10.0
        report = self._build(self._sweep(rows=rows))
        self.assertIn('does not match the signed exchange flux', ' '.join(report['current_issues']))

    def test_co2_export_cannot_exceed_configured_cap(self):
        rows = [self._row(v) for v in self.VALUES]
        rows[1]['tracked_flux_values']['EX_co2_e'] = 20.5
        rows[1]['exchange_raw_fluxes']['EX_co2_e'] = 20.5
        report = self._build(self._sweep(rows=rows))
        self.assertIn('exceeds its configured upper bound', ' '.join(report['current_issues']))

    def test_pfba_diagnostics_are_mandatory(self):
        rows = [self._row(v) for v in self.VALUES]
        rows[0] = self._row(25.0, diagnostics={'method_score_name': 'primary_objective_flux'})
        report = self._build(self._sweep(rows=rows))
        self.assertIn('secondary criterion is missing', ' '.join(report['current_issues']))

        rows = [self._row(v) for v in self.VALUES]
        rows[0] = self._row(25.0, diagnostics={'primary_objective_flux': 0.2})
        report = self._build(self._sweep(rows=rows))
        self.assertIn('does not match biomass', ' '.join(report['current_issues']))

        rows = [self._row(v) for v in self.VALUES]
        rows[0] = self._row(25.0, diagnostics={'method_score': 100.0})
        report = self._build(self._sweep(rows=rows))
        self.assertIn('does not match total absolute flux', ' '.join(report['current_issues']))

    def test_relationship_requires_formate_before_acetate(self):
        rows = [self._row(v) for v in self.VALUES]
        rows[1]['tracked_flux_values']['EX_ac_e'] = 1.0
        rows[1]['exchange_raw_fluxes']['EX_co2_e'] = 20.0
        report = self._build(self._sweep(rows=rows))
        self.assertFalse(report['relationship_supported'])

    def test_invalid_later_sweep_preserves_valid_evidence(self):
        valid = self._build()
        invalid = self._build(self._sweep(method='FBA'), existing=valid)
        self.assertFalse(invalid['current_sweep_recorded'])
        self.assertTrue(invalid['evidence_ready'])
        self.assertTrue(invalid['ready_to_deliver'])
        text = simulation.build_mission24_export_capacity_report_text(invalid)
        self.assertIn('Latest sweep was not recorded', text)
        self.assertIn('Previously valid Mission 24 evidence remains available', text)
        self.assertIn('Evidence complete', text)

    def test_explicit_empty_sweep_does_not_load_old_bound_sweep(self):
        with patch.object(simulation, 'load_bound_sweep', side_effect=AssertionError('must not load')):
            with patch.object(simulation, 'load_mission24_comparison_check', return_value={}):
                with patch.object(simulation, 'save_mission24_comparison_check'):
                    report = simulation.run_mission24_export_capacity_check({})
        self.assertFalse(report['evidence_ready'])

    def test_answer_aliases_are_accepted(self):
        report = self._build()
        for answer in ('formate', 'formato', 'EX_for_e', 'formate exchange'):
            with self.subTest(answer=answer):
                self.assertTrue(simulation.mission24_answer_matches(answer, report))

    def test_wrong_or_multiple_answers_are_rejected(self):
        report = self._build()
        for answer in ('acetate', 'CO2', 'formate and acetate', 'both', 'ethanol', 'all routes'):
            with self.subTest(answer=answer):
                self.assertFalse(simulation.mission24_answer_matches(answer, report))

    def test_report_exposes_evidence_without_declaring_answer(self):
        text = simulation.build_mission24_export_capacity_report_text(self._build())
        self.assertIn('Sweep points recorded: 4/4', text)
        self.assertIn('Evidence complete', text)
        self.assertIn('20 | 0.842', text)
        self.assertNotIn('Formate is the answer', text)
        self.assertNotIn('Expected first compensatory', text)

    def test_state_is_json_serialisable(self):
        json.dumps(self._build())

    def test_opening_report_is_informative_without_repeating_menu_title(self):
        text = simulation.build_mission24_export_capacity_report_text({})
        self.assertNotIn('Mission 24 Export Capacity Thresholds', text)
        self.assertIn('controlled four-point export-capacity experiment', text)
        self.assertIn('progressively restricting only CO2 export', text)
        self.assertIn('pFBA diagnostics', text)

    def test_default_bound_toggles_use_native_python_booleans(self):
        reactions = simulation._build_default_reactions_data()
        self.assertTrue(reactions)
        self.assertTrue(all(type(value) is bool for value in reactions.values()))
        json.dumps(reactions)

    def test_validator_and_wrapper_launch_no_solver_or_http_request(self):
        source = inspect.getsource(simulation.run_mission24_export_capacity_check)
        source += inspect.getsource(simulation._build_mission24_data)
        source += inspect.getsource(simulation.run_mission24_export_capacity_check_remote)
        self.assertNotIn('simul.simulate', source)
        self.assertNotIn('_http_post_json', source)
        self.assertNotIn('run_bound_sweep(', source)

    def test_remote_sweep_reuses_simulate_contract_four_times_with_upper_bounds(self):
        responses = []
        for value in self.VALUES:
            data = self.EXPECTED[value]
            fluxes = {
                simulation.MISSION24_GROWTH_OBJECTIVE: data['growth'],
                'EX_glc__D_e': data['glucose'],
                'EX_o2_e': data['oxygen'],
                'EX_co2_e': data['co2'],
                'EX_for_e': data['formate'],
                'EX_ac_e': data['acetate'],
            }
            responses.append({
                'status': 'ok',
                'method': 'pFBA',
                'objective': simulation.MISSION24_GROWTH_OBJECTIVE,
                'objective_reaction': simulation.MISSION24_GROWTH_OBJECTIVE,
                'primary_objective_flux': data['growth'],
                'method_score': data['total'],
                'method_score_name': 'total_absolute_flux',
                'total_absolute_flux': data['total'],
                'active_reaction_count': data['active'],
                'fluxes': fluxes,
            })
        with patch.object(simulation, '_read_simulation_file', return_value=(
            'pFBA', simulation.MISSION24_GROWTH_OBJECTIVE,
            simulation._build_active_genes_data(), simulation._build_default_reactions_data(),
        )):
            with patch.object(simulation, '_read_selected_production_fluxes', return_value=['EX_co2_e', 'EX_for_e', 'EX_ac_e']):
                with patch.object(simulation, '_build_request_payload', return_value={
                    'method': 'pFBA', 'objective': simulation.MISSION24_GROWTH_OBJECTIVE,
                    'gene_knockouts': [], 'env_conditions': simulation._build_default_env_conditions_payload(),
                }):
                    with patch.object(simulation, '_http_post_json', side_effect=responses) as post:
                        with patch.object(simulation, 'save_bound_sweep'):
                            data = simulation.run_bound_sweep_remote('/api', {
                                'sweep_variable': [[('CO2', 'EX_co2_e:upper')]],
                                'sweep_values': [[('CO2 values', 'co2_export_capacity')]],
                            })
        self.assertEqual(post.call_count, 4)
        self.assertEqual(len(data['rows']), 4)
        for call, value in zip(post.call_args_list, self.VALUES):
            payload = call.args[1]
            self.assertEqual(float(payload['env_conditions']['EX_co2_e'][1]), value)

    def test_window_integrates_local_and_browser_sweep(self):
        source = (CODE_DIR / 'window.py').read_text()
        self.assertIn("('Carbon dioxide upper bound (EX_co2_e)', 'EX_co2_e:upper')", source)
        self.assertIn("('CO2 export capacity: 25, 20, 10, 0', 'co2_export_capacity')", source)
        self.assertIn('run_mission24_export_capacity_check_remote(', source)
        self.assertIn('run_mission24_export_capacity_check(bound_sweep_data)', source)
        self.assertIn('return build_mission24_export_capacity_report_text(report_data)', source)

    def test_mission_ui_has_gating_idempotence_and_answer_guards(self):
        source = (CODE_DIR / 'mission24.py').read_text()
        self.assertIn('is_mission24_unlocked', source)
        self.assertIn("if '24' in self.missions_activated", source)
        self.assertIn('initialise_mission24_export_capacity_thresholds', source)
        self.assertIn('normalise_mission24_answer', source)
        self.assertIn('mission24_answer_matches', source)
        self.assertIn('Dr. Luna', source)
        self.assertNotIn('Deliver Method Comparison', source)
        self.assertNotIn('Dr. Vega', source)

    def test_old_method_comparison_recipe_is_removed(self):
        source = inspect.getsource(simulation._build_mission24_data)
        source += (CODE_DIR / 'mission24.py').read_text()
        self.assertNotIn('MISSION24_BASELINE_METHOD', source)
        self.assertNotIn('MISSION24_TARGET_METHOD', source)
        self.assertNotIn('FBA vs pFBA', source)
        self.assertNotIn('Compare Runs', source)

    def test_mission25_is_wired_as_dr_smith_interaction(self):
        level = (CODE_DIR / 'level.py').read_text()
        player = (CODE_DIR / 'player.py').read_text()
        mission25 = (CODE_DIR / 'mission25.py').read_text()
        self.assertIn('from mission25 import Mission25', level)
        self.assertIn("obj.name == 'Mission25'", level)
        self.assertIn('talk_25 = self.toggle_talk_25', level)
        self.assertIn("name == 'Mission25'", player)
        self.assertIn('self.talk_25()', player)
        self.assertIn("graphics/dialogues/smith.jpg", mission25)
        self.assertIn('Dr. Smith', mission25)

    def test_documentation_assigns_mission_to_luna(self):
        documentation = (PROJECT_ROOT / 'data' / 'missions' / 'mission24.md').read_text()
        self.assertIn('Dr. Luna', documentation)
        self.assertNotIn('Dr. Vega', documentation)
        self.assertIn('EX_co2_e', documentation)
        self.assertIn('EX_for_e', documentation)

    def test_independent_pfba_values_for_four_co2_caps(self):
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
        co2_index = reaction_index['R_EX_co2_e']
        count = len(reactions)

        def solve(bound_value):
            current_bounds = list(bounds)
            current_bounds[co2_index] = (current_bounds[co2_index][0], bound_value)
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
            'glucose': 'R_EX_glc__D_e',
            'oxygen': 'R_EX_o2_e',
            'co2': 'R_EX_co2_e',
            'formate': 'R_EX_for_e',
            'acetate': 'R_EX_ac_e',
        }
        for value in self.VALUES:
            with self.subTest(bound=value):
                fluxes, total, active = solve(value)
                expected = self.EXPECTED[value]
                for key, reaction_id in flux_ids.items():
                    self.assertAlmostEqual(fluxes[reaction_index[reaction_id]], expected[key], delta=1e-5)
                self.assertAlmostEqual(total, expected['total'], delta=1e-3)
                self.assertEqual(active, expected['active'])

    def test_backend_pfba_contract_when_dependencies_exist(self):
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
            env['EX_co2_e'][1] = value
            response = backend_simulate(SimulateRequest(
                method='pFBA',
                objective=simulation.MISSION24_GROWTH_OBJECTIVE,
                gene_knockouts=[],
                env_conditions=env,
            ))
            self.assertEqual(response.status, 'ok', response.message)
            expected = self.EXPECTED[value]
            self.assertAlmostEqual(float(response.primary_objective_flux), expected['growth'], delta=1e-3)
            self.assertEqual(response.method_score_name, 'total_absolute_flux')
            self.assertAlmostEqual(float(response.total_absolute_flux), expected['total'], delta=1e-2)
            self.assertEqual(int(response.active_reaction_count), expected['active'])
            self.assertAlmostEqual(float(response.fluxes['EX_co2_e']), expected['co2'], delta=1e-3)
            self.assertAlmostEqual(float(response.fluxes['EX_for_e']), expected['formate'], delta=1e-3)
            self.assertAlmostEqual(float(response.fluxes['EX_ac_e']), expected['acetate'], delta=1e-3)


if __name__ == '__main__':
    unittest.main()
