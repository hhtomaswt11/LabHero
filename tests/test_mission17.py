"""Regression tests for Mission 17 essential uptake routes.

Run from the project root with:
    python3 tests/test_mission17.py
"""
from __future__ import annotations

import inspect
import json
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import simulation  # noqa: E402


class Mission17RegressionTests(unittest.TestCase):
    BASELINE_GROWTH = 0.873921507
    BASELINE_RAW = {
        'EX_glc__D_e': -10.0,
        'EX_nh4_e': -4.765319193,
        'EX_pi_e': -3.214895048,
        'EX_h2o_e': 29.175827136,
        'EX_h_e': 17.530865430,
        'EX_co2_e': 22.809833310,
        'EX_o2_e': -21.799492656,
    }
    TRIAL_GROWTH = {
        'EX_nh4_e': 0.0,
        'EX_pi_e': 0.0,
        'EX_h2o_e': BASELINE_GROWTH,
        'EX_h_e': BASELINE_GROWTH,
        'EX_co2_e': BASELINE_GROWTH,
    }

    def setUp(self):
        self.genes = simulation._build_active_genes_data()

    def _reactions(self, closed=None):
        reactions = simulation._build_default_reactions_data()
        if closed:
            index = list(simulation.REACTIONS.index).index(closed)
            reactions[f'reaction_{index}_lb'] = False
        return reactions

    def _trial_raw(self, closed=None):
        if closed in ('EX_nh4_e', 'EX_pi_e'):
            return {
                'EX_glc__D_e': -0.645384615,
                'EX_nh4_e': 0.0,
                'EX_pi_e': 0.0,
                'EX_h2o_e': 3.872307692,
                'EX_h_e': 0.0,
                'EX_co2_e': 3.872307692,
                'EX_o2_e': -3.872307692,
            }
        return dict(self.BASELINE_RAW)

    def _medium(self, closed=None, missing=None, selected_uptake_override=None):
        missing = set(missing or [])
        raw_values = self._trial_raw(closed)
        items = []
        for reaction_id in simulation.MISSION17_REQUIRED_MEDIUM_FLUXES:
            if reaction_id in missing:
                continue
            raw = float(raw_values[reaction_id])
            if reaction_id == closed and selected_uptake_override is not None:
                raw = -float(selected_uptake_override)
            items.append({
                'reaction_id': reaction_id,
                'raw_flux': raw,
                'uptake_flux': max(-raw, 0.0),
                'secretion_flux': max(raw, 0.0),
            })
        return {'items': items}

    def _record(
        self,
        closed=None,
        report=None,
        result=None,
        medium=None,
        method=None,
        objective=None,
        genes=None,
        reactions=None,
        error=None,
    ):
        if result is None:
            result = self.BASELINE_GROWTH if closed is None else self.TRIAL_GROWTH[closed]
        if medium is None:
            medium = self._medium(closed)
        with patch.object(simulation, 'save_mission17_essential_medium_check'):
            return simulation._build_mission17_data(
                method or simulation.MISSION17_METHOD,
                objective or simulation.MISSION17_GROWTH_OBJECTIVE,
                result,
                dict(genes or self.genes),
                dict(reactions or self._reactions(closed)),
                medium_fluxes=medium,
                existing_report=report,
                objective_error=error,
            )

    def _baseline(self):
        return self._record()

    def _complete_screen(self, order=None):
        report = self._baseline()
        for reaction_id in order or simulation.MISSION17_CANDIDATE_NUTRIENTS:
            report = self._record(reaction_id, report=report)
        return report

    def test_progression_and_redesign_constants(self):
        self.assertFalse(simulation.is_mission17_unlocked([]))
        self.assertFalse(simulation.is_mission17_unlocked(['15']))
        self.assertTrue(simulation.is_mission17_unlocked(['16']))
        self.assertEqual(simulation.MISSION17_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION17_METHOD, 'FBA')
        self.assertEqual(simulation.MISSION17_GROWTH_OBJECTIVE, 'BIOMASS_Ecoli_core_w_GAM')
        self.assertAlmostEqual(simulation.MISSION17_COLLAPSE_RATIO, 0.01)
        self.assertAlmostEqual(simulation.MISSION17_PRESERVED_RATIO, 0.99)
        self.assertFalse(hasattr(simulation, 'MISSION17_MAX_GROWTH'))
        self.assertLess(simulation.MISSION17_MIN_BASELINE_GROWTH, 1.0)

    def test_environment_reader_is_order_independent_and_legacy_compatible(self):
        reactions = self._reactions('EX_pi_e')
        status = simulation._mission17_environment_status(reactions)
        self.assertTrue(status['bounds_complete'])
        self.assertEqual(status['closed_candidate_nutrients'], ['EX_pi_e'])
        self.assertEqual(status['unexpected_environment_changes'], [])

        reordered = dict(reversed(list(reactions.items())))
        self.assertEqual(simulation._mission17_environment_status(reordered), status)

        legacy = {f'widget_{i}': value for i, value in enumerate(reactions.values())}
        legacy_status = simulation._mission17_environment_status(legacy)
        self.assertTrue(legacy_status['bounds_complete'])
        self.assertEqual(legacy_status['closed_candidate_nutrients'], ['EX_pi_e'])

    def test_incomplete_explicit_bounds_are_rejected(self):
        reactions = self._reactions()
        reactions.pop('reaction_0_ub')
        report = self._record(reactions=reactions)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('environmental-bound payload is incomplete', ' '.join(report['current_issues']))

    def test_baseline_records_growth_and_signed_exchange_directions(self):
        report = self._baseline()
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertTrue(report['baseline_ready'])
        baseline = report['baseline_run']
        self.assertAlmostEqual(baseline['growth'], self.BASELINE_GROWTH, delta=1e-6)
        self.assertEqual(baseline['candidate_directions']['EX_nh4_e'], 'uptake')
        self.assertEqual(baseline['candidate_directions']['EX_pi_e'], 'uptake')
        self.assertEqual(baseline['candidate_directions']['EX_h2o_e'], 'secretion')
        self.assertEqual(baseline['candidate_directions']['EX_h_e'], 'secretion')
        self.assertEqual(baseline['candidate_directions']['EX_co2_e'], 'secretion')

    def test_candidate_trial_before_baseline_is_rejected(self):
        report = self._record('EX_nh4_e')
        self.assertFalse(report['current_run_valid'])
        self.assertIn('default-medium baseline', ' '.join(report['current_issues']))
        self.assertEqual(report['candidate_trials'], {})

    def test_all_five_candidate_trials_record_visible_growth_and_blocked_uptake(self):
        report = self._baseline()
        for reaction_id, expected_growth in self.TRIAL_GROWTH.items():
            report = self._record(reaction_id, report=report)
            self.assertTrue(report['current_run_valid'], (reaction_id, report['current_issues']))
            trial = report['candidate_trials'][reaction_id]
            self.assertAlmostEqual(trial['growth'], expected_growth, delta=1e-6)
            self.assertAlmostEqual(trial['closed_route_uptake'], 0.0, delta=1e-6)

    def test_complete_screen_derives_two_collapses_and_three_preserved_trials(self):
        report = self._complete_screen()
        self.assertTrue(report['screen_complete'])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['relationship_supported'])
        self.assertEqual(report['valid_trial_count'], 5)
        self.assertEqual(set(report['collapse_candidates']), {'EX_nh4_e', 'EX_pi_e'})
        self.assertEqual(set(report['preserved_growth_candidates']), {'EX_h2o_e', 'EX_h_e', 'EX_co2_e'})
        self.assertEqual(report['intermediate_candidates'], [])

    def test_screen_order_is_irrelevant_and_repeated_trial_updates_without_duplication(self):
        report = self._complete_screen(order=list(reversed(simulation.MISSION17_CANDIDATE_NUTRIENTS)))
        self.assertEqual(set(report['collapse_candidates']), {'EX_nh4_e', 'EX_pi_e'})
        repeated = self._record('EX_co2_e', report=report)
        self.assertEqual(repeated['valid_trial_count'], 5)
        self.assertEqual(len(repeated['candidate_trials']), 5)

    def test_wrong_method_objective_or_knockout_is_rejected(self):
        baseline = self._baseline()
        self.assertFalse(self._record('EX_nh4_e', report=baseline, method='pFBA')['current_run_valid'])
        self.assertFalse(self._record('EX_nh4_e', report=baseline, objective='EX_succ_e')['current_run_valid'])
        genes = dict(self.genes)
        genes[next(iter(genes))] = False
        self.assertFalse(self._record('EX_nh4_e', report=baseline, genes=genes)['current_run_valid'])

    def test_multiple_or_unrelated_environment_changes_are_rejected(self):
        baseline = self._baseline()
        reactions = self._reactions('EX_nh4_e')
        pi_index = list(simulation.REACTIONS.index).index('EX_pi_e')
        reactions[f'reaction_{pi_index}_lb'] = False
        multiple = self._record('EX_nh4_e', report=baseline, reactions=reactions)
        self.assertFalse(multiple['current_run_valid'])
        self.assertIn('exactly one', ' '.join(multiple['current_issues']))

        reactions = self._reactions('EX_nh4_e')
        oxygen_index = list(simulation.REACTIONS.index).index('EX_o2_e')
        reactions[f'reaction_{oxygen_index}_lb'] = False
        extra = self._record('EX_nh4_e', report=baseline, reactions=reactions)
        self.assertFalse(extra['current_run_valid'])
        self.assertIn('unrelated environmental bound', ' '.join(extra['current_issues']))

    def test_medium_report_is_mandatory_and_missing_flux_is_not_zero(self):
        baseline = self._record(medium=self._medium(missing=['EX_pi_e']))
        self.assertFalse(baseline['current_run_valid'])
        self.assertIn('missing required Mission 17 reactions', ' '.join(baseline['current_issues']))

        valid_baseline = self._baseline()
        trial = self._record(
            'EX_pi_e',
            report=valid_baseline,
            medium=self._medium('EX_pi_e', missing=['EX_pi_e']),
        )
        self.assertFalse(trial['current_run_valid'])
        self.assertIsNone(trial['current_selected_uptake'])

    def test_closed_route_must_have_numeric_zero_uptake(self):
        baseline = self._baseline()
        report = self._record(
            'EX_pi_e',
            report=baseline,
            medium=self._medium('EX_pi_e', selected_uptake_override=0.5),
        )
        self.assertFalse(report['current_run_valid'])
        self.assertIn('did not block uptake', ' '.join(report['current_issues']))

    def test_invalid_attempt_preserves_complete_evidence(self):
        complete = self._complete_screen()
        invalid = self._record('EX_nh4_e', report=complete, method='pFBA')
        self.assertFalse(invalid['current_run_recorded'])
        self.assertTrue(invalid['baseline_ready'])
        self.assertTrue(invalid['screen_complete'])
        self.assertTrue(invalid['evidence_ready'])
        text = simulation.build_mission17_essential_routes_report_text(invalid)
        self.assertIn('Latest run was not recorded', text)
        self.assertIn('Previously valid Mission 17 evidence remains available', text)

    def test_short_two_route_answers_are_accepted_in_either_order(self):
        report = self._complete_screen()
        accepted = (
            'EX_nh4_e and EX_pi_e',
            'EX_pi_e, EX_nh4_e',
            'nh4 and pi',
            'ammonia and phosphate',
            'ammonium + phosphate',
            'fosfato e amónio',
        )
        for answer in accepted:
            self.assertTrue(simulation.mission17_answer_matches(answer, report), answer)

        rejected = (
            'phosphate',
            'ammonium',
            'water and phosphate',
            'oxygen',
            'all candidates',
            'ammonium phosphate water',
        )
        for answer in rejected:
            self.assertFalse(simulation.mission17_answer_matches(answer, report), answer)
        self.assertFalse(simulation.mission17_answer_matches('nh4 and pi', self._baseline()))

    def test_single_letter_proton_alias_cannot_be_silently_ignored(self):
        report = self._complete_screen()
        for answer in ('h pi nh4', 'H nh4 pi', 'nh4 + pi + h', 'h+ pi nh4'):
            self.assertEqual(
                set(simulation.normalise_mission17_answer(answer)),
                {'EX_nh4_e', 'EX_pi_e', 'EX_h_e'},
                answer,
            )
            self.assertFalse(simulation.mission17_answer_matches(answer, report), answer)

        # Natural wording with only the two evidence-supported routes remains valid.
        self.assertTrue(
            simulation.mission17_answer_matches(
                'I think ammonium and phosphate are the required uptake routes',
                report,
            )
        )

    def test_report_presents_evidence_without_printing_the_answer_pair(self):
        report = self._complete_screen()
        text = simulation.build_mission17_essential_routes_report_text(report)
        self.assertIn('Baseline predicted growth rate: 0.874 h^-1', text)
        self.assertIn('Candidate trials recorded: 5/5', text)
        self.assertIn('Trials at or below 1.0% of baseline growth: 2', text)
        self.assertIn('Which two candidate uptake routes', text)
        self.assertNotIn('Answer: EX_nh4_e and EX_pi_e', text)
        self.assertNotIn('Ammonium and Phosphate are required', text)
        self.assertIn('negative = uptake', text)
        self.assertIn('positive = secretion', text)

    def test_negative_zero_is_normalised_in_state_and_existing_reports(self):
        baseline = self._baseline()
        report = self._record('EX_pi_e', report=baseline, result=-0.0)
        trial = report['candidate_trials']['EX_pi_e']

        self.assertEqual(trial['growth'], 0.0)
        self.assertEqual(trial['closed_route_raw_flux'], 0.0)
        self.assertEqual(trial['closed_route_uptake'], 0.0)
        self.assertEqual(math.copysign(1.0, trial['growth']), 1.0)
        self.assertEqual(math.copysign(1.0, trial['closed_route_uptake']), 1.0)

        # Old saves may already contain IEEE negative zero. The report builder
        # must still clean those values without requiring the mission to be run
        # again.
        trial['growth'] = -0.0
        trial['closed_route_uptake'] = -0.0
        text = simulation.build_mission17_essential_routes_report_text(report)
        self.assertNotIn('predicted growth rate -0.000', text)
        self.assertNotIn('closed-route uptake -0.000', text)
        self.assertIn('predicted growth rate 0.000 h^-1', text)
        self.assertIn('closed-route uptake 0.000', text)

    def test_solver_and_web_contract_normalise_negative_zero(self):
        class NegativeZeroResult:
            def __str__(self):
                return 'Objective: -0.0001\nStatus: OPTIMAL'

        value = simulation._normalise_result(NegativeZeroResult())
        self.assertEqual(value, 0.0)
        self.assertEqual(math.copysign(1.0, value), 1.0)

        backend_source = (
            PROJECT_ROOT / 'backend' / 'app' / 'simulator.py'
        ).read_text(encoding='utf-8')
        self.assertIn('def _clean_numeric', backend_source)
        self.assertIn('result=_clean_numeric(primary_objective_flux, 3)', backend_source)
        self.assertIn('clean_fluxes[str(reaction_id)] = _clean_numeric(value, 6)', backend_source)

    def test_remote_wrapper_uses_visible_result_only_and_state_is_json_serialisable(self):
        report = self._complete_screen()
        json.dumps(report)
        source = inspect.getsource(simulation.run_mission17_essential_medium_check_remote)
        self.assertNotIn('_http_post_json', source)
        self.assertIn('run_mission17_essential_medium_check(simulation_results)', source)
        builder = inspect.getsource(simulation._build_mission17_data)
        self.assertNotIn('.simulate(', builder)
        self.assertNotIn('_simulate_', builder)

    def test_ui_has_progression_guard_idempotent_activation_and_direct_answer_field(self):
        source = (CODE_DIR / 'mission17.py').read_text(encoding='utf-8')
        self.assertIn('is_mission17_unlocked', source)
        self.assertIn('initialise_mission17_essential_routes()', source)
        self.assertIn("if '17' in self.missions_activated", source)
        self.assertIn('Required uptake routes:', source)
        self.assertIn('mission17_answer_matches', source)
        self.assertNotIn('Target concept: phosphate', source)
        window = (CODE_DIR / 'window.py').read_text(encoding='utf-8')
        self.assertIn('run_mission17_essential_medium_check_remote', window)
        self.assertIn('build_mission17_essential_routes_report_text', window)

    def test_documentation_matches_reconstruction(self):
        mission_doc = (PROJECT_ROOT / 'data' / 'missions' / 'mission17.md').read_text(encoding='utf-8')
        self.assertIn('Essential Uptake Routes', mission_doc)
        self.assertIn('signed exchange flux', mission_doc)
        self.assertIn('Which two candidate uptake routes', mission_doc)

    def test_real_fba_values_for_baseline_and_five_closures(self):
        try:
            result, _production, medium = simulation._simulate_local_objective_with_production_fluxes(
                simulation.MISSION17_METHOD,
                simulation.MISSION17_GROWTH_OBJECTIVE,
                dict(self.genes),
                self._reactions(),
                [],
            )
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'MEWpy/COBRApy unavailable: {exc}')

        self.assertAlmostEqual(float(result), self.BASELINE_GROWTH, delta=1e-3)
        raw, _uptake, _secretion = simulation._medium_flux_maps(medium)
        for reaction_id, expected in self.BASELINE_RAW.items():
            self.assertAlmostEqual(raw[reaction_id], expected, delta=1e-3, msg=reaction_id)

        for reaction_id, expected_growth in self.TRIAL_GROWTH.items():
            result, _production, medium = simulation._simulate_local_objective_with_production_fluxes(
                simulation.MISSION17_METHOD,
                simulation.MISSION17_GROWTH_OBJECTIVE,
                dict(self.genes),
                self._reactions(reaction_id),
                [],
            )
            self.assertAlmostEqual(float(result), expected_growth, delta=1e-3, msg=reaction_id)
            _raw, uptake, _secretion = simulation._medium_flux_maps(medium)
            self.assertAlmostEqual(uptake[reaction_id], 0.0, delta=1e-3, msg=reaction_id)


    def test_real_fva_confirms_baseline_exchange_directions(self):
        try:
            from cobra.flux_analysis import flux_variability_analysis
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'COBRApy FVA unavailable: {exc}')
        if simulation.model is None:
            self.skipTest('Desktop metabolic model unavailable in this runtime.')

        reaction_ids = list(simulation.MISSION17_CANDIDATE_NUTRIENTS)
        fva = flux_variability_analysis(
            simulation.model,
            reaction_list=reaction_ids,
            fraction_of_optimum=1.0,
        )
        for reaction_id in ('EX_nh4_e', 'EX_pi_e'):
            self.assertLess(float(fva.loc[reaction_id, 'maximum']), -simulation.MISSION17_FLUX_TOLERANCE)
        for reaction_id in ('EX_h2o_e', 'EX_h_e', 'EX_co2_e'):
            self.assertGreater(float(fva.loc[reaction_id, 'minimum']), simulation.MISSION17_FLUX_TOLERANCE)


if __name__ == '__main__':
    unittest.main()
