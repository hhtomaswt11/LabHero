"""Regression tests for Mission 21 compensatory flux comparison.

Run from the project root with:
    python3 tests/test_mission21.py
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


class Mission21RegressionTests(unittest.TestCase):
    BASELINE_GROWTH = 0.211662950
    MODIFIED_GROWTH = 0.137904780
    BASELINE_PROFILE = {
        'EX_ac_e': 8.503585,
        'EX_etoh_e': 8.279455,
        'EX_for_e': 17.804674,
        'EX_succ_e': 0.0,
        'EX_lac__D_e': 0.0,
    }
    MODIFIED_PROFILE = {
        'EX_ac_e': 0.146027,
        'EX_etoh_e': 0.0,
        'EX_for_e': 0.811652,
        'EX_succ_e': 0.0,
        'EX_lac__D_e': 17.758027,
    }

    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.panel = list(simulation.MISSION21_REQUIRED_TRACKED_FLUXES)

    def _reactions(self, ethanol_closed=False):
        reactions = simulation._build_default_reactions_data()
        oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION21_OXYGEN_REACTION)
        reactions[f'reaction_{oxygen_index}_lb'] = False
        if ethanol_closed:
            ethanol_index = list(simulation.REACTIONS.index).index(simulation.MISSION21_ETHANOL_EXPORT)
            reactions[f'reaction_{ethanol_index}_ub'] = False
        return reactions

    def _values(self, ethanol_closed=False):
        if ethanol_closed:
            return self.MODIFIED_GROWTH, dict(self.MODIFIED_PROFILE)
        return self.BASELINE_GROWTH, dict(self.BASELINE_PROFILE)

    def _medium(self, ethanol_closed=False, missing=None, override=None):
        missing = set(missing or [])
        growth, profile = self._values(ethanol_closed)
        raw = {
            simulation.MISSION21_GLUCOSE_REACTION: -10.0,
            simulation.MISSION21_OXYGEN_REACTION: 0.0,
            **profile,
        }
        if override:
            raw.update(override)
        return {
            'items': [
                {
                    'reaction_id': reaction_id,
                    'raw_flux': float(value),
                    'uptake_flux': max(-float(value), 0.0),
                    'secretion_flux': max(float(value), 0.0),
                }
                for reaction_id, value in raw.items()
                if reaction_id not in missing
            ]
        }

    def _production(
        self,
        ethanol_closed=False,
        missing=None,
        profile_override=None,
        diagnostics_override=None,
        biomass=None,
    ):
        missing = set(missing or [])
        growth, profile = self._values(ethanol_closed)
        if profile_override:
            profile.update(profile_override)
        diagnostics = {
            'method': simulation.MISSION21_METHOD,
            'objective_reaction': simulation.MISSION21_GROWTH_OBJECTIVE,
            'primary_objective_flux': growth,
            'method_score': growth,
            'method_score_name': 'primary_objective_flux',
            'total_absolute_flux': 300.0 if ethanol_closed else 340.0,
            'active_reaction_count': 42 if ethanol_closed else 47,
        }
        if diagnostics_override:
            diagnostics.update(diagnostics_override)
        return {
            'selected_ids': list(self.panel),
            'items': [
                {
                    'reaction_id': reaction_id,
                    'production_flux': float(profile[reaction_id]),
                }
                for reaction_id in self.panel
                if reaction_id not in missing
            ],
            'biomass_raw': growth if biomass is None else biomass,
            'method_diagnostics': diagnostics,
        }

    def _record(
        self,
        ethanol_closed=False,
        report=None,
        method=None,
        objective=None,
        genes=None,
        reactions=None,
        result=None,
        medium=None,
        production=None,
        selected=None,
        error=None,
    ):
        growth, profile = self._values(ethanol_closed)
        method = method or simulation.MISSION21_METHOD
        objective = objective or simulation.MISSION21_GROWTH_OBJECTIVE
        if result is None:
            result = growth
        if medium is None:
            medium = self._medium(ethanol_closed)
        if production is None:
            diagnostics_override = {
                'method': method,
                'objective_reaction': objective,
                'method_score_name': 'primary_objective_flux' if method == 'FBA' else 'total_absolute_flux',
            }
            production = self._production(
                ethanol_closed,
                diagnostics_override=diagnostics_override,
            )
        if reactions is None:
            reactions = self._reactions(ethanol_closed)
        with patch.object(simulation, 'save_mission21_comparison_check'):
            return simulation._build_mission21_data(
                method,
                objective,
                result,
                dict(genes or self.genes),
                dict(reactions),
                production_fluxes=production,
                medium_fluxes=medium,
                existing_report=report,
                selected_fluxes=list(self.panel if selected is None else selected),
                objective_error=error,
            )

    def _complete(self, order=None):
        report = None
        for ethanol_closed in (order or [False, True]):
            report = self._record(ethanol_closed, report=report)
        return report

    def test_progression_and_redesign_constants(self):
        self.assertFalse(simulation.is_mission21_unlocked([]))
        self.assertFalse(simulation.is_mission21_unlocked(['19']))
        self.assertTrue(simulation.is_mission21_unlocked(['20']))
        self.assertEqual(simulation.MISSION21_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION21_METHOD, 'FBA')
        self.assertEqual(simulation.MISSION21_ETHANOL_EXPORT, 'EX_etoh_e')
        self.assertEqual(simulation.MISSION21_EXPECTED_LARGEST_INCREASE, 'EX_lac__D_e')
        self.assertFalse(hasattr(simulation, 'MISSION21_MIN_GROWTH_DROP'))

    def test_initial_state_is_json_serialisable(self):
        with patch.object(simulation, 'save_mission21_comparison_check'):
            report = simulation.initialise_mission21_compensatory_comparison()
        self.assertEqual(report['recorded_run_count'], 0)
        self.assertEqual(report['missing_run_types'], ['baseline', 'ethanol_closed'])
        self.assertFalse(report['evidence_ready'])
        json.dumps(report)

    def test_environment_reader_is_order_independent_and_legacy_compatible(self):
        reactions = self._reactions(True)
        expected = simulation._mission21_environment_status(reactions)
        self.assertTrue(expected['bounds_complete'])
        self.assertTrue(expected['oxygen_lower_bound_closed'])
        self.assertTrue(expected['ethanol_upper_bound_closed'])
        self.assertEqual(expected['run_type'], 'ethanol_closed')
        self.assertEqual(simulation._mission21_environment_status(dict(reversed(list(reactions.items())))), expected)
        legacy = {f'widget_{index}': value for index, value in enumerate(reactions.values())}
        self.assertEqual(simulation._mission21_environment_status(legacy)['run_type'], 'ethanol_closed')

    def test_incomplete_explicit_bound_payload_is_rejected(self):
        reactions = self._reactions()
        reactions.pop('reaction_0_ub')
        report = self._record(reactions=reactions)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('environmental-bound payload is incomplete', ' '.join(report['current_issues']))

    def test_baseline_records_visible_values(self):
        report = self._record(False)
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertTrue(report['current_run_recorded'])
        self.assertEqual(report['current_run_type'], 'baseline')
        self.assertAlmostEqual(report['baseline_run']['growth'], self.BASELINE_GROWTH, delta=1e-6)
        self.assertAlmostEqual(report['baseline_run']['tracked_flux_values']['EX_etoh_e'], 8.279455, delta=1e-6)

    def test_ethanol_closed_run_records_visible_values(self):
        report = self._record(True)
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertEqual(report['current_run_type'], 'ethanol_closed')
        self.assertAlmostEqual(report['ethanol_closed_run']['growth'], self.MODIFIED_GROWTH, delta=1e-6)
        self.assertAlmostEqual(report['ethanol_closed_run']['tracked_flux_values']['EX_lac__D_e'], 17.758027, delta=1e-6)

    def test_runs_can_be_recorded_in_either_order(self):
        report = self._complete(order=[True, False])
        self.assertTrue(report['all_runs_recorded'])
        self.assertTrue(report['same_controlled_setup'])
        self.assertTrue(report['ready_to_deliver'])

    def test_repeated_valid_run_updates_without_duplication(self):
        report = self._record(False)
        report = self._record(False, report=report)
        self.assertEqual(report['recorded_run_count'], 1)
        self.assertIsNotNone(report['baseline_run'])
        self.assertIsNone(report['ethanol_closed_run'])

    def test_method_objective_and_gene_guards(self):
        report = self._record(False, method='pFBA')
        self.assertFalse(report['current_run_valid'])
        self.assertIn('Use FBA', ' '.join(report['current_issues']))
        report = self._record(False, objective='EX_etoh_e')
        self.assertFalse(report['current_run_valid'])
        self.assertIn('biomass objective', ' '.join(report['current_issues']))
        genes = dict(self.genes)
        genes['b0728'] = False
        report = self._record(False, genes=genes)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('Keep every gene active', ' '.join(report['current_issues']))

    def test_oxygen_must_be_closed_in_both_runs(self):
        reactions = simulation._build_default_reactions_data()
        report = self._record(False, reactions=reactions)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('Close the oxygen lower bound', ' '.join(report['current_issues']))

    def test_only_ethanol_upper_bound_may_change(self):
        reactions = self._reactions(False)
        acetate_index = list(simulation.REACTIONS.index).index('EX_ac_e')
        reactions[f'reaction_{acetate_index}_ub'] = False
        report = self._record(False, reactions=reactions)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('unrelated environmental bound', ' '.join(report['current_issues']))

    def test_exact_complete_panel_is_required(self):
        report = self._record(False, selected=self.panel[:-1])
        self.assertFalse(report['current_run_valid'])
        report = self._record(False, selected=self.panel + ['EX_pyr_e'])
        self.assertFalse(report['current_run_valid'])
        self.assertIn('exactly the complete', ' '.join(report['current_issues']))

    def test_missing_production_and_medium_values_are_not_zero(self):
        report = self._record(False, production=self._production(False, missing=['EX_lac__D_e']))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('missing numeric', ' '.join(report['current_issues']))
        report = self._record(False, medium=self._medium(False, missing=['EX_o2_e']))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('missing required', ' '.join(report['current_issues']))

    def test_production_and_exchange_reports_must_describe_same_solution(self):
        production = self._production(False, profile_override={'EX_ac_e': 99.0})
        report = self._record(False, production=production)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('same visible solution', ' '.join(report['current_issues']))

    def test_visible_fba_diagnostics_are_required_and_consistent(self):
        production = self._production(False, diagnostics_override={'primary_objective_flux': None})
        report = self._record(False, production=production)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('missing biomass or FBA objective diagnostics', ' '.join(report['current_issues']))
        production = self._production(False, diagnostics_override={'method_score': 99.0})
        report = self._record(False, production=production)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('method score', ' '.join(report['current_issues']))

    def test_reference_requires_active_ethanol_and_modified_requires_closed_export(self):
        production = self._production(False, profile_override={'EX_etoh_e': 0.0})
        medium = self._medium(False, override={'EX_etoh_e': 0.0})
        report = self._record(False, production=production, medium=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('active ethanol export', ' '.join(report['current_issues']))
        production = self._production(True, profile_override={'EX_etoh_e': 1.0})
        medium = self._medium(True, override={'EX_etoh_e': 1.0})
        report = self._record(True, production=production, medium=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('still exports ethanol', ' '.join(report['current_issues']))

    def test_complete_comparison_derives_expected_differences(self):
        report = self._complete()
        self.assertTrue(report['all_runs_recorded'])
        self.assertAlmostEqual(report['growth_ratio'], 0.651531, delta=1e-6)
        expected = {
            'EX_ac_e': -8.357558,
            'EX_etoh_e': -8.279455,
            'EX_for_e': -16.993022,
            'EX_succ_e': 0.0,
            'EX_lac__D_e': 17.758027,
        }
        for reaction_id, value in expected.items():
            self.assertAlmostEqual(report['flux_differences'][reaction_id], value, delta=1e-6)
        self.assertEqual(report['largest_increase_candidates'], ['EX_lac__D_e'])
        self.assertTrue(report['relationship_supported'])
        self.assertTrue(report['ready_to_deliver'])

    def test_modified_run_must_remain_viable(self):
        report = self._record(False)
        production = self._production(True, biomass=0.05)
        production['method_diagnostics']['primary_objective_flux'] = 0.05
        production['method_diagnostics']['method_score'] = 0.05
        report = self._record(True, report=report, result=0.05, production=production)
        self.assertTrue(report['all_runs_recorded'])
        self.assertFalse(report['relationship_supported'])
        self.assertFalse(report['ready_to_deliver'])

    def test_invalid_later_attempt_preserves_complete_evidence(self):
        report = self._complete()
        preserved_baseline = json.dumps(report['baseline_run'], sort_keys=True)
        preserved_modified = json.dumps(report['ethanol_closed_run'], sort_keys=True)
        report = self._record(False, report=report, method='pFBA')
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['ready_to_deliver'])
        self.assertEqual(json.dumps(report['baseline_run'], sort_keys=True), preserved_baseline)
        self.assertEqual(json.dumps(report['ethanol_closed_run'], sort_keys=True), preserved_modified)

    def test_answer_parser_accepts_concise_lactate_forms(self):
        report = self._complete()
        for answer in ('D-lactate', 'd lactate', 'lactate', 'EX_lac__D_e', 'lactato'):
            with self.subTest(answer=answer):
                self.assertTrue(simulation.mission21_answer_matches(answer, report))

    def test_answer_parser_rejects_wrong_or_additional_routes(self):
        report = self._complete()
        for answer in ('ethanol', 'acetate', 'formate', 'succinate', 'oxygen', 'all products', 'lactate and acetate'):
            with self.subTest(answer=answer):
                self.assertFalse(simulation.mission21_answer_matches(answer, report))

    def test_report_preserves_evidence_language_and_does_not_state_answer(self):
        report = self._complete()
        text = simulation.build_mission21_compensatory_report_text(report)
        self.assertIn('Evidence complete.', text)
        self.assertIn('Which tracked secretion showed the largest increase', text)
        self.assertNotIn('The answer is', text)
        self.assertNotIn('largest increase was D-Lactate', text)
        invalid = self._record(False, report=report, method='pFBA')
        text = simulation.build_mission21_compensatory_report_text(invalid)
        self.assertIn('Latest run was not recorded', text)
        self.assertIn('Previously valid Mission 21 evidence remains available', text)
        self.assertIn('Evidence complete.', text)

    def test_remote_wrapper_reuses_visible_result_without_network_or_solver(self):
        source = inspect.getsource(simulation.run_mission21_comparison_check_remote)
        self.assertIn('run_mission21_comparison_check(simulation_results)', source)
        self.assertNotIn('requests.', source)
        self.assertNotIn('_simulate_', source)

    def test_validator_contains_no_hidden_simulation(self):
        source = inspect.getsource(simulation.run_mission21_comparison_check)
        source += inspect.getsource(simulation._build_mission21_data)
        self.assertNotIn('simul.simulate', source)
        self.assertNotIn('_simulate_local', source)
        self.assertNotIn('run_simul', source)

    def test_window_validates_the_visible_result_and_has_browser_wrapper(self):
        source = (CODE_DIR / 'window.py').read_text()
        self.assertIn('run_mission21_comparison_check(self.results)', source)
        self.assertIn('run_mission21_comparison_check_remote(BACKEND_URL, self.results)', source)
        self.assertNotIn('run_mission21_comparison_check(compare_runs)', source)

    def test_dr_vega_owns_only_missions_21_and_22(self):
        source = (CODE_DIR / 'mission21.py').read_text()
        self.assertIn('from mission22 import Mission22_info', source)
        self.assertNotIn('Mission23_info', source)
        self.assertNotIn('Mission24_info', source)
        self.assertNotIn('Mission25_info', source)
        self.assertIn("if '22' in self.missions_completed", source)
        self.assertIn('Dr. Luna will continue', source)
        mission22_source = (CODE_DIR / 'mission22.py').read_text()
        self.assertNotIn('In Mission 21 you compared two environments', mission22_source)
        self.assertIn('export-bound change', mission22_source)

    def test_activation_and_delivery_guards_are_present(self):
        source = (CODE_DIR / 'mission21.py').read_text()
        self.assertIn('is_mission21_unlocked', source)
        npc_source = source.split('class Mission21_info:', 1)[0]
        self.assertIn("if not self.player.is_mission_unlocked('21'):", npc_source)
        self.assertIn('self.menu_message(locked_dialogue, buttons=False)', npc_source)
        self.assertIn("if '21' in self.missions_completed", source)
        self.assertIn("if '21' in self.missions_activated", source)
        self.assertIn('initialise_mission21_compensatory_comparison', source)
        self.assertIn("if '21' not in self.missions_activated", source)
        self.assertIn('normalise_mission21_answer', source)
        self.assertIn('mission21_answer_matches', source)

    def test_generic_compare_runs_describes_ethanol_closure_explicitly(self):
        snapshot = {
            'environment_changed': True,
            'oxygen_lower_bound_closed': True,
            'ethanol_upper_bound_closed': True,
            'oxygen_unexpected_changes': [],
        }
        text = simulation._format_compare_environment(snapshot)
        self.assertIn('oxygen lower bound closed', text)
        self.assertIn('ethanol upper bound closed', text)

    def test_generic_compare_runs_does_not_turn_missing_fluxes_into_zero(self):
        base = {
            'slot': 'A', 'name': 'Run A', 'run_kind': 'test',
            'method': 'FBA', 'objective': simulation.MISSION21_GROWTH_OBJECTIVE,
            'growth_value': 0.2, 'knocked_out_genes': [], 'environment_changed': False,
            'selected_production_fluxes': ['EX_ac_e'], 'production_flux_values': {},
            'exchange_uptake_fluxes': {}, 'oxygen_unexpected_changes': [],
        }
        modified = dict(base)
        modified.update({'slot': 'B', 'name': 'Run B'})
        text = simulation.build_compare_runs_report_text({'run_a': base, 'run_b': modified})
        self.assertIn('Oxygen uptake magnitude', text)
        self.assertIn('not available', text)
        self.assertNotIn('Acetate (EX_ac_e): 0.000 -> 0.000', text)

    def test_full_complete_state_is_json_serialisable(self):
        json.dumps(self._complete())

    def test_independent_fba_and_fva_values(self):
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
            lb_ref = reaction.attrib[f"{{{ns['fbc']}}}lowerFluxBound"]
            ub_ref = reaction.attrib[f"{{{ns['fbc']}}}upperFluxBound"]
            bounds.append((parameters[lb_ref], parameters[ub_ref]))
            reactants = reaction.find('sbml:listOfReactants', ns)
            if reactants is not None:
                for item in reactants:
                    matrix[species_index[item.attrib['species']], column] -= float(item.attrib.get('stoichiometry', '1'))
            products = reaction.find('sbml:listOfProducts', ns)
            if products is not None:
                for item in products:
                    matrix[species_index[item.attrib['species']], column] += float(item.attrib.get('stoichiometry', '1'))

        biomass_index = reaction_index['R_BIOMASS_Ecoli_core_w_GAM']

        def solve(ethanol_closed):
            current_bounds = list(bounds)
            oxygen_index = reaction_index['R_EX_o2_e']
            current_bounds[oxygen_index] = (0.0, current_bounds[oxygen_index][1])
            if ethanol_closed:
                ethanol_index = reaction_index['R_EX_etoh_e']
                current_bounds[ethanol_index] = (current_bounds[ethanol_index][0], 0.0)
            objective = np.zeros(len(reactions))
            objective[biomass_index] = -1.0
            result = linprog(
                objective,
                A_eq=matrix,
                b_eq=np.zeros(len(species)),
                bounds=current_bounds,
                method='highs',
            )
            self.assertTrue(result.success)
            return result, current_bounds

        expected = {
            False: (self.BASELINE_GROWTH, self.BASELINE_PROFILE),
            True: (self.MODIFIED_GROWTH, self.MODIFIED_PROFILE),
        }
        for ethanol_closed, (expected_growth, expected_profile) in expected.items():
            result, current_bounds = solve(ethanol_closed)
            self.assertAlmostEqual(result.x[biomass_index], expected_growth, delta=1e-6)
            for reaction_id, expected_value in expected_profile.items():
                self.assertAlmostEqual(
                    result.x[reaction_index[f'R_{reaction_id}']],
                    expected_value,
                    delta=1e-5,
                )

            # FVA-style checks at optimum confirm that the tracked values are
            # effectively fixed and the largest increase is not a solver tie.
            optimum = result.x[biomass_index]
            fva_bounds = list(current_bounds)
            fva_bounds[biomass_index] = (optimum - 1e-8, optimum + 1e-8)
            for reaction_id, expected_value in expected_profile.items():
                index = reaction_index[f'R_{reaction_id}']
                extrema = []
                for direction in (1.0, -1.0):
                    objective = np.zeros(len(reactions))
                    objective[index] = direction
                    fva = linprog(
                        objective,
                        A_eq=matrix,
                        b_eq=np.zeros(len(species)),
                        bounds=fva_bounds,
                        method='highs',
                    )
                    self.assertTrue(fva.success)
                    extrema.append(float(fva.x[index]))
                self.assertAlmostEqual(min(extrema), expected_value, delta=1e-5)
                self.assertAlmostEqual(max(extrema), expected_value, delta=1e-5)

    def test_backend_fba_matches_visible_contract_when_dependencies_exist(self):
        backend_dir = PROJECT_ROOT / 'backend'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        try:
            from app.schemas import SimulateRequest
            from app.simulator import simulate as backend_simulate
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'Backend MEWpy/COBRApy unavailable: {exc}')

        for ethanol_closed, expected_growth, expected_profile in (
            (False, self.BASELINE_GROWTH, self.BASELINE_PROFILE),
            (True, self.MODIFIED_GROWTH, self.MODIFIED_PROFILE),
        ):
            reactions = self._reactions(ethanol_closed)
            env_conditions = simulation._build_envconditions_from_reactions(reactions, simulation.REACTIONS)
            response = backend_simulate(SimulateRequest(
                method=simulation.MISSION21_METHOD,
                objective=simulation.MISSION21_GROWTH_OBJECTIVE,
                gene_knockouts=[],
                env_conditions=env_conditions,
            ))
            self.assertEqual(response.status, 'ok', response.message)
            self.assertAlmostEqual(float(response.primary_objective_flux), expected_growth, delta=1e-3)
            for reaction_id, expected_value in expected_profile.items():
                self.assertAlmostEqual(float(response.fluxes[reaction_id]), expected_value, delta=1e-3)


if __name__ == '__main__':
    unittest.main()
