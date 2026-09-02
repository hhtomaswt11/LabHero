"""Regression tests for Mission 22 phenotype equivalence audit.

Run from the project root with:
    python3 tests/test_mission22.py
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


class Mission22RegressionTests(unittest.TestCase):
    GROWTH = 0.1891731046374887
    PROFILE = {
        'EX_ac_e': 0.0,
        'EX_etoh_e': 16.584255740929652,
        'EX_for_e': 3.9563473930779764,
        'EX_succ_e': 0.0,
        'EX_lac__D_e': 0.0,
    }

    def setUp(self):
        self.panel = list(simulation.MISSION22_REQUIRED_TRACKED_FLUXES)

    def _genes(self, genetic=False, only=None):
        genes = simulation._build_active_genes_data()
        targets = list(only if only is not None else (simulation.MISSION22_TARGET_GENES if genetic else []))
        for gene_id in targets:
            genes[gene_id] = False
        return genes

    def _reactions(self, environmental=False, acetate_closed=None):
        reactions = simulation._build_default_reactions_data()
        oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION22_OXYGEN_REACTION)
        reactions[f'reaction_{oxygen_index}_lb'] = False
        if acetate_closed is None:
            acetate_closed = environmental
        if acetate_closed:
            acetate_index = list(simulation.REACTIONS.index).index(simulation.MISSION22_ENVIRONMENTAL_EXPORT)
            reactions[f'reaction_{acetate_index}_ub'] = False
        return reactions

    def _medium(self, missing=None, override=None):
        missing = set(missing or [])
        raw = {
            simulation.MISSION22_GLUCOSE_REACTION: -10.0,
            simulation.MISSION22_OXYGEN_REACTION: 0.0,
            **self.PROFILE,
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

    def _production(self, missing=None, override=None, diagnostics_override=None, biomass=None):
        missing = set(missing or [])
        profile = dict(self.PROFILE)
        if override:
            profile.update(override)
        diagnostics = {
            'method': simulation.MISSION22_METHOD,
            'objective_reaction': simulation.MISSION22_GROWTH_OBJECTIVE,
            'primary_objective_flux': self.GROWTH,
            'method_score': self.GROWTH,
            'method_score_name': 'primary_objective_flux',
            'total_absolute_flux': 293.75463,
            'active_reaction_count': 46,
        }
        if diagnostics_override:
            diagnostics.update(diagnostics_override)
        return {
            'selected_ids': list(self.panel),
            'items': [
                {'reaction_id': reaction_id, 'production_flux': float(profile[reaction_id])}
                for reaction_id in self.panel
                if reaction_id not in missing
            ],
            'biomass_raw': self.GROWTH if biomass is None else biomass,
            'method_diagnostics': diagnostics,
        }

    def _record(
        self,
        genetic=False,
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
        method = method or simulation.MISSION22_METHOD
        objective = objective or simulation.MISSION22_GROWTH_OBJECTIVE
        if result is None:
            result = self.GROWTH
        if genes is None:
            genes = self._genes(genetic)
        if reactions is None:
            reactions = self._reactions(environmental=not genetic)
        if medium is None:
            medium = self._medium()
        if production is None:
            production = self._production(diagnostics_override={
                'method': method,
                'objective_reaction': objective,
                'method_score_name': 'primary_objective_flux' if method == 'FBA' else 'total_absolute_flux',
            })
        with patch.object(simulation, 'save_mission22_comparison_check'):
            return simulation._build_mission22_data(
                method,
                objective,
                result,
                dict(genes),
                dict(reactions),
                production_fluxes=production,
                medium_fluxes=medium,
                existing_report=report,
                selected_fluxes=list(self.panel if selected is None else selected),
                objective_error=error,
            )

    def _complete(self, order=None):
        report = None
        for genetic in (order or [False, True]):
            report = self._record(genetic=genetic, report=report)
        return report

    def test_progression_and_redesign_constants(self):
        self.assertFalse(simulation.is_mission22_unlocked([]))
        self.assertFalse(simulation.is_mission22_unlocked(['20']))
        self.assertTrue(simulation.is_mission22_unlocked(['21']))
        self.assertEqual(simulation.MISSION22_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION22_METHOD, 'FBA')
        self.assertEqual(simulation.MISSION22_TARGET_GENES, ['b2297', 'b2458'])
        self.assertEqual(simulation.MISSION22_EXPECTED_DISABLED_REACTIONS, ['PTAr'])
        self.assertEqual(simulation.MISSION22_EXPECTED_DIFFERENT_OUTPUT_COUNT, 0)
        self.assertFalse(hasattr(simulation, 'MISSION22_MIN_GROWTH'))
        self.assertFalse(hasattr(simulation, 'MISSION22_MIN_PRODUCTION_INCREASE'))

    def test_initial_state_is_json_serialisable(self):
        with patch.object(simulation, 'save_mission22_comparison_check'):
            report = simulation.initialise_mission22_phenotype_equivalence_audit()
        self.assertEqual(report['recorded_run_count'], 0)
        self.assertEqual(report['missing_run_types'], ['environmental_intervention', 'genetic_intervention'])
        self.assertFalse(report['evidence_ready'])
        json.dumps(report)

    def test_environment_reader_is_order_independent_and_legacy_compatible(self):
        reactions = self._reactions(environmental=True)
        expected = simulation._mission22_environment_status(reactions)
        self.assertTrue(expected['bounds_complete'])
        self.assertTrue(expected['oxygen_lower_bound_closed'])
        self.assertTrue(expected['acetate_upper_bound_closed'])
        self.assertEqual(simulation._mission22_environment_status(dict(reversed(list(reactions.items())))), expected)
        legacy = {f'widget_{index}': value for index, value in enumerate(reactions.values())}
        self.assertEqual(simulation._mission22_environment_status(legacy), expected)

    def test_incomplete_explicit_bound_payload_is_rejected(self):
        reactions = self._reactions(environmental=True)
        reactions.pop('reaction_0_ub')
        report = self._record(False, reactions=reactions)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('environmental-bound payload is incomplete', ' '.join(report['current_issues']))

    def test_complete_gpr_requires_both_genes(self):
        self.assertNotIn('PTAr', simulation._mission22_disabled_reactions(['b2297']))
        self.assertNotIn('PTAr', simulation._mission22_disabled_reactions(['b2458']))
        self.assertEqual(simulation._mission22_disabled_reactions(['b2297', 'b2458']), ['PTAr'])

    def test_environmental_intervention_records_visible_values(self):
        report = self._record(False)
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertEqual(report['current_run_type'], 'environmental_intervention')
        run = report['environmental_intervention_run']
        self.assertEqual(run['knocked_out_genes'], [])
        self.assertTrue(run['acetate_upper_bound_closed'])
        self.assertAlmostEqual(run['growth'], self.GROWTH, delta=1e-6)
        self.assertAlmostEqual(run['tracked_flux_values']['EX_etoh_e'], self.PROFILE['EX_etoh_e'], delta=1e-6)

    def test_genetic_intervention_records_gpr_evidence(self):
        report = self._record(True)
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertEqual(report['current_run_type'], 'genetic_intervention')
        run = report['genetic_intervention_run']
        self.assertEqual(set(run['knocked_out_genes']), set(simulation.MISSION22_TARGET_GENES))
        self.assertEqual(run['disabled_reactions'], ['PTAr'])
        self.assertFalse(run['acetate_upper_bound_closed'])

    def test_runs_can_be_recorded_in_either_order(self):
        report = self._complete(order=[True, False])
        self.assertTrue(report['all_runs_recorded'])
        self.assertTrue(report['same_base_protocol'])
        self.assertTrue(report['ready_to_deliver'])

    def test_repeated_valid_run_updates_without_duplication(self):
        report = self._record(False)
        report = self._record(False, report=report)
        self.assertEqual(report['recorded_run_count'], 1)
        self.assertIsNotNone(report['environmental_intervention_run'])
        self.assertIsNone(report['genetic_intervention_run'])

    def test_method_objective_and_gene_guards(self):
        report = self._record(False, method='pFBA')
        self.assertFalse(report['current_run_valid'])
        self.assertIn('Use FBA', ' '.join(report['current_issues']))
        report = self._record(False, objective='EX_etoh_e')
        self.assertFalse(report['current_run_valid'])
        self.assertIn('biomass objective', ' '.join(report['current_issues']))
        report = self._record(True, genes=self._genes(only=['b2297']))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('exactly b2297 + b2458', ' '.join(report['current_issues']))
        report = self._record(True, genes=self._genes(only=['b2297', 'b2458', 'b0728']))
        self.assertFalse(report['current_run_valid'])

    def test_interventions_cannot_be_combined_or_swapped(self):
        report = self._record(True, reactions=self._reactions(environmental=True))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('keep the acetate upper bound', ' '.join(report['current_issues']))
        report = self._record(False, reactions=self._reactions(environmental=False))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('must close acetate export', ' '.join(report['current_issues']))

    def test_oxygen_and_unrelated_environment_guards(self):
        reactions = simulation._build_default_reactions_data()
        acetate_index = list(simulation.REACTIONS.index).index(simulation.MISSION22_ENVIRONMENTAL_EXPORT)
        reactions[f'reaction_{acetate_index}_ub'] = False
        report = self._record(False, reactions=reactions)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('Close the oxygen lower bound', ' '.join(report['current_issues']))
        reactions = self._reactions(environmental=True)
        reactions['reaction_0_lb'] = not reactions['reaction_0_lb']
        report = self._record(False, reactions=reactions)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('unrelated environmental bound', ' '.join(report['current_issues']))

    def test_complete_panel_selection_and_measurement_are_required(self):
        report = self._record(False, selected=self.panel[:-1])
        self.assertFalse(report['current_run_valid'])
        self.assertIn('complete Mission 22 product/byproduct panel', ' '.join(report['current_issues']))
        report = self._record(False, selected=self.panel + ['EX_co2_e'])
        self.assertFalse(report['current_run_valid'])
        report = self._record(False, production=self._production(missing=['EX_succ_e']))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('missing numeric Mission 22 values', ' '.join(report['current_issues']))

    def test_exchange_report_is_required_and_missing_is_not_zero(self):
        report = self._record(False, medium=self._medium(missing=['EX_ac_e']))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('missing required Mission 22 reactions', ' '.join(report['current_issues']))
        report = self._record(False, medium={'error': 'missing'})
        self.assertFalse(report['current_run_valid'])

    def test_measured_zero_is_preserved_as_real_evidence(self):
        report = self._record(False)
        self.assertTrue(report['current_run_valid'])
        self.assertEqual(report['environmental_intervention_run']['tracked_flux_values']['EX_ac_e'], 0.0)
        self.assertEqual(report['environmental_intervention_run']['oxygen_uptake'], 0.0)

    def test_production_and_exchange_reports_must_describe_same_solution(self):
        report = self._record(False, production=self._production(override={'EX_etoh_e': 99.0}))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('same visible solution', ' '.join(report['current_issues']))

    def test_visible_fba_diagnostics_are_required_and_consistent(self):
        report = self._record(False, production=self._production(diagnostics_override={'primary_objective_flux': None}))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('missing biomass or FBA objective diagnostics', ' '.join(report['current_issues']))
        report = self._record(False, production=self._production(diagnostics_override={'method_score': 99.0}))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('method score', ' '.join(report['current_issues']))
        report = self._record(False, production=self._production(biomass=99.0))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('biomass evidence', ' '.join(report['current_issues']))

    def test_expected_viable_phenotype_is_required(self):
        production = self._production(override={'EX_etoh_e': 0.0})
        medium = self._medium(override={'EX_etoh_e': 0.0})
        report = self._record(False, production=production, medium=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('positive ethanol', ' '.join(report['current_issues']))
        production = self._production(override={'EX_ac_e': 1.0})
        medium = self._medium(override={'EX_ac_e': 1.0})
        report = self._record(False, production=production, medium=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('suppress acetate', ' '.join(report['current_issues']))

    def test_complete_audit_derives_zero_differences(self):
        report = self._complete()
        self.assertTrue(report['all_runs_recorded'])
        self.assertTrue(report['same_base_protocol'])
        self.assertEqual(report['different_output_ids'], [])
        self.assertEqual(report['different_output_count'], 0)
        self.assertEqual(report['maximum_absolute_difference'], 0.0)
        self.assertTrue(report['relationship_supported'])
        self.assertTrue(report['ready_to_deliver'])

    def test_difference_beyond_tolerance_is_counted_and_blocks_relationship(self):
        report = self._record(False)
        profile = dict(self.PROFILE)
        profile['EX_for_e'] += 0.02
        production = self._production(override={'EX_for_e': profile['EX_for_e']})
        medium = self._medium(override={'EX_for_e': profile['EX_for_e']})
        report = self._record(True, report=report, production=production, medium=medium)
        self.assertEqual(report['different_output_ids'], ['EX_for_e'])
        self.assertEqual(report['different_output_count'], 1)
        self.assertFalse(report['relationship_supported'])

    def test_invalid_later_attempt_preserves_complete_evidence(self):
        report = self._complete()
        environmental = json.dumps(report['environmental_intervention_run'], sort_keys=True)
        genetic = json.dumps(report['genetic_intervention_run'], sort_keys=True)
        report = self._record(False, report=report, method='pFBA')
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['ready_to_deliver'])
        self.assertEqual(json.dumps(report['environmental_intervention_run'], sort_keys=True), environmental)
        self.assertEqual(json.dumps(report['genetic_intervention_run'], sort_keys=True), genetic)

    def test_answer_parser_accepts_concise_zero_forms(self):
        report = self._complete()
        for answer in ('0', 'zero', 'none', 'no differences', 'zero outputs', 'nenhum', 'nenhuma diferença'):
            with self.subTest(answer=answer):
                self.assertTrue(simulation.mission22_answer_matches(answer, report))

    def test_answer_parser_rejects_wrong_or_contradictory_forms(self):
        report = self._complete()
        for answer in ('1', 'acetate', 'ethanol', 'PTAr', 'b2297', 'all', 'zero and acetate', '0 and 1'):
            with self.subTest(answer=answer):
                self.assertFalse(simulation.mission22_answer_matches(answer, report))

    def test_report_shows_deltas_without_revealing_the_answer(self):
        report = self._complete()
        text = simulation.build_mission22_phenotype_equivalence_report_text(report)
        self.assertIn('Evidence complete.', text)
        self.assertIn('How many recorded phenotype outputs differed beyond tolerance', text)
        self.assertIn('Genetic minus environmental phenotype differences', text)
        self.assertIn('Output-difference tolerance: 0.010', text)
        self.assertIn('GPR labels describe mechanisms; they are not counted phenotype outputs', text)
        self.assertNotIn('The answer is', text)
        self.assertNotIn('0 outputs differed', text)
        self.assertNotIn('phenotypes are equivalent', text.lower())
        invalid = self._record(False, report=report, method='pFBA')
        text = simulation.build_mission22_phenotype_equivalence_report_text(invalid)
        self.assertIn('Latest run was not recorded', text)
        self.assertIn('Previously valid Mission 22 evidence remains available', text)
        self.assertIn('Evidence complete.', text)

    def test_remote_wrapper_reuses_visible_result_without_network_or_solver(self):
        source = inspect.getsource(simulation.run_mission22_comparison_check_remote)
        self.assertIn('run_mission22_comparison_check(simulation_results)', source)
        self.assertNotIn('requests.', source)
        self.assertNotIn('_simulate_', source)

    def test_validator_contains_no_hidden_simulation(self):
        source = inspect.getsource(simulation.run_mission22_comparison_check)
        source += inspect.getsource(simulation._build_mission22_data)
        self.assertNotIn('simul.simulate', source)
        self.assertNotIn('_simulate_local', source)
        self.assertNotIn('run_simul', source)

    def test_window_validates_visible_result_and_highlights_both_genes(self):
        source = (CODE_DIR / 'window.py').read_text()
        self.assertIn('run_mission22_comparison_check(self.results)', source)
        self.assertIn('run_mission22_comparison_check_remote(BACKEND_URL, self.results)', source)
        self.assertNotIn('run_mission22_comparison_check(compare_runs)', source)
        self.assertIn("('22', list(MISSION22_TARGET_GENES))", source)

    def test_activation_and_delivery_guards_are_present(self):
        source = (CODE_DIR / 'mission22.py').read_text()
        self.assertIn('is_mission22_unlocked', source)
        self.assertIn("if '22' in self.missions_completed", source)
        self.assertIn("if '22' in self.missions_activated", source)
        self.assertIn('initialise_mission22_phenotype_equivalence_audit', source)
        self.assertIn("if '22' not in self.missions_activated", source)
        self.assertIn('normalise_mission22_answer', source)
        self.assertIn('mission22_answer_matches', source)

    def test_vega_ends_at_22_and_luna_mission23_is_connected_to_runtime(self):
        vega = (CODE_DIR / 'mission21.py').read_text()
        self.assertIn('Dr. Luna will continue in Mission 23.', vega)
        self.assertNotIn('Mission23_info', vega)
        luna = (CODE_DIR / 'mission23.py').read_text()
        self.assertIn('class Mission23:', luna)
        self.assertIn('from mission24 import Mission24_info', luna)
        self.assertIn("I'm Dr. Luna", luna)
        level = (CODE_DIR / 'level.py').read_text()
        player = (CODE_DIR / 'player.py').read_text()
        self.assertIn('from mission23 import Mission23', level)
        self.assertIn("obj.name == 'Mission23'", level)
        self.assertIn("name == 'Mission23'", player)
        self.assertNotIn("obj.name == 'Mission26'", level)
        self.assertNotIn("name == 'Mission26'", player)

    def test_old_invalid_mission22_recipe_is_removed(self):
        simulation_source = (CODE_DIR / 'simulation.py').read_text()
        mission_source = (CODE_DIR / 'mission22.py').read_text()
        self.assertNotIn('MISSION22_MIN_GROWTH = 1.0', simulation_source)
        self.assertNotIn('MISSION22_MIN_PRODUCTION_INCREASE = 20.0', simulation_source)
        self.assertNotIn('turn off b2297 / pta', mission_source)
        self.assertNotIn('Knockout Comparison', mission_source)

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

        def solve(genetic):
            current_bounds = list(bounds)
            oxygen_index = reaction_index['R_EX_o2_e']
            current_bounds[oxygen_index] = (0.0, current_bounds[oxygen_index][1])
            if genetic:
                current_bounds[reaction_index['R_PTAr']] = (0.0, 0.0)
            else:
                acetate_index = reaction_index['R_EX_ac_e']
                current_bounds[acetate_index] = (current_bounds[acetate_index][0], 0.0)
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

        outputs = {
            'R_EX_glc__D_e': -10.0,
            'R_EX_o2_e': 0.0,
            'R_EX_ac_e': 0.0,
            'R_EX_etoh_e': self.PROFILE['EX_etoh_e'],
            'R_EX_for_e': self.PROFILE['EX_for_e'],
            'R_EX_succ_e': 0.0,
            'R_EX_lac__D_e': 0.0,
        }
        solutions = []
        for genetic in (False, True):
            result, current_bounds = solve(genetic)
            solutions.append(result.x)
            self.assertAlmostEqual(result.x[biomass_index], self.GROWTH, delta=1e-6)
            for reaction_id, expected_value in outputs.items():
                self.assertAlmostEqual(result.x[reaction_index[reaction_id]], expected_value, delta=1e-5)

            optimum = result.x[biomass_index]
            fva_bounds = list(current_bounds)
            fva_bounds[biomass_index] = (optimum - 1e-8, optimum + 1e-8)
            for reaction_id, expected_value in outputs.items():
                index = reaction_index[reaction_id]
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
                self.assertAlmostEqual(min(extrema), expected_value, delta=5e-5)
                self.assertAlmostEqual(max(extrema), expected_value, delta=5e-5)

        for left, right in zip(solutions[0], solutions[1]):
            # Internal flux vectors need not be identical; the mission compares
            # only the explicitly recorded phenotype outputs above.
            pass

    def test_backend_matches_visible_contract_when_dependencies_exist(self):
        backend_dir = PROJECT_ROOT / 'backend'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        try:
            from app.schemas import SimulateRequest
            from app.simulator import simulate as backend_simulate
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'Backend MEWpy/COBRApy unavailable: {exc}')

        for genetic in (False, True):
            reactions = self._reactions(environmental=not genetic)
            env_conditions = simulation._build_envconditions_from_reactions(reactions, simulation.REACTIONS)
            response = backend_simulate(SimulateRequest(
                method=simulation.MISSION22_METHOD,
                objective=simulation.MISSION22_GROWTH_OBJECTIVE,
                gene_knockouts=list(simulation.MISSION22_TARGET_GENES if genetic else []),
                env_conditions=env_conditions,
            ))
            self.assertEqual(response.status, 'ok', response.message)
            self.assertAlmostEqual(float(response.primary_objective_flux), self.GROWTH, delta=1e-3)
            self.assertAlmostEqual(float(response.fluxes['EX_etoh_e']), self.PROFILE['EX_etoh_e'], delta=1e-3)
            self.assertAlmostEqual(float(response.fluxes['EX_for_e']), self.PROFILE['EX_for_e'], delta=1e-3)
            self.assertAlmostEqual(float(response.fluxes['EX_ac_e']), 0.0, delta=1e-3)


if __name__ == '__main__':
    unittest.main()
