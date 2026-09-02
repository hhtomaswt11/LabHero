"""Regression tests for Mission 02's controlled carbon-source comparison.

Run from the project root with:
    python -m unittest tests.test_mission02
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import simulation  # noqa: E402


class Mission02RegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.genes = simulation._build_active_genes_data()
        self.default_reactions = simulation._build_default_reactions_data()
        self.reaction_ids = list(simulation.REACTIONS.index)

    def _candidate_reactions(self, source_id):
        reactions = dict(self.default_reactions)
        glucose_index = self.reaction_ids.index(
            simulation.MISSION02_BLOCKED_CARBON_SOURCE
        )
        source_index = self.reaction_ids.index(source_id)
        reactions[f'reaction_{glucose_index}_lb'] = False
        reactions[f'reaction_{source_index}_lb'] = True
        return reactions

    def _simulate_candidate(self, source_id):
        reactions = self._candidate_reactions(source_id)
        simul, constraints = simulation._build_local_constraints(self.genes, reactions)
        simul.objective = simulation.MISSION02_GROWTH_OBJECTIVE
        result = simul.simulate(
            method=simulation.MISSION02_METHOD,
            constraints=constraints,
        )
        growth = simulation._as_float_or_none(simulation._normalise_result(result))
        self.assertIsNotNone(growth)

        medium_fluxes = simulation._build_medium_flux_data(
            reaction_ids=[
                simulation.MISSION02_BLOCKED_CARBON_SOURCE,
                source_id,
            ],
            flux_getter=lambda reaction_id: simulation._extract_flux(
                result,
                reaction_id,
            ),
        )
        return reactions, float(growth), medium_fluxes, constraints


    def _record_valid_trial(self, source_id, existing_report=None):
        reactions, growth, medium_fluxes, _constraints = self._simulate_candidate(
            source_id
        )
        return simulation._build_mission02_trial_data(
            simulation.MISSION02_METHOD,
            simulation.MISSION02_GROWTH_OBJECTIVE,
            growth,
            self.genes,
            reactions,
            medium_fluxes=medium_fluxes,
            existing_report=existing_report,
        )

    def test_exchange_report_covers_every_candidate(self):
        self.assertTrue(
            set(simulation.MISSION02_CANDIDATE_CARBON_SOURCES).issubset(
                set(simulation.EXCHANGE_FLUX_REPORT_REACTION_IDS)
            )
        )

    def test_each_candidate_uses_the_same_minus_ten_uptake_limit(self):
        for source_id in simulation.MISSION02_CANDIDATE_CARBON_SOURCES:
            _reactions, _growth, _medium_fluxes, constraints = self._simulate_candidate(
                source_id
            )
            self.assertEqual(
                constraints[simulation.MISSION02_BLOCKED_CARBON_SOURCE],
                (0.0, 1000.0),
            )
            self.assertEqual(
                constraints[source_id],
                (simulation.MISSION02_COMMON_UPTAKE_BOUND, 1000.0),
            )

    def test_complete_controlled_comparison_identifies_fructose(self):
        report = None
        with patch.object(simulation, 'save_mission02_source_comparison_check'):
            for source_id in simulation.MISSION02_CANDIDATE_CARBON_SOURCES:
                reactions, growth, medium_fluxes, _constraints = self._simulate_candidate(
                    source_id
                )
                report = simulation._build_mission02_trial_data(
                    simulation.MISSION02_METHOD,
                    simulation.MISSION02_GROWTH_OBJECTIVE,
                    growth,
                    self.genes,
                    reactions,
                    medium_fluxes=medium_fluxes,
                    existing_report=report,
                )
                self.assertTrue(report['current_run_valid'], report['current_issues'])

        self.assertEqual(
            report['valid_trial_count'],
            len(simulation.MISSION02_CANDIDATE_CARBON_SOURCES),
        )
        self.assertTrue(report['comparison_complete'])
        self.assertTrue(report['winner_unique'])
        self.assertEqual(report['winner_reaction'], 'EX_fru_e')
        self.assertTrue(report['expected_winner_confirmed'])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(simulation.mission02_answer_matches('Fructose', report))
        self.assertTrue(simulation.mission02_answer_matches(' fructose ', report))
        self.assertTrue(simulation.mission02_answer_matches('frutose', report))
        self.assertFalse(simulation.mission02_answer_matches('malate', report))

    def test_glucose_supplementation_is_rejected(self):
        source_id = 'EX_fru_e'
        reactions = dict(self.default_reactions)
        source_index = self.reaction_ids.index(source_id)
        reactions[f'reaction_{source_index}_lb'] = True

        medium_fluxes = {
            'items': [
                {
                    'reaction_id': simulation.MISSION02_BLOCKED_CARBON_SOURCE,
                    'raw_flux': -10.0,
                    'uptake_flux': 10.0,
                    'secretion_flux': 0.0,
                },
                {
                    'reaction_id': source_id,
                    'raw_flux': -1.0,
                    'uptake_flux': 1.0,
                    'secretion_flux': 0.0,
                },
            ]
        }

        with patch.object(simulation, 'save_mission02_source_comparison_check'):
            report = simulation._build_mission02_trial_data(
                simulation.MISSION02_METHOD,
                simulation.MISSION02_GROWTH_OBJECTIVE,
                1.0,
                self.genes,
                reactions,
                medium_fluxes=medium_fluxes,
            )

        self.assertFalse(report['current_run_valid'])
        self.assertFalse(report['current_run_recorded'])
        self.assertEqual(report['valid_trial_count'], 0)
        self.assertTrue(
            any('Glucose is still available' in issue for issue in report['current_issues'])
        )

    def test_two_candidates_in_one_run_are_rejected(self):
        reactions = self._candidate_reactions('EX_fru_e')
        malate_index = self.reaction_ids.index('EX_mal__L_e')
        reactions[f'reaction_{malate_index}_lb'] = True

        medium_fluxes = {
            'items': [
                {
                    'reaction_id': simulation.MISSION02_BLOCKED_CARBON_SOURCE,
                    'raw_flux': 0.0,
                    'uptake_flux': 0.0,
                    'secretion_flux': 0.0,
                },
                {
                    'reaction_id': 'EX_fru_e',
                    'raw_flux': -5.0,
                    'uptake_flux': 5.0,
                    'secretion_flux': 0.0,
                },
                {
                    'reaction_id': 'EX_mal__L_e',
                    'raw_flux': -5.0,
                    'uptake_flux': 5.0,
                    'secretion_flux': 0.0,
                },
            ]
        }

        with patch.object(simulation, 'save_mission02_source_comparison_check'):
            report = simulation._build_mission02_trial_data(
                simulation.MISSION02_METHOD,
                simulation.MISSION02_GROWTH_OBJECTIVE,
                1.0,
                self.genes,
                reactions,
                medium_fluxes=medium_fluxes,
            )

        self.assertFalse(report['current_run_valid'])
        self.assertTrue(
            any('exactly one candidate' in issue for issue in report['current_issues'])
        )



    def test_initial_report_hides_the_full_recipe(self):
        text = simulation.build_mission02_evidence_report_text({})
        self.assertIn('Build a fair carbon-source replacement comparison', text)
        self.assertNotIn('common uptake limit', text)
        self.assertNotIn('FBA biomass objective', text)
        self.assertNotIn('no knockouts', text)

    def test_protocol_is_confirmed_after_the_first_valid_trial(self):
        with patch.object(simulation, 'save_mission02_source_comparison_check'):
            report = self._record_valid_trial('EX_mal__L_e')

        text = simulation.build_mission02_evidence_report_text(report)
        self.assertIn('Controlled setup confirmed', text)
        self.assertIn('common uptake limit -10', text)
        self.assertIn('FBA biomass objective', text)
        self.assertIn('genes unchanged', text)

    def test_invalid_runs_do_not_replace_or_increment_valid_evidence(self):
        with patch.object(simulation, 'save_mission02_source_comparison_check'):
            baseline_report = self._record_valid_trial('EX_mal__L_e')

        self.assertEqual(baseline_report['valid_trial_count'], 1)
        expected_trials = dict(baseline_report['trials'])

        # Invalid case 1: glucose remains available, so the candidate is a
        # supplement rather than a replacement.
        glucose_open = dict(self.default_reactions)
        fructose_index = self.reaction_ids.index('EX_fru_e')
        glucose_open[f'reaction_{fructose_index}_lb'] = True
        glucose_open_fluxes = {
            'items': [
                {
                    'reaction_id': simulation.MISSION02_BLOCKED_CARBON_SOURCE,
                    'raw_flux': -10.0,
                    'uptake_flux': 10.0,
                    'secretion_flux': 0.0,
                },
                {
                    'reaction_id': 'EX_fru_e',
                    'raw_flux': -5.0,
                    'uptake_flux': 5.0,
                    'secretion_flux': 0.0,
                },
            ]
        }

        # Invalid case 2: two candidate sources are available together.
        two_sources = self._candidate_reactions('EX_fru_e')
        malate_index = self.reaction_ids.index('EX_mal__L_e')
        two_sources[f'reaction_{malate_index}_lb'] = True
        two_source_fluxes = {
            'items': [
                {
                    'reaction_id': simulation.MISSION02_BLOCKED_CARBON_SOURCE,
                    'raw_flux': 0.0,
                    'uptake_flux': 0.0,
                    'secretion_flux': 0.0,
                },
                {
                    'reaction_id': 'EX_fru_e',
                    'raw_flux': -5.0,
                    'uptake_flux': 5.0,
                    'secretion_flux': 0.0,
                },
                {
                    'reaction_id': 'EX_mal__L_e',
                    'raw_flux': -5.0,
                    'uptake_flux': 5.0,
                    'secretion_flux': 0.0,
                },
            ]
        }

        # Invalid case 3: a gene knockout is active during an otherwise valid
        # fructose trial.
        fructose_reactions, fructose_growth, fructose_fluxes, _ = self._simulate_candidate(
            'EX_fru_e'
        )
        genes_with_knockout = dict(self.genes)
        knocked_gene = next(iter(genes_with_knockout))
        genes_with_knockout[knocked_gene] = False

        cases = [
            (self.genes, glucose_open, glucose_open_fluxes, 'Glucose is still available'),
            (self.genes, two_sources, two_source_fluxes, 'exactly one candidate'),
            (genes_with_knockout, fructose_reactions, fructose_fluxes, 'Keep all genes active'),
        ]

        with patch.object(simulation, 'save_mission02_source_comparison_check'):
            for genes, reactions, medium_fluxes, expected_issue in cases:
                report = simulation._build_mission02_trial_data(
                    simulation.MISSION02_METHOD,
                    simulation.MISSION02_GROWTH_OBJECTIVE,
                    fructose_growth,
                    genes,
                    reactions,
                    medium_fluxes=medium_fluxes,
                    existing_report=baseline_report,
                )
                self.assertFalse(report['current_run_valid'])
                self.assertFalse(report['current_run_recorded'])
                self.assertEqual(report['valid_trial_count'], 1)
                self.assertEqual(report['trials'], expected_trials)
                self.assertTrue(
                    any(expected_issue in issue for issue in report['current_issues']),
                    report['current_issues'],
                )
    def test_progression_requires_mission01(self):
        self.assertFalse(simulation.is_mission02_unlocked([]))
        self.assertFalse(simulation.is_mission02_unlocked(['02']))
        self.assertTrue(simulation.is_mission02_unlocked(['01']))
        self.assertTrue(simulation.is_mission02_unlocked(['01', '02']))

    def test_mission02_guards_every_entry_and_delivery_path(self):
        source = (CODE_DIR / 'mission02.py').read_text(encoding='utf-8')
        # Compatibility dialogue, setup, activation and delivery each enforce
        # the prerequisite instead of relying only on the normal NPC path.
        self.assertGreaterEqual(
            source.count("if not self.player.is_mission_unlocked('02'):"),
            4,
        )
        self.assertIn('Mission 02 is locked. Complete Mission 01', source)
        self.assertIn('Complete Mission 01 before starting Mission 02.', source)
        self.assertIn('Complete Mission 01 before delivering Mission 02.', source)
        self.assertIn("if '02' not in self.missions_activated:", source)

    def test_mission02_reactivation_does_not_clear_candidate_trials(self):
        source = (CODE_DIR / 'mission02.py').read_text(encoding='utf-8')
        active_guard = source.index("if '02' in self.missions_activated:")
        clear_check = source.index('clear_mission02_source_comparison_check()', active_guard)
        self.assertLess(active_guard, clear_check)
        self.assertIn('Mission 02 is already active.', source[active_guard:clear_check])



if __name__ == '__main__':
    unittest.main()
