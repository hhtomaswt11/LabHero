"""Regression tests for Mission 20 context-specific export robustness.

Run from the project root with:
    python3 tests/test_mission20.py
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


class Mission20RegressionTests(unittest.TestCase):
    AEROBIC_GROWTH = 0.873921507
    ANAEROBIC_GROWTH = 0.211662950
    ANAEROBIC_CLOSED_GROWTH = 0.189173105
    AEROBIC_TOTAL = 518.422086
    ANAEROBIC_TOTAL = 335.650617
    ANAEROBIC_CLOSED_TOTAL = 293.754630
    AEROBIC_PROFILE = {
        'EX_ac_e': 0.0,
        'EX_etoh_e': 0.0,
        'EX_for_e': 0.0,
        'EX_succ_e': 0.0,
        'EX_lac__D_e': 0.0,
    }
    ANAEROBIC_PROFILE = {
        'EX_ac_e': 8.503585,
        'EX_etoh_e': 8.279455,
        'EX_for_e': 17.804674,
        'EX_succ_e': 0.0,
        'EX_lac__D_e': 0.0,
    }
    ANAEROBIC_CLOSED_PROFILE = {
        'EX_ac_e': 0.0,
        'EX_etoh_e': 16.584256,
        'EX_for_e': 3.956347,
        'EX_succ_e': 0.0,
        'EX_lac__D_e': 0.0,
    }

    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.panel = list(simulation.MISSION20_REQUIRED_TRACKED_FLUXES)

    def _reactions(self, oxygen_closed=False, acetate_closed=False):
        reactions = simulation._build_default_reactions_data()
        if oxygen_closed:
            index = list(simulation.REACTIONS.index).index(simulation.MISSION20_OXYGEN_REACTION)
            reactions[f'reaction_{index}_lb'] = False
        if acetate_closed:
            index = list(simulation.REACTIONS.index).index(simulation.MISSION20_ACETATE_EXPORT)
            reactions[f'reaction_{index}_ub'] = False
        return reactions

    def _values(self, oxygen_closed=False, acetate_closed=False):
        if not oxygen_closed:
            return self.AEROBIC_GROWTH, dict(self.AEROBIC_PROFILE), self.AEROBIC_TOTAL, 48, 21.799493
        if acetate_closed:
            return (
                self.ANAEROBIC_CLOSED_GROWTH,
                dict(self.ANAEROBIC_CLOSED_PROFILE),
                self.ANAEROBIC_CLOSED_TOTAL,
                46,
                0.0,
            )
        return self.ANAEROBIC_GROWTH, dict(self.ANAEROBIC_PROFILE), self.ANAEROBIC_TOTAL, 47, 0.0

    def _medium(self, oxygen_closed=False, acetate_closed=False, missing=None, override=None):
        missing = set(missing or [])
        growth, profile, total, active, oxygen_uptake = self._values(oxygen_closed, acetate_closed)
        raw = {
            simulation.MISSION20_GLUCOSE_REACTION: -10.0,
            simulation.MISSION20_OXYGEN_REACTION: -float(oxygen_uptake),
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
        oxygen_closed=False,
        acetate_closed=False,
        missing=None,
        profile_override=None,
        diagnostics_override=None,
        biomass=None,
    ):
        missing = set(missing or [])
        growth, profile, total, active, oxygen_uptake = self._values(oxygen_closed, acetate_closed)
        if profile_override:
            profile.update(profile_override)
        diagnostics = {
            'method': simulation.MISSION20_TARGET_METHOD,
            'objective_reaction': simulation.MISSION20_GROWTH_OBJECTIVE,
            'primary_objective_flux': growth,
            'method_score': total,
            'method_score_name': simulation.MISSION20_EXPECTED_SECONDARY_CRITERION,
            'total_absolute_flux': total,
            'active_reaction_count': active,
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
        oxygen_closed=False,
        acetate_closed=False,
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
        growth, profile, total, active, oxygen_uptake = self._values(oxygen_closed, acetate_closed)
        if result is None:
            result = growth
        if medium is None:
            medium = self._medium(oxygen_closed, acetate_closed)
        if production is None:
            production = self._production(oxygen_closed, acetate_closed)
        if reactions is None:
            reactions = self._reactions(oxygen_closed, acetate_closed)
        with patch.object(simulation, 'save_mission20_robustness_report_check'):
            return simulation._build_mission20_data(
                method or simulation.MISSION20_TARGET_METHOD,
                objective or simulation.MISSION20_GROWTH_OBJECTIVE,
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
        combinations = order or [
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ]
        for oxygen_closed, acetate_closed in combinations:
            report = self._record(oxygen_closed, acetate_closed, report=report)
        return report

    def test_progression_and_redesign_constants(self):
        self.assertFalse(simulation.is_mission20_unlocked([]))
        self.assertFalse(simulation.is_mission20_unlocked(['18']))
        self.assertTrue(simulation.is_mission20_unlocked(['19']))
        self.assertEqual(simulation.MISSION20_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION20_TARGET_METHOD, 'pFBA')
        self.assertEqual(simulation.MISSION20_ACETATE_EXPORT, 'EX_ac_e')
        self.assertFalse(hasattr(simulation, 'MISSION20_ALTERNATIVE_CARBON_SOURCE'))
        self.assertFalse(hasattr(simulation, 'MISSION20_MIN_GROWTH'))
        self.assertNotIn('EX_pyr_e', simulation.MISSION20_REQUIRED_MEDIUM_FLUXES)

    def test_initial_state_is_json_serialisable(self):
        with patch.object(simulation, 'save_mission20_robustness_report_check'):
            report = simulation.initialise_mission20_context_matrix()
        self.assertEqual(report['recorded_run_count'], 0)
        self.assertFalse(report['all_runs_recorded'])
        self.assertFalse(report['evidence_ready'])
        json.dumps(report)

    def test_environment_reader_is_order_independent_and_legacy_compatible(self):
        reactions = self._reactions(True, True)
        expected = simulation._mission20_environment_status(reactions)
        self.assertTrue(expected['bounds_complete'])
        self.assertTrue(expected['oxygen_lower_bound_closed'])
        self.assertTrue(expected['acetate_upper_bound_closed'])
        self.assertEqual(expected['run_type'], 'oxygen_closed_acetate_closed')
        self.assertEqual(simulation._mission20_environment_status(dict(reversed(list(reactions.items())))), expected)
        legacy = {f'widget_{index}': value for index, value in enumerate(reactions.values())}
        legacy_status = simulation._mission20_environment_status(legacy)
        self.assertEqual(legacy_status['run_type'], expected['run_type'])

    def test_incomplete_explicit_bound_payload_is_rejected(self):
        reactions = self._reactions()
        reactions.pop('reaction_0_ub')
        report = self._record(reactions=reactions)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('environmental-bound payload is incomplete', ' '.join(report['current_issues']))

    def test_each_matrix_cell_records_visible_values(self):
        cases = [
            (False, False, 'oxygen_available_baseline', 'aerobic_baseline_run'),
            (False, True, 'oxygen_available_acetate_closed', 'aerobic_acetate_closed_run'),
            (True, False, 'oxygen_closed_baseline', 'anaerobic_baseline_run'),
            (True, True, 'oxygen_closed_acetate_closed', 'anaerobic_acetate_closed_run'),
        ]
        for oxygen_closed, acetate_closed, run_type, slot in cases:
            with self.subTest(run_type=run_type):
                report = self._record(oxygen_closed, acetate_closed)
                self.assertTrue(report['current_run_valid'], report['current_issues'])
                self.assertEqual(report['current_run_type'], run_type)
                self.assertIsNotNone(report[slot])
                growth, profile, total, active, oxygen_uptake = self._values(oxygen_closed, acetate_closed)
                self.assertAlmostEqual(report[slot]['growth'], growth, delta=1e-6)
                self.assertAlmostEqual(report[slot]['oxygen_uptake'], oxygen_uptake, delta=1e-6)
                self.assertAlmostEqual(report[slot]['method_diagnostics']['total_absolute_flux'], total, delta=1e-6)
                self.assertEqual(report[slot]['method_diagnostics']['active_reaction_count'], active)

    def test_four_runs_complete_matrix_and_derive_context_response(self):
        report = self._complete()
        self.assertTrue(report['all_runs_recorded'])
        self.assertTrue(report['same_controlled_setup'])
        self.assertEqual(report['recorded_run_count'], 4)
        self.assertEqual(report['missing_run_types'], [])
        self.assertEqual(report['aerobic_response']['classification'], 'nonbinding_response')
        self.assertEqual(report['anaerobic_response']['classification'], 'binding_response')
        self.assertEqual(report['responsive_contexts'], ['oxygen_closed'])
        self.assertEqual(report['nonresponsive_contexts'], ['oxygen_available'])
        self.assertTrue(report['relationship_supported'])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['ready_to_deliver'])

    def test_matrix_runs_may_be_recorded_in_any_order(self):
        order = [(True, True), (False, True), (True, False), (False, False)]
        report = self._complete(order)
        self.assertTrue(report['relationship_supported'])
        self.assertEqual(report['recorded_run_count'], 4)

    def test_repeated_run_updates_slot_without_duplication(self):
        report = self._complete()
        report = self._record(False, False, report=report)
        self.assertEqual(report['recorded_run_count'], 4)
        self.assertTrue(report['relationship_supported'])

    def test_invalid_later_attempt_preserves_complete_evidence(self):
        report = self._complete()
        invalid = self._record(False, False, report=report, method='FBA')
        self.assertFalse(invalid['current_run_recorded'])
        self.assertIn('Use pFBA', ' '.join(invalid['current_issues']))
        self.assertEqual(invalid['recorded_run_count'], 4)
        self.assertTrue(invalid['evidence_ready'])
        self.assertTrue(invalid['relationship_supported'])
        text = simulation.build_mission20_context_report_text(invalid)
        self.assertIn('Latest run was not recorded', text)
        self.assertIn('Previously valid Mission 20 evidence remains available', text)
        self.assertIn('Evidence complete', text)

    def test_wrong_method_objective_or_knockout_is_rejected(self):
        wrong_method = self._record(method='FBA')
        self.assertFalse(wrong_method['current_run_valid'])
        wrong_objective = self._record(objective='EX_ac_e')
        self.assertFalse(wrong_objective['current_run_valid'])
        genes = dict(self.genes)
        genes['b0728'] = False
        knockout = self._record(genes=genes)
        self.assertFalse(knockout['current_run_valid'])

    def test_unrelated_environment_change_is_rejected(self):
        reactions = self._reactions()
        index = list(simulation.REACTIONS.index).index('EX_pi_e')
        reactions[f'reaction_{index}_lb'] = False
        report = self._record(reactions=reactions)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('unrelated environmental bound', ' '.join(report['current_issues']))

    def test_default_glucose_and_context_specific_oxygen_flux_are_required(self):
        wrong_glucose = self._record(medium=self._medium(override={'EX_glc__D_e': -9.0}))
        self.assertFalse(wrong_glucose['current_run_valid'])
        no_aerobic_oxygen = self._record(medium=self._medium(override={'EX_o2_e': 0.0}))
        self.assertFalse(no_aerobic_oxygen['current_run_valid'])
        anaerobic_oxygen = self._record(
            True,
            False,
            medium=self._medium(True, False, override={'EX_o2_e': -1.0}),
        )
        self.assertFalse(anaerobic_oxygen['current_run_valid'])

    def test_missing_medium_or_production_value_is_not_treated_as_zero(self):
        medium_missing = self._record(medium=self._medium(missing={'EX_o2_e'}))
        self.assertFalse(medium_missing['current_run_valid'])
        incomplete_medium = self._medium()
        for item in incomplete_medium['items']:
            if item['reaction_id'] == 'EX_o2_e':
                item.pop('raw_flux')
        incomplete = self._record(medium=incomplete_medium)
        self.assertFalse(incomplete['current_run_valid'])
        production_missing = self._record(production=self._production(missing={'EX_ac_e'}))
        self.assertFalse(production_missing['current_run_valid'])

    def test_nonfinite_numeric_evidence_is_rejected(self):
        medium = self._medium()
        for item in medium['items']:
            if item['reaction_id'] == 'EX_o2_e':
                item['raw_flux'] = float('nan')
                item['uptake_flux'] = float('nan')
        self.assertFalse(self._record(medium=medium)['current_run_valid'])

        production = self._production(diagnostics_override={'method_score': float('inf')})
        self.assertFalse(self._record(production=production)['current_run_valid'])

        self.assertFalse(self._record(result=float('nan'))['current_run_valid'])

    def test_complete_panel_must_be_selected_and_measured(self):
        selected = [reaction_id for reaction_id in self.panel if reaction_id != 'EX_for_e']
        report = self._record(selected=selected)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('complete Mission 20 product/byproduct panel', ' '.join(report['current_issues']))

    def test_production_and_exchange_reports_must_describe_same_solution(self):
        production = self._production(True, False, profile_override={'EX_ac_e': 7.0})
        report = self._record(True, False, production=production)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('same visible solution', ' '.join(report['current_issues']))

    def test_pfba_diagnostics_are_mandatory_and_consistent(self):
        missing = self._production()
        missing.pop('method_diagnostics')
        report = self._record(production=missing)
        self.assertFalse(report['current_run_valid'])
        bad_name = self._production(diagnostics_override={'method_score_name': 'primary_objective_flux'})
        report = self._record(production=bad_name)
        self.assertFalse(report['current_run_valid'])
        bad_score = self._production(diagnostics_override={'method_score': self.AEROBIC_TOTAL + 5.0})
        report = self._record(production=bad_score)
        self.assertFalse(report['current_run_valid'])

    def test_primary_objective_and_biomass_must_match_visible_result(self):
        primary = self._production(diagnostics_override={'primary_objective_flux': 0.5})
        report = self._record(production=primary)
        self.assertFalse(report['current_run_valid'])
        biomass = self._production(biomass=0.5)
        report = self._record(production=biomass)
        self.assertFalse(report['current_run_valid'])

    def test_closed_acetate_upper_bound_requires_measured_zero_export(self):
        production = self._production(False, True, profile_override={'EX_ac_e': 0.5})
        medium = self._medium(False, True, override={'EX_ac_e': 0.5})
        report = self._record(False, True, production=production, medium=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('did not eliminate acetate export', ' '.join(report['current_issues']))

    def test_pair_metrics_match_expected_growth_and_flux_changes(self):
        report = self._complete()
        aerobic = report['aerobic_response']
        anaerobic = report['anaerobic_response']
        self.assertAlmostEqual(aerobic['growth_ratio'], 1.0, delta=1e-6)
        self.assertAlmostEqual(aerobic['maximum_profile_change'], 0.0, delta=1e-6)
        self.assertAlmostEqual(anaerobic['growth_ratio'], 0.893742, delta=1e-5)
        self.assertAlmostEqual(anaerobic['flux_changes']['EX_ac_e'], -8.503585, delta=1e-6)
        self.assertAlmostEqual(anaerobic['flux_changes']['EX_etoh_e'], 8.304801, delta=1e-5)
        self.assertAlmostEqual(anaerobic['flux_changes']['EX_for_e'], -13.848327, delta=1e-5)

    def test_answer_parser_accepts_direct_oxygen_closed_forms(self):
        report = self._complete()
        accepted = [
            'anaerobic',
            'without oxygen',
            'no O2',
            'oxygen closed',
            'oxygen unavailable',
            'EX_o2_e closed',
            'anaeróbio',
            'sem oxigénio',
        ]
        for answer in accepted:
            with self.subTest(answer=answer):
                self.assertTrue(simulation.mission20_answer_matches(answer, report))

    def test_answer_parser_rejects_opposite_ambiguous_or_extra_contexts(self):
        report = self._complete()
        rejected = [
            'aerobic',
            'with oxygen',
            'both',
            'neither',
            'oxygen',
            'acetate',
            'pFBA',
            'anaerobic and aerobic',
            'without oxygen and with oxygen',
        ]
        for answer in rejected:
            with self.subTest(answer=answer):
                self.assertFalse(simulation.mission20_answer_matches(answer, report))

    def test_answer_cannot_pass_before_complete_supported_evidence(self):
        report = self._record()
        self.assertFalse(simulation.mission20_answer_matches('anaerobic', report))

    def test_report_displays_evidence_without_stating_the_answer(self):
        report = self._complete()
        text = simulation.build_mission20_context_report_text(report)
        self.assertIn('Evidence complete', text)
        self.assertIn('Oxygen-available pair comparison', text)
        self.assertIn('Oxygen-closed pair comparison', text)
        self.assertIn('Question: In which oxygen context', text)
        lower = text.lower()
        self.assertNotIn('the answer is', lower)
        self.assertNotIn('responsive context: oxygen_closed', lower)
        self.assertNotIn('binding_response', lower)

    def test_remote_wrapper_reuses_visible_result_without_request(self):
        source = inspect.getsource(simulation.run_mission20_robustness_report_check_remote)
        self.assertNotIn('requests.', source)
        self.assertNotIn('_simulate_', source)
        self.assertIn('run_mission20_robustness_report_check', source)

    def test_validator_contains_no_hidden_solver_call(self):
        source = inspect.getsource(simulation.run_mission20_robustness_report_check)
        source += inspect.getsource(simulation._build_mission20_data)
        self.assertNotIn('_simulate_local_objective', source)
        self.assertNotIn('simul.simulate', source)
        self.assertNotIn('requests.', source)

    def test_window_uses_remote_wrapper_and_shared_report_builder(self):
        source = (CODE_DIR / 'window.py').read_text()
        self.assertIn('run_mission20_robustness_report_check_remote(BACKEND_URL, self.results)', source)
        self.assertIn('return build_mission20_context_report_text(report_data)', source)

    def test_mission_ui_has_progression_idempotence_and_direct_answer_guards(self):
        source = (CODE_DIR / 'mission20.py').read_text()
        self.assertIn('is_mission20_unlocked', source)
        self.assertIn("if '20' in self.missions_activated", source)
        self.assertIn('initialise_mission20_context_matrix', source)
        self.assertIn('normalise_mission20_answer', source)
        self.assertIn('mission20_answer_matches', source)
        self.assertIn('Complete all four oxygen-by-acetate matrix runs', source)

    def test_old_pyruvate_recipe_and_threshold_are_absent_from_mission20_code(self):
        source = inspect.getsource(simulation._build_mission20_data)
        source += (CODE_DIR / 'mission20.py').read_text()
        self.assertNotIn('EX_pyr_e', source)
        self.assertNotIn('growth >= 1.0', source)
        self.assertNotIn('MISSION20_MIN_GROWTH', source)

    def test_full_complete_state_is_json_serialisable(self):
        report = self._complete()
        json.dumps(report)

    def test_independent_pfba_values_for_all_four_matrix_cells(self):
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

        def controlled_bounds(oxygen_closed, acetate_closed):
            current_bounds = list(bounds)
            if oxygen_closed:
                index = reaction_index['R_EX_o2_e']
                current_bounds[index] = (0.0, current_bounds[index][1])
            if acetate_closed:
                index = reaction_index['R_EX_ac_e']
                current_bounds[index] = (current_bounds[index][0], 0.0)
            return current_bounds

        def primary_solution(current_bounds):
            objective = np.zeros(len(reactions))
            objective[biomass_index] = -1.0
            primary = linprog(
                objective,
                A_eq=matrix,
                b_eq=np.zeros(len(species)),
                bounds=current_bounds,
                method='highs',
            )
            self.assertTrue(primary.success)
            return primary

        def solve(oxygen_closed, acetate_closed):
            current_bounds = controlled_bounds(oxygen_closed, acetate_closed)

            primary = primary_solution(current_bounds)
            optimum = primary.x[biomass_index]

            count = len(reactions)
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
            inequality_rhs = np.zeros(count * 2)
            pfba = linprog(
                pfba_objective,
                A_ub=inequalities,
                b_ub=inequality_rhs,
                A_eq=equality,
                b_eq=equality_rhs,
                bounds=current_bounds + [(0.0, None)] * count,
                method='highs',
            )
            self.assertTrue(pfba.success)
            fluxes = pfba.x[:count]
            active_count = sum(abs(float(value)) > 1e-7 for value in fluxes)
            return optimum, fluxes, float(sum(abs(float(value)) for value in fluxes)), active_count

        expected = {
            (False, False): (self.AEROBIC_GROWTH, self.AEROBIC_PROFILE, self.AEROBIC_TOTAL, 48),
            (False, True): (self.AEROBIC_GROWTH, self.AEROBIC_PROFILE, self.AEROBIC_TOTAL, 48),
            (True, False): (self.ANAEROBIC_GROWTH, self.ANAEROBIC_PROFILE, self.ANAEROBIC_TOTAL, 47),
            (True, True): (
                self.ANAEROBIC_CLOSED_GROWTH,
                self.ANAEROBIC_CLOSED_PROFILE,
                self.ANAEROBIC_CLOSED_TOTAL,
                46,
            ),
        }
        for combination, (expected_growth, expected_profile, expected_total, expected_active) in expected.items():
            with self.subTest(combination=combination):
                growth, fluxes, total, active_count = solve(*combination)
                self.assertAlmostEqual(growth, expected_growth, delta=1e-6)
                self.assertAlmostEqual(total, expected_total, delta=1e-3)
                self.assertEqual(active_count, expected_active)
                for reaction_id, expected_value in expected_profile.items():
                    self.assertAlmostEqual(
                        fluxes[reaction_index[f'R_{reaction_id}']],
                        expected_value,
                        delta=1e-5,
                    )

        # FVA-style checks at maximum biomass confirm that acetate export is
        # fixed at zero with oxygen available and fixed at a positive value
        # after oxygen uptake is closed.  The contextual difference therefore
        # does not depend on an arbitrary pFBA optimum.
        acetate_index = reaction_index['R_EX_ac_e']
        for oxygen_closed, expected_acetate in (
            (False, 0.0),
            (True, self.ANAEROBIC_PROFILE['EX_ac_e']),
        ):
            with self.subTest(fva_oxygen_closed=oxygen_closed):
                current_bounds = controlled_bounds(oxygen_closed, False)
                primary = primary_solution(current_bounds)
                optimum = primary.x[biomass_index]
                fva_bounds = list(current_bounds)
                fva_bounds[biomass_index] = (optimum - 1e-8, optimum + 1e-8)
                for direction in (1.0, -1.0):
                    objective = np.zeros(len(reactions))
                    objective[acetate_index] = direction
                    result = linprog(
                        objective,
                        A_eq=matrix,
                        b_eq=np.zeros(len(species)),
                        bounds=fva_bounds,
                        method='highs',
                    )
                    self.assertTrue(result.success)
                    self.assertAlmostEqual(
                        float(result.x[acetate_index]),
                        expected_acetate,
                        delta=1e-5,
                    )

    def test_backend_pfba_matches_visible_contract_when_dependencies_exist(self):
        backend_dir = PROJECT_ROOT / 'backend'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        try:
            from app.schemas import SimulateRequest
            from app.simulator import simulate as backend_simulate
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'Backend MEWpy/COBRApy unavailable: {exc}')

        for oxygen_closed, acetate_closed in ((False, False), (False, True), (True, False), (True, True)):
            reactions = self._reactions(oxygen_closed, acetate_closed)
            env_conditions = simulation._build_envconditions_from_reactions(reactions, simulation.REACTIONS)
            response = backend_simulate(SimulateRequest(
                method=simulation.MISSION20_TARGET_METHOD,
                objective=simulation.MISSION20_GROWTH_OBJECTIVE,
                gene_knockouts=[],
                env_conditions=env_conditions,
            ))
            self.assertEqual(response.status, 'ok', response.message)
            expected_growth, expected_profile, expected_total, expected_active, _ = self._values(
                oxygen_closed, acetate_closed
            )
            self.assertAlmostEqual(float(response.primary_objective_flux), expected_growth, delta=1e-3)
            self.assertEqual(response.method_score_name, simulation.MISSION20_EXPECTED_SECONDARY_CRITERION)
            self.assertAlmostEqual(float(response.total_absolute_flux), expected_total, delta=1e-2)
            self.assertEqual(int(response.active_reaction_count), expected_active)
            for reaction_id, expected_value in expected_profile.items():
                self.assertAlmostEqual(float(response.fluxes[reaction_id]), expected_value, delta=1e-3)


if __name__ == '__main__':
    unittest.main()
