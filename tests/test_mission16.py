"""Regression tests for Mission 16 context-dependent carbon rescue.

Run from the project root with:
    python3 tests/test_mission16.py
"""
from __future__ import annotations

import inspect
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import simulation  # noqa: E402


class Mission16RegressionTests(unittest.TestCase):
    EXPECTED = {
        'EX_ac_e': {'growth': 0.173339, 'oxygen': 12.423093},
        'EX_pyr_e': {'growth': 0.291225, 'oxygen': 12.270099},
        'EX_mal__L_e': {'growth': 0.370741, 'oxygen': 13.794339},
        'EX_fum_e': {'growth': 0.370741, 'oxygen': 13.794339},
        'EX_akg_e': {'growth': 0.528755, 'oxygen': 16.887255},
    }

    def setUp(self):
        self.genes = simulation._build_active_genes_data()

    def _reactions(self, source_id, oxygen_closed=False):
        reactions = simulation._build_default_reactions_data()
        glucose_index = list(simulation.REACTIONS.index).index(simulation.MISSION16_BLOCKED_CARBON_SOURCE)
        source_index = list(simulation.REACTIONS.index).index(source_id)
        oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION16_OXYGEN_REACTION)
        reactions[f'reaction_{glucose_index}_lb'] = False
        reactions[f'reaction_{source_index}_lb'] = True
        if oxygen_closed:
            reactions[f'reaction_{oxygen_index}_lb'] = False
        return reactions

    def _medium(self, source_id, oxygen_uptake=None, source_uptake=10.0, missing=None):
        oxygen_uptake = self.EXPECTED[source_id]['oxygen'] if oxygen_uptake is None else oxygen_uptake
        missing = set(missing or [])
        items = []
        for reaction_id in simulation.MISSION16_REQUIRED_MEDIUM_FLUXES:
            if reaction_id in missing:
                continue
            if reaction_id == simulation.MISSION16_BLOCKED_CARBON_SOURCE:
                raw = 0.0
            elif reaction_id == source_id:
                raw = -float(source_uptake)
            elif reaction_id == simulation.MISSION16_OXYGEN_REACTION:
                raw = -float(oxygen_uptake)
            else:
                raw = 0.0
            items.append({
                'reaction_id': reaction_id,
                'raw_flux': raw,
                'uptake_flux': max(-raw, 0.0),
                'secretion_flux': max(raw, 0.0),
            })
        return {'items': items}

    def _record(
        self,
        source_id,
        report=None,
        oxygen_closed=False,
        result=None,
        medium=None,
        method=None,
        objective=None,
        genes=None,
        reactions=None,
        error=None,
    ):
        if result is None:
            result = (
                'Status: INFEASIBLE'
                if oxygen_closed
                else self.EXPECTED[source_id]['growth']
            )
        if medium is None:
            medium = (
                {'error': 'Simulation infeasible. Medium fluxes could not be measured.'}
                if oxygen_closed and 'INFEASIBLE' in str(result).upper()
                else self._medium(source_id)
            )
        with patch.object(simulation, 'save_mission16_medium_report_check'):
            return simulation._build_mission16_data(
                method or simulation.MISSION16_METHOD,
                objective or simulation.MISSION16_GROWTH_OBJECTIVE,
                result,
                dict(genes or self.genes),
                dict(reactions or self._reactions(source_id, oxygen_closed=oxygen_closed)),
                medium_fluxes=medium,
                existing_report=report,
                objective_error=error,
            )

    def _complete_screen(self, order=None):
        report = None
        for source_id in order or simulation.MISSION16_CANDIDATE_CARBON_SOURCES:
            report = self._record(source_id, report=report)
        return report

    def _complete_mission_evidence(self):
        report = self._complete_screen()
        return self._record(
            simulation.MISSION16_EXPECTED_STRONGEST_SOURCE,
            report=report,
            oxygen_closed=True,
        )

    def test_progression_and_redesign_constants(self):
        self.assertFalse(simulation.is_mission16_unlocked([]))
        self.assertFalse(simulation.is_mission16_unlocked(['14']))
        self.assertTrue(simulation.is_mission16_unlocked(['15']))
        self.assertEqual(simulation.MISSION16_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION16_METHOD, 'FBA')
        self.assertEqual(simulation.MISSION16_GROWTH_OBJECTIVE, 'BIOMASS_Ecoli_core_w_GAM')
        self.assertEqual(simulation.MISSION16_EXPECTED_STRONGEST_SOURCE, 'EX_akg_e')
        self.assertEqual(simulation.MISSION16_EXPECTED_FACTOR, 'oxygen')
        self.assertFalse(hasattr(simulation, 'MISSION16_MIN_GROWTH'))

    def test_environment_reader_is_order_independent_and_legacy_compatible(self):
        reactions = self._reactions('EX_akg_e')
        status = simulation._mission16_environment_status(reactions)
        self.assertTrue(status['bounds_complete'])
        self.assertTrue(status['glucose_lower_bound_closed'])
        self.assertFalse(status['oxygen_lower_bound_closed'])
        self.assertEqual(status['selected_sources'], ['EX_akg_e'])
        self.assertEqual(status['unexpected_environment_changes'], [])

        reordered = dict(reversed(list(reactions.items())))
        self.assertEqual(simulation._mission16_environment_status(reordered), status)

        legacy = {f'widget_{i}': value for i, value in enumerate(reactions.values())}
        legacy_status = simulation._mission16_environment_status(legacy)
        self.assertTrue(legacy_status['bounds_complete'])
        self.assertEqual(legacy_status['selected_sources'], ['EX_akg_e'])

    def test_incomplete_explicit_bounds_are_rejected(self):
        reactions = self._reactions('EX_akg_e')
        reactions.pop('reaction_0_ub')
        status = simulation._mission16_environment_status(reactions)
        self.assertFalse(status['bounds_complete'])
        report = self._record('EX_akg_e', reactions=reactions)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('environmental-bound payload is incomplete', ' '.join(report['current_issues']))

    def test_each_aerobic_candidate_records_expected_visible_values(self):
        for source_id, expected in self.EXPECTED.items():
            report = self._record(source_id)
            self.assertTrue(report['current_run_valid'], (source_id, report['current_issues']))
            trial = report['candidate_trials'][source_id]
            self.assertAlmostEqual(trial['growth'], expected['growth'], delta=1e-6)
            self.assertAlmostEqual(trial['source_uptake'], 10.0, delta=1e-6)
            self.assertAlmostEqual(trial['glucose_uptake'], 0.0, delta=1e-6)
            self.assertAlmostEqual(trial['oxygen_uptake'], expected['oxygen'], delta=1e-6)

    def test_complete_screen_derives_ranking_and_unique_strongest_source(self):
        report = self._complete_screen()
        self.assertTrue(report['aerobic_screen_complete'])
        self.assertEqual(report['valid_trial_count'], 5)
        self.assertEqual(report['missing_candidates'], [])
        self.assertEqual(report['strongest_candidate'], 'EX_akg_e')
        self.assertTrue(report['expected_strongest_confirmed'])
        self.assertAlmostEqual(report['strongest_growth'], 0.528755, delta=1e-6)
        ranked = [row['source_id'] for row in report['ranked_candidates']]
        self.assertEqual(ranked[0], 'EX_akg_e')
        self.assertEqual(set(ranked[1:3]), {'EX_mal__L_e', 'EX_fum_e'})
        self.assertFalse(report['evidence_ready'])

    def test_screen_order_is_irrelevant_and_repeated_trial_updates_without_duplication(self):
        order = list(reversed(simulation.MISSION16_CANDIDATE_CARBON_SOURCES))
        report = self._complete_screen(order=order)
        self.assertEqual(report['strongest_candidate'], 'EX_akg_e')
        repeated = self._record('EX_ac_e', report=report)
        self.assertEqual(repeated['valid_trial_count'], 5)
        self.assertEqual(len(repeated['candidate_trials']), 5)

    def test_one_run_cannot_complete_screen(self):
        report = self._record('EX_akg_e')
        self.assertFalse(report['aerobic_screen_complete'])
        self.assertEqual(report['valid_trial_count'], 1)
        self.assertEqual(len(report['missing_candidates']), 4)

    def test_wrong_method_objective_or_knockout_is_rejected(self):
        wrong_method = self._record('EX_akg_e', method='pFBA')
        self.assertFalse(wrong_method['current_run_valid'])
        wrong_objective = self._record('EX_akg_e', objective='EX_succ_e')
        self.assertFalse(wrong_objective['current_run_valid'])
        genes = dict(self.genes)
        genes[next(iter(genes))] = False
        wrong_gene = self._record('EX_akg_e', genes=genes)
        self.assertFalse(wrong_gene['current_run_valid'])

    def test_medium_values_must_be_present_and_source_protocol_must_be_common(self):
        missing = self._record(
            'EX_akg_e',
            medium=self._medium('EX_akg_e', missing=['EX_glc__D_e']),
        )
        self.assertFalse(missing['current_run_valid'])
        self.assertIn('missing required Mission 16 reactions', ' '.join(missing['current_issues']))

        weak = self._record(
            'EX_akg_e',
            medium=self._medium('EX_akg_e', source_uptake=1.0),
        )
        self.assertFalse(weak['current_run_valid'])
        self.assertIn('-10 uptake protocol', ' '.join(weak['current_issues']))

    def test_unrelated_environment_change_is_rejected(self):
        reactions = self._reactions('EX_akg_e')
        phosphate_index = list(simulation.REACTIONS.index).index('EX_pi_e')
        reactions[f'reaction_{phosphate_index}_lb'] = False
        report = self._record('EX_akg_e', reactions=reactions)
        self.assertFalse(report['current_run_valid'])
        self.assertTrue(report['current_unexpected_environment_changes'])

    def test_oxygen_challenge_requires_completed_screen_and_strongest_source(self):
        early = self._record('EX_akg_e', oxygen_closed=True)
        self.assertFalse(early['current_run_valid'])
        self.assertIn('Complete the five-source aerobic screen', ' '.join(early['current_issues']))

        complete = self._complete_screen()
        wrong = self._record('EX_ac_e', report=complete, oxygen_closed=True)
        self.assertFalse(wrong['current_run_valid'])
        self.assertIn('uniquely strongest aerobic source', ' '.join(wrong['current_issues']))

    def test_visible_infeasible_challenge_completes_evidence(self):
        report = self._complete_mission_evidence()
        self.assertTrue(report['current_run_valid'])
        self.assertTrue(report['current_run_recorded'])
        self.assertEqual(report['oxygen_challenge_run']['status'], 'infeasible')
        self.assertTrue(report['oxygen_challenge_infeasible'])
        self.assertTrue(report['relationship_supported'])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['ready_to_deliver'])

    def test_feasible_challenge_is_recorded_but_does_not_support_expected_relation(self):
        complete = self._complete_screen()
        report = self._record(
            'EX_akg_e',
            report=complete,
            oxygen_closed=True,
            result=0.05,
            medium=self._medium('EX_akg_e', oxygen_uptake=0.0),
        )
        self.assertTrue(report['current_run_valid'])
        self.assertEqual(report['oxygen_challenge_run']['status'], 'feasible')
        self.assertTrue(report['evidence_ready'])
        self.assertFalse(report['relationship_supported'])
        self.assertFalse(report['ready_to_deliver'])

    def test_invalid_attempt_preserves_complete_evidence(self):
        complete = self._complete_mission_evidence()
        invalid = self._record('EX_akg_e', report=complete, method='pFBA')
        self.assertFalse(invalid['current_run_recorded'])
        self.assertTrue(invalid['aerobic_screen_complete'])
        self.assertTrue(invalid['oxygen_challenge_recorded'])
        self.assertTrue(invalid['evidence_ready'])
        text = simulation.build_mission16_context_report_text(invalid)
        self.assertIn('Latest run was not recorded', text)
        self.assertIn('Previously valid Mission 16 evidence remains available', text)

    def test_direct_factor_answers_are_easy_to_enter_but_still_evidence_gated(self):
        complete = self._complete_mission_evidence()
        for answer in ('oxygen', 'O2', 'EX_o2_e', 'oxygen availability', 'oxygen uptake', 'oxygen supply', 'oxygen/O2', 'O2 availability', 'oxigénio'):
            self.assertEqual(simulation.normalise_mission16_answer(answer), 'oxygen')
            self.assertTrue(simulation.mission16_answer_matches(answer, complete), answer)
        for answer in ('infeasible', 'carbon', '2-oxoglutarate', 'growth', 'nitrogen'):
            self.assertIsNone(simulation.normalise_mission16_answer(answer), answer)
            self.assertFalse(simulation.mission16_answer_matches(answer, complete), answer)
        self.assertFalse(simulation.mission16_answer_matches('oxygen', self._complete_screen()))

    def test_report_provides_evidence_and_direct_question_without_printing_answer(self):
        report = self._complete_mission_evidence()
        text = simulation.build_mission16_context_report_text(report)
        self.assertIn('Candidate trials recorded: 5/5', text)
        self.assertIn('Visible solver status: INFEASIBLE', text)
        self.assertIn('Which removed environmental factor', text)
        self.assertNotIn('Answer: oxygen', text)
        self.assertNotIn('The rescue depends on oxygen', text)
        self.assertIn('equal molar', text)
        self.assertIn('not a universal', text)

    def test_remote_wrapper_uses_visible_result_only_and_state_is_json_serialisable(self):
        report = self._complete_mission_evidence()
        json.dumps(report)
        source = inspect.getsource(simulation.run_mission16_medium_report_check_remote)
        self.assertNotIn('_http_post_json', source)
        self.assertIn('run_mission16_medium_report_check(simulation_results)', source)
        builder_source = inspect.getsource(simulation._build_mission16_data)
        self.assertNotIn('.simulate(', builder_source)
        self.assertNotIn('_simulate_', builder_source)

    def test_ui_has_progression_guard_idempotent_activation_and_short_answer(self):
        source = (CODE_DIR / 'mission16.py').read_text(encoding='utf-8')
        self.assertIn('is_mission16_unlocked', source)
        self.assertIn('initialise_mission16_context_rescue()', source)
        self.assertIn("if '16' in self.missions_activated", source)
        self.assertIn('Environmental factor:', source)
        self.assertIn('mission16_answer_matches', source)
        self.assertNotIn('MISSION16_MIN_GROWTH', source)
        window = (CODE_DIR / 'window.py').read_text(encoding='utf-8')
        self.assertIn('run_mission16_medium_report_check_remote', window)
        self.assertIn('build_mission16_context_report_text', window)

    def test_documentation_matches_context_dependent_redesign(self):
        mission_doc = (PROJECT_ROOT / 'data' / 'missions' / 'mission16.md').read_text(encoding='utf-8')
        self.assertIn('Context-Dependent Carbon Rescue', mission_doc)
        self.assertIn('Status: INFEASIBLE', mission_doc)
        self.assertIn('Which removed environmental factor', mission_doc)
        overview = (PROJECT_ROOT / 'MISSION_PROGRESS_OVERVIEW.md').read_text(encoding='utf-8')
        self.assertIn('Mission 16 — Context-Dependent Carbon Rescue', overview)

    def test_real_fba_values_for_five_sources_and_infeasible_challenge(self):
        for source_id, expected in self.EXPECTED.items():
            result, _production, medium = simulation._simulate_local_objective_with_production_fluxes(
                simulation.MISSION16_METHOD,
                simulation.MISSION16_GROWTH_OBJECTIVE,
                dict(self.genes),
                self._reactions(source_id),
                [],
            )
            self.assertAlmostEqual(float(result), expected['growth'], delta=1e-3, msg=source_id)
            _, uptake, _ = simulation._medium_flux_maps(medium)
            self.assertAlmostEqual(uptake[source_id], 10.0, delta=1e-3, msg=source_id)
            self.assertAlmostEqual(uptake[simulation.MISSION16_BLOCKED_CARBON_SOURCE], 0.0, delta=1e-3)
            self.assertAlmostEqual(uptake[simulation.MISSION16_OXYGEN_REACTION], expected['oxygen'], delta=1e-3)

        result, production, medium = simulation._simulate_local_objective_with_production_fluxes(
            simulation.MISSION16_METHOD,
            simulation.MISSION16_GROWTH_OBJECTIVE,
            dict(self.genes),
            self._reactions('EX_akg_e', oxygen_closed=True),
            [],
        )
        self.assertEqual(result, 'Status: INFEASIBLE')
        self.assertIn('infeasible', production.get('error', '').lower())
        self.assertIn('infeasible', medium.get('error', '').lower())


if __name__ == '__main__':
    unittest.main()
