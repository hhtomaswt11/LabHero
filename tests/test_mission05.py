"""Regression tests for Mission 05 context-dependent anaerobic ethanol evidence.

Run from the project root with:
    python3 -m unittest discover -s tests -p "test_mission05.py"
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import simulation  # noqa: E402
from gpr import disabled_reaction_ids  # noqa: E402


class Mission05RegressionTests(unittest.TestCase):
    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.reactions = simulation._build_anaerobic_reactions_data()

    def _simulate(self, knocked_out=None, method=None, objective=None, reactions=None):
        genes = dict(self.genes)
        for gene_id in knocked_out or []:
            genes[gene_id] = False

        active_reactions = reactions or self.reactions
        simul, constraints = simulation._build_local_constraints(genes, active_reactions)
        simul.objective = objective or simulation.MISSION05_GROWTH_OBJECTIVE
        result = simul.simulate(
            method=method or simulation.MISSION05_METHOD,
            constraints=constraints,
        )
        objective_result = simulation._normalise_result(result)
        production_fluxes = simulation._build_production_flux_data(
            [simulation.MISSION05_PRODUCTION_OBJECTIVE],
            flux_getter=lambda reaction_id: simulation._extract_flux(result, reaction_id),
        )
        medium_fluxes = simulation._build_medium_flux_data(
            flux_getter=lambda reaction_id: simulation._extract_flux(result, reaction_id),
        )
        return objective_result, production_fluxes, medium_fluxes, genes, constraints, result

    def _record(
        self,
        knocked_out=None,
        report=None,
        method=None,
        objective=None,
        reactions=None,
        objective_result=None,
        production_fluxes=None,
        medium_fluxes=None,
        tracked=True,
    ):
        active_reactions = reactions or self.reactions
        if objective_result is None and production_fluxes is None and medium_fluxes is None:
            (
                objective_result,
                production_fluxes,
                medium_fluxes,
                genes,
                _constraints,
                _result,
            ) = self._simulate(
                knocked_out,
                method=method,
                objective=objective,
                reactions=active_reactions,
            )
        else:
            genes = dict(self.genes)
            for gene_id in knocked_out or []:
                genes[gene_id] = False

        selected_fluxes = (
            [simulation.MISSION05_PRODUCTION_OBJECTIVE]
            if tracked
            else []
        )
        with (
            patch.object(simulation, 'save_mission05_production_check'),
            patch.object(simulation, '_read_selected_production_fluxes', return_value=selected_fluxes),
        ):
            return simulation._build_mission05_trial_data(
                method or simulation.MISSION05_METHOD,
                objective or simulation.MISSION05_GROWTH_OBJECTIVE,
                objective_result,
                genes,
                active_reactions,
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                existing_report=report,
            )

    @staticmethod
    def _synthetic_flux_data(ethanol=8.0, oxygen_uptake=0.0):
        production_fluxes = {
            'selected_ids': [simulation.MISSION05_PRODUCTION_OBJECTIVE],
            'items': [{
                'reaction_id': simulation.MISSION05_PRODUCTION_OBJECTIVE,
                'production_flux': float(ethanol),
                'raw_flux': float(ethanol),
            }],
        }
        medium_fluxes = {
            'items': [{
                'reaction_id': simulation.MISSION05_OXYGEN_REACTION,
                'raw_flux': -float(oxygen_uptake),
                'uptake_flux': float(oxygen_uptake),
                'secretion_flux': 0.0,
            }],
        }
        return production_fluxes, medium_fluxes

    @staticmethod
    def _flux_value(production_fluxes, reaction_id):
        values = simulation._production_flux_value_map(production_fluxes)
        return float(values[reaction_id])

    def test_old_lactate_design_is_invalid_under_correct_gpr(self):
        # b1241 has OR alternatives, so its single-gene deletion must not
        # directly disable ACALD/ALCD2x or create the legacy lactate phenotype.
        _growth, _production, _medium, _genes, constraints, result = self._simulate(['b1241'])
        self.assertNotEqual(constraints.get('ACALD'), (0.0, 0.0))
        self.assertNotEqual(constraints.get('ALCD2x'), (0.0, 0.0))
        lactate = simulation._extract_flux(result, 'EX_lac__D_e')
        self.assertAlmostEqual(float(lactate), 0.0, places=3)

    def test_all_legacy_single_knockout_candidates_keep_lactate_zero(self):
        legacy_candidates = ['b0903', 'b2297', 'b0723', 'b3115', 'b0728', 'b1241']
        for gene_id in legacy_candidates:
            growth, _production, _medium, _genes, _constraints, result = self._simulate([gene_id])
            self.assertGreater(float(growth), 0.0, gene_id)
            self.assertAlmostEqual(float(simulation._extract_flux(result, 'EX_lac__D_e')), 0.0, places=3, msg=gene_id)

    def test_backend_and_desktop_disable_the_same_reactions(self):
        backend_path = PROJECT_ROOT / 'backend' / 'app' / 'gpr.py'
        spec = importlib.util.spec_from_file_location('labhero_backend_gpr_m05', backend_path)
        backend_gpr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend_gpr)

        for knockouts in ({'b2278'}, {'b0728'}, {'b1602'}, {'b3736'}, {'b1241'}):
            self.assertEqual(
                set(disabled_reaction_ids(simulation.model, knockouts)),
                set(backend_gpr.disabled_reaction_ids(simulation.model, knockouts)),
            )

    def test_candidate_pattern_and_complete_evidence(self):
        report = self._record([])
        self.assertAlmostEqual(report['baseline_growth'], 0.211663, places=3)
        self.assertAlmostEqual(report['baseline_production'], 8.279455, places=3)
        self.assertLessEqual(report['baseline_oxygen_uptake'], simulation.MISSION05_FLUX_TOLERANCE)

        for gene_id in simulation.MISSION05_CANDIDATE_GENES:
            report = self._record([gene_id], report=report)
            self.assertTrue(report['current_run_valid'], report['current_issues'])

        self.assertEqual(report['valid_trial_count'], 4)
        self.assertTrue(report['comparison_complete'])
        self.assertTrue(report['winner_unique'])
        self.assertEqual(report['winning_gene'], 'b3736')
        self.assertTrue(report['evidence_ready'])

        trials = report['trials']
        self.assertAlmostEqual(trials['b2278']['growth'], 0.211663, places=3)
        self.assertAlmostEqual(trials['b2278']['production'], 8.279455, places=3)
        self.assertAlmostEqual(trials['b2278']['production_change'], 0.0, places=3)
        self.assertAlmostEqual(trials['b0728']['production'], 8.279455, places=3)
        self.assertAlmostEqual(trials['b1602']['growth'], 0.207557, places=3)
        self.assertAlmostEqual(trials['b1602']['production'], 9.795662, places=3)
        self.assertTrue(trials['b1602']['eligible_design'])
        self.assertAlmostEqual(trials['b3736']['growth'], 0.196462, places=3)
        self.assertAlmostEqual(trials['b3736']['production'], 13.892611, places=3)
        self.assertGreaterEqual(
            trials['b3736']['growth_ratio'],
            simulation.MISSION05_MIN_VIABLE_GROWTH_RATIO,
        )
        self.assertTrue(trials['b3736']['eligible_design'])

    def test_delivery_requires_complete_evidence_and_accepts_aliases(self):
        self.assertFalse(simulation.mission05_answer_matches('b3736', {}))
        report = self._record([])
        for gene_id in simulation.MISSION05_CANDIDATE_GENES:
            report = self._record([gene_id], report=report)

        for answer in ('b3736', 'B3736', 'atpF', 'ATPF', 'b3736 (atpF)', 'b3736/atpF'):
            self.assertTrue(simulation.mission05_answer_matches(answer, report))
        self.assertFalse(simulation.mission05_answer_matches('b2278', report))
        self.assertFalse(simulation.mission05_answer_matches('b1241', report))

    def test_invalid_runs_do_not_increment_or_replace_evidence(self):
        report = self._record([])
        report = self._record(['b2278'], report=report)
        expected_trials = dict(report['trials'])
        expected_baseline = report['baseline_growth']

        aerobic_environment = simulation._build_default_reactions_data()
        extra_changed_environment = dict(self.reactions)
        glucose_index = list(simulation.REACTIONS.index).index('EX_glc__D_e')
        extra_changed_environment[f'reaction_{glucose_index}_lb'] = False

        production_fluxes, medium_fluxes = self._synthetic_flux_data(13.0, 0.0)
        invalid_cases = [
            (['b2278', 'b0728'], simulation.MISSION05_METHOD, simulation.MISSION05_GROWTH_OBJECTIVE, self.reactions, True, 'exactly one'),
            (['b1241'], simulation.MISSION05_METHOD, simulation.MISSION05_GROWTH_OBJECTIVE, self.reactions, True, 'not one of'),
            (['b3736'], 'pFBA', simulation.MISSION05_GROWTH_OBJECTIVE, self.reactions, True, 'Use FBA'),
            (['b3736'], simulation.MISSION05_METHOD, simulation.MISSION05_PRODUCTION_OBJECTIVE, self.reactions, True, 'biomass objective'),
            (['b3736'], simulation.MISSION05_METHOD, simulation.MISSION05_GROWTH_OBJECTIVE, aerobic_environment, True, 'anaerobic environment'),
            (['b3736'], simulation.MISSION05_METHOD, simulation.MISSION05_GROWTH_OBJECTIVE, extra_changed_environment, True, 'only environmental change'),
            (['b3736'], simulation.MISSION05_METHOD, simulation.MISSION05_GROWTH_OBJECTIVE, self.reactions, False, 'Track EX_etoh_e'),
        ]

        for knockouts, method, objective, reactions, tracked, expected_issue in invalid_cases:
            candidate = self._record(
                knockouts,
                report=report,
                method=method,
                objective=objective,
                reactions=reactions,
                objective_result=0.2,
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                tracked=tracked,
            )
            self.assertFalse(candidate['current_run_valid'])
            self.assertFalse(candidate['current_run_recorded'])
            self.assertEqual(candidate['valid_trial_count'], 1)
            self.assertEqual(candidate['trials'], expected_trials)
            self.assertEqual(candidate['baseline_growth'], expected_baseline)
            self.assertTrue(
                any(expected_issue in issue for issue in candidate['current_issues']),
                candidate['current_issues'],
            )

    def test_nonzero_oxygen_uptake_is_rejected_even_if_toggles_claim_anaerobiosis(self):
        report = self._record([])
        production_fluxes, medium_fluxes = self._synthetic_flux_data(13.0, 2.0)
        candidate = self._record(
            ['b3736'],
            report=report,
            objective_result=0.196,
            production_fluxes=production_fluxes,
            medium_fluxes=medium_fluxes,
        )
        self.assertFalse(candidate['current_run_valid'])
        self.assertFalse(candidate['current_run_recorded'])
        self.assertEqual(candidate['valid_trial_count'], 0)
        self.assertTrue(
            any('zero oxygen uptake' in issue for issue in candidate['current_issues']),
            candidate['current_issues'],
        )

    def test_missing_or_infeasible_result_preserves_evidence(self):
        report = self._record([])
        report = self._record(['b2278'], report=report)
        expected_trials = dict(report['trials'])
        expected_baseline = report['baseline_growth']

        genes = dict(self.genes)
        genes['b3736'] = False
        with (
            patch.object(simulation, 'save_mission05_production_check'),
            patch.object(
                simulation,
                '_read_selected_production_fluxes',
                return_value=[simulation.MISSION05_PRODUCTION_OBJECTIVE],
            ),
        ):
            candidate = simulation._build_mission05_trial_data(
                simulation.MISSION05_METHOD,
                simulation.MISSION05_GROWTH_OBJECTIVE,
                None,
                genes,
                self.reactions,
                production_fluxes={'error': 'infeasible'},
                medium_fluxes={'error': 'infeasible'},
                existing_report=report,
            )

        self.assertFalse(candidate['current_run_valid'])
        self.assertFalse(candidate['current_run_recorded'])
        self.assertEqual(candidate['trials'], expected_trials)
        self.assertEqual(candidate['baseline_growth'], expected_baseline)
        self.assertTrue(any('numeric biomass-growth' in issue for issue in candidate['current_issues']))
        self.assertTrue(any('numeric EX_etoh_e' in issue for issue in candidate['current_issues']))

    def test_repeated_candidate_replaces_instead_of_incrementing(self):
        report = self._record([])
        report = self._record(['b2278'], report=report)
        self.assertEqual(report['valid_trial_count'], 1)
        repeated = self._record(['b2278'], report=report)
        self.assertEqual(repeated['valid_trial_count'], 1)
        self.assertEqual(set(repeated['trials']), {'b2278'})

    def test_explicit_empty_report_does_not_load_saved_evidence(self):
        completed = {
            'mission_id': '05',
            'check_version': 2,
            'evidence_ready': True,
            'winning_gene': 'b3736',
            'trials': {'b3736': {'growth': 0.196, 'production': 13.893}},
        }
        with patch.object(simulation, 'load_mission05_production_check', return_value=completed) as loader:
            text = simulation.build_mission05_evidence_report_text({})
            self.assertFalse(simulation.mission05_answer_matches('b3736', {}))
        loader.assert_not_called()
        self.assertIn('Investigate whether a production strategy remains useful', text)
        self.assertNotIn('Controlled setup confirmed', text)

    def test_legacy_report_is_not_mixed_with_new_evidence(self):
        legacy = {
            'target_gene': 'b1241',
            'product_name': 'lactate',
            'baseline_growth': 10.0,
            'baseline_production': 0.0,
            'current_growth': 8.0,
            'current_production': 700.0,
        }
        production_fluxes, medium_fluxes = self._synthetic_flux_data(8.279455, 0.0)
        report = self._record(
            [],
            report=legacy,
            objective_result=0.211663,
            production_fluxes=production_fluxes,
            medium_fluxes=medium_fluxes,
        )
        self.assertAlmostEqual(report['baseline_growth'], 0.211663, places=3)
        self.assertAlmostEqual(report['baseline_production'], 8.279455, places=3)
        self.assertNotIn('target_gene', report)
        self.assertEqual(report['product_name'], 'ethanol')

    def test_progression_requires_mission04(self):
        self.assertFalse(simulation.is_mission05_unlocked([]))
        self.assertFalse(simulation.is_mission05_unlocked(['03']))
        self.assertTrue(simulation.is_mission05_unlocked(['04']))

    def test_remote_wrapper_reuses_visible_result_without_hidden_requests(self):
        visible_result = object()
        expected = {'visible': True}
        with patch.object(simulation, 'run_mission05_production_trial_check', return_value=expected) as runner:
            observed = simulation.run_mission05_production_check_remote('unused-url', visible_result)
        self.assertIs(observed, expected)
        runner.assert_called_once_with(visible_result)

    def test_candidate_ethanol_fluxes_are_fixed_at_maximum_growth(self):
        try:
            from cobra.flux_analysis import flux_variability_analysis
        except Exception as exc:  # pragma: no cover - dependency is expected in the project env
            self.skipTest(f'COBRApy FVA unavailable: {exc}')

        expected = {
            'b2278': 8.279455,
            'b0728': 8.279455,
            'b1602': 9.795662,
            'b3736': 13.892611,
        }
        for gene_id, expected_ethanol in expected.items():
            model = simulation.model.copy()
            model.reactions.get_by_id(simulation.MISSION05_OXYGEN_REACTION).lower_bound = 0.0
            for reaction_id in disabled_reaction_ids(model, {gene_id}):
                model.reactions.get_by_id(reaction_id).bounds = (0.0, 0.0)
            model.objective = simulation.MISSION05_GROWTH_OBJECTIVE
            solution = model.optimize()
            self.assertEqual(solution.status, 'optimal', gene_id)
            fva = flux_variability_analysis(
                model,
                reaction_list=[simulation.MISSION05_PRODUCTION_OBJECTIVE],
                fraction_of_optimum=1.0,
            )
            minimum = float(fva.loc[simulation.MISSION05_PRODUCTION_OBJECTIVE, 'minimum'])
            maximum = float(fva.loc[simulation.MISSION05_PRODUCTION_OBJECTIVE, 'maximum'])
            self.assertAlmostEqual(minimum, maximum, delta=1e-4, msg=gene_id)
            self.assertAlmostEqual(minimum, expected_ethanol, delta=1e-3, msg=gene_id)


if __name__ == '__main__':
    unittest.main()
