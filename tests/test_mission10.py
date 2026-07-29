"""Regression tests for Mission 10 two-gene redundancy and flux redirection.

Run from the project root with:
    python3 tests/test_mission10.py
"""
from __future__ import annotations

import inspect
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


class Mission10RegressionTests(unittest.TestCase):
    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.reactions = simulation._build_default_reactions_data()
        oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION10_OXYGEN_REACTION)
        self.reactions[f'reaction_{oxygen_index}_lb'] = False

    def _simulate(self, knocked_out=None, method=None, objective=None, reactions=None):
        genes = dict(self.genes)
        for gene_id in knocked_out or []:
            genes[gene_id] = False
        reactions = reactions or self.reactions
        simul, constraints = simulation._build_local_constraints(genes, reactions)
        objective = objective or simulation.MISSION10_GROWTH_OBJECTIVE
        simul.objective = objective
        result = simul.simulate(method=method or simulation.MISSION10_METHOD, constraints=constraints)
        objective_result = simulation._normalise_result(result)
        flux_getter = lambda reaction_id: simulation._extract_flux(result, reaction_id)
        production = simulation._build_production_flux_data(
            simulation.MISSION10_REQUIRED_TRACKED_FLUXES,
            flux_getter=flux_getter,
        )
        objective_raw = simulation._as_float_or_none(simulation._extract_flux(result, objective))
        if objective_raw is not None:
            production['objective_raw'] = objective_raw
        biomass_raw = simulation._as_float_or_none(
            simulation._extract_flux(result, simulation.MISSION10_GROWTH_OBJECTIVE)
        )
        if biomass_raw is not None:
            production['biomass_raw'] = biomass_raw
        medium = simulation._build_medium_flux_data(flux_getter=flux_getter)
        return objective_result, production, medium, genes, constraints

    def _record(
        self,
        knocked_out=None,
        report=None,
        method=None,
        objective=None,
        reactions=None,
        tracked_fluxes=None,
        objective_result=None,
        production_fluxes=None,
        medium_fluxes=None,
    ):
        reactions = reactions or self.reactions
        if objective_result is None and production_fluxes is None and medium_fluxes is None:
            objective_result, production_fluxes, medium_fluxes, genes, _constraints = self._simulate(
                knocked_out,
                method=method,
                objective=objective,
                reactions=reactions,
            )
        else:
            genes = dict(self.genes)
            for gene_id in knocked_out or []:
                genes[gene_id] = False
        if tracked_fluxes is None:
            tracked_fluxes = list(simulation.MISSION10_REQUIRED_TRACKED_FLUXES)
        with (
            patch.object(simulation, 'save_mission10_robust_design_check'),
            patch.object(simulation, '_read_selected_production_fluxes', return_value=tracked_fluxes),
        ):
            return simulation._build_mission10_data(
                method or simulation.MISSION10_METHOD,
                objective or simulation.MISSION10_GROWTH_OBJECTIVE,
                objective_result,
                genes,
                reactions,
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                existing_report=report,
            )

    @staticmethod
    def _synthetic_flux_data(growth=0.2, ethanol=10.0, acetate=4.0, glucose=10.0, oxygen=0.0):
        production = {
            'selected_ids': list(simulation.MISSION10_REQUIRED_TRACKED_FLUXES),
            'objective_raw': float(growth),
            'biomass_raw': float(growth),
            'items': [
                {
                    'reaction_id': simulation.MISSION10_TARGET_FLUX,
                    'raw_flux': float(ethanol),
                    'production_flux': round(max(float(ethanol), 0.0), 3),
                },
                {
                    'reaction_id': simulation.MISSION10_COMPETING_FLUX,
                    'raw_flux': float(acetate),
                    'production_flux': round(max(float(acetate), 0.0), 3),
                },
            ],
        }
        medium = {'items': [
            {
                'reaction_id': simulation.MISSION10_GLUCOSE_REACTION,
                'raw_flux': -float(glucose),
                'uptake_flux': float(glucose),
                'secretion_flux': 0.0,
            },
            {
                'reaction_id': simulation.MISSION10_OXYGEN_REACTION,
                'raw_flux': -float(oxygen),
                'uptake_flux': float(oxygen),
                'secretion_flux': 0.0,
            },
        ]}
        return production, medium

    def _complete_report(self, reverse=False):
        report = None
        pairs = list(simulation.MISSION10_REQUIRED_PAIRS)
        if reverse:
            pairs.reverse()
        for pair in pairs:
            report = self._record(pair, report=report)
        return self._record([], report=report)

    def test_progression_requires_mission09(self):
        self.assertFalse(simulation.is_mission10_unlocked([]))
        self.assertFalse(simulation.is_mission10_unlocked(['08']))
        self.assertTrue(simulation.is_mission10_unlocked(['09']))

    def test_constants_candidate_names_and_pairs(self):
        self.assertEqual(simulation.MISSION10_CHECK_VERSION, 3)
        self.assertEqual(simulation.MISSION10_METHOD, 'FBA')
        self.assertEqual(simulation.MISSION10_TARGET_PRODUCT, 'ethanol')
        self.assertEqual(simulation.MISSION10_TARGET_FLUX, 'EX_etoh_e')
        self.assertEqual(simulation.MISSION10_COMPETING_FLUX, 'EX_ac_e')
        self.assertEqual(
            simulation.MISSION10_CANDIDATE_GENES,
            ['b2297', 'b2458', 'b1241', 'b0351'],
        )
        self.assertEqual(simulation.MISSION10_GENE_NAMES['b2458'], 'eutD')
        self.assertEqual(simulation.MISSION10_EXPECTED_WINNING_PAIR, ('b2297', 'b2458'))
        self.assertEqual(len(simulation.MISSION10_REQUIRED_PAIRS), 6)
        self.assertEqual(len(set(simulation._mission10_required_pair_keys())), 6)

    def test_environment_validator_accepts_explicit_and_legacy_keys(self):
        self.assertEqual(simulation._mission10_environment_status(self.reactions), (True, True, []))
        legacy = {
            f'auto_widget_{index}': value
            for index, value in enumerate(self.reactions.values())
        }
        self.assertEqual(simulation._mission10_environment_status(legacy), (True, True, []))
        explicit_constraints = simulation._build_envconditions_from_reactions(self.reactions, simulation.REACTIONS)
        legacy_constraints = simulation._build_envconditions_from_reactions(legacy, simulation.REACTIONS)
        self.assertEqual(explicit_constraints, legacy_constraints)
        self.assertEqual(explicit_constraints[simulation.MISSION10_GLUCOSE_REACTION][0], -10.0)
        self.assertEqual(explicit_constraints[simulation.MISSION10_OXYGEN_REACTION][0], 0.0)

    def test_no_knockout_anaerobic_reference(self):
        report = self._record([])
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertTrue(report['baseline_recorded'])
        baseline = report['baseline']
        self.assertAlmostEqual(baseline['growth'], 0.211663, places=3)
        self.assertAlmostEqual(baseline['ethanol'], 8.279455, places=3)
        self.assertAlmostEqual(baseline['acetate'], 8.503585, places=3)
        self.assertAlmostEqual(baseline['glucose_uptake'], 10.0, places=3)
        self.assertAlmostEqual(baseline['oxygen_uptake'], 0.0, places=3)

    def test_all_pair_values_and_unique_winner(self):
        expected = {
            'b2297+b2458': (0.189173, 16.584256, 0.0),
            'b2297+b1241': (0.211663, 8.279455, 8.503585),
            'b2297+b0351': (0.211663, 8.279455, 8.503585),
            'b2458+b1241': (0.211663, 8.279455, 8.503585),
            'b2458+b0351': (0.211663, 8.279455, 8.503585),
            'b1241+b0351': (0.137905, 0.0, 0.146027),
        }
        report = self._record([])
        for pair in simulation.MISSION10_REQUIRED_PAIRS:
            report = self._record(pair, report=report)
            key = simulation._mission10_pair_key(pair)
            growth, ethanol, acetate = expected[key]
            trial = report['trials'][key]
            self.assertAlmostEqual(trial['growth'], growth, places=3, msg=key)
            self.assertAlmostEqual(trial['ethanol'], ethanol, places=3, msg=key)
            self.assertAlmostEqual(trial['acetate'], acetate, places=3, msg=key)
        self.assertTrue(report['comparison_complete'])
        self.assertTrue(report['winner_unique'])
        self.assertEqual(report['winning_pair'], 'b2297+b2458')
        self.assertTrue(report['expected_winner_confirmed'])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['trials']['b2297+b2458']['eligible_design'])
        self.assertAlmostEqual(report['trials']['b2297+b2458']['growth_percent'], 89.4, places=1)
        self.assertAlmostEqual(report['trials']['b2297+b2458']['ethanol_change'], 8.3048, places=3)
        self.assertFalse(report['trials']['b1241+b0351']['viable'])
        for key in (
            'b2297+b1241', 'b2297+b0351',
            'b2458+b1241', 'b2458+b0351',
        ):
            self.assertFalse(report['trials'][key]['ethanol_improved'], key)

    def test_single_redundant_knockouts_preserve_the_baseline_phenotype(self):
        baseline_result, baseline_production, _medium, _genes, _constraints = self._simulate([])
        baseline_growth = simulation._as_float_or_none(baseline_production.get('objective_raw'))
        baseline_fluxes = {
            item['reaction_id']: item.get('raw_flux')
            for item in baseline_production.get('items') or []
        }
        for gene_id in ('b2297', 'b2458'):
            _result, production, _medium, _genes, _constraints = self._simulate([gene_id])
            growth = simulation._as_float_or_none(production.get('objective_raw'))
            fluxes = {
                item['reaction_id']: item.get('raw_flux')
                for item in production.get('items') or []
            }
            self.assertAlmostEqual(growth, baseline_growth, places=6, msg=gene_id)
            self.assertAlmostEqual(
                fluxes[simulation.MISSION10_TARGET_FLUX],
                baseline_fluxes[simulation.MISSION10_TARGET_FLUX],
                places=6,
                msg=gene_id,
            )
            self.assertAlmostEqual(
                fluxes[simulation.MISSION10_COMPETING_FLUX],
                baseline_fluxes[simulation.MISSION10_COMPETING_FLUX],
                places=6,
                msg=gene_id,
            )

    def test_gpr_redundancy_and_pair_reaction_effects(self):
        model = simulation.model
        self.assertEqual(disabled_reaction_ids(model, {'b2297'}), [])
        self.assertEqual(disabled_reaction_ids(model, {'b2458'}), [])
        self.assertEqual(set(disabled_reaction_ids(model, {'b2297', 'b2458'})), {'PTAr'})
        self.assertEqual(disabled_reaction_ids(model, {'b1241'}), [])
        self.assertEqual(disabled_reaction_ids(model, {'b0351'}), [])
        self.assertEqual(set(disabled_reaction_ids(model, {'b1241', 'b0351'})), {'ACALD'})
        for pair in (
            {'b2297', 'b1241'}, {'b2297', 'b0351'},
            {'b2458', 'b1241'}, {'b2458', 'b0351'},
        ):
            self.assertEqual(disabled_reaction_ids(model, pair), [])

    def test_trials_can_precede_baseline_and_order_is_irrelevant(self):
        report = self._record(('b2297', 'b2458'))
        self.assertFalse(report['baseline_recorded'])
        self.assertIn('b2297+b2458', report['trials'])
        report = self._record([], report=report)
        self.assertTrue(report['baseline_recorded'])
        self.assertAlmostEqual(report['trials']['b2297+b2458']['growth_percent'], 89.4, places=1)
        complete = self._complete_report(reverse=True)
        self.assertTrue(complete['evidence_ready'])
        self.assertEqual(complete['winning_pair'], 'b2297+b2458')

    def test_repeated_pair_updates_without_duplicate_count(self):
        report = self._record([])
        report = self._record(('b2297', 'b2458'), report=report)
        report = self._record(('b2458', 'b2297'), report=report)
        self.assertEqual(report['valid_trial_count'], 1)
        self.assertEqual(set(report['trials']), {'b2297+b2458'})

    def test_invalid_runs_preserve_complete_evidence(self):
        report = self._complete_report()
        baseline = dict(report['baseline'])
        trials = {key: dict(value) for key, value in report['trials'].items()}
        production, medium = self._synthetic_flux_data()

        default_env = simulation._build_default_reactions_data()
        extra_env = dict(self.reactions)
        glucose_index = list(simulation.REACTIONS.index).index(simulation.MISSION10_GLUCOSE_REACTION)
        extra_env[f'reaction_{glucose_index}_lb'] = False

        cases = [
            dict(method='pFBA', message='Use FBA'),
            dict(objective=simulation.MISSION10_TARGET_FLUX, message='biomass objective'),
            dict(reactions=default_env, message='Close only'),
            dict(reactions=extra_env, message='every other environmental bound'),
            dict(knocked_out=['b2297'], message='exactly two'),
            dict(knocked_out=['b2297', 'b2458', 'b1241'], message='exactly two'),
            dict(knocked_out=['b2297', 'b1479'], message='candidate list'),
            dict(tracked_fluxes=[simulation.MISSION10_TARGET_FLUX], message='Track both'),
        ]
        for case in cases:
            candidate = self._record(
                knocked_out=case.get('knocked_out', ['b2297', 'b2458']),
                report=report,
                method=case.get('method'),
                objective=case.get('objective'),
                reactions=case.get('reactions', self.reactions),
                tracked_fluxes=case.get('tracked_fluxes'),
                objective_result=0.2,
                production_fluxes=production,
                medium_fluxes=medium,
            )
            self.assertFalse(candidate['current_run_valid'])
            self.assertEqual(candidate['baseline'], baseline)
            self.assertEqual(candidate['trials'], trials)
            self.assertTrue(candidate['evidence_ready'])
            self.assertTrue(any(case['message'] in issue for issue in candidate['current_issues']))

    def test_visible_solution_requires_growth_products_and_medium_evidence(self):
        production, medium = self._synthetic_flux_data()
        production['items'] = [
            item for item in production['items']
            if item['reaction_id'] != simulation.MISSION10_TARGET_FLUX
        ]
        missing_ethanol = self._record([], objective_result=0.2, production_fluxes=production, medium_fluxes=medium)
        self.assertFalse(missing_ethanol['current_run_valid'])
        self.assertTrue(any('EX_etoh_e' in issue for issue in missing_ethanol['current_issues']))

        production, medium = self._synthetic_flux_data()
        production['items'] = [
            item for item in production['items']
            if item['reaction_id'] != simulation.MISSION10_COMPETING_FLUX
        ]
        missing_acetate = self._record([], objective_result=0.2, production_fluxes=production, medium_fluxes=medium)
        self.assertFalse(missing_acetate['current_run_valid'])
        self.assertTrue(any('EX_ac_e' in issue for issue in missing_acetate['current_issues']))

        production, medium = self._synthetic_flux_data()
        medium['items'] = [item for item in medium['items'] if item['reaction_id'] != simulation.MISSION10_OXYGEN_REACTION]
        missing_oxygen = self._record([], objective_result=0.2, production_fluxes=production, medium_fluxes=medium)
        self.assertFalse(missing_oxygen['current_run_valid'])
        self.assertTrue(any('oxygen' in issue.lower() for issue in missing_oxygen['current_issues']))

    def test_answer_requires_complete_evidence_and_accepts_pair_aliases(self):
        incomplete = self._record([])
        self.assertFalse(simulation.mission10_answer_matches('b2297 + b2458', incomplete))
        complete = self._complete_report()
        accepted = (
            'b2297 + b2458', 'b2458/b2297',
            'pta + eutD', 'EUTD PTA',
            'b2297 + eutD', 'pta/b2458',
        )
        for answer in accepted:
            self.assertTrue(simulation.mission10_answer_matches(answer, complete), answer)
        self.assertFalse(simulation.mission10_answer_matches('b1241 + b0351', complete))

    def test_old_version2_report_is_rejected(self):
        stale = {
            'mission_id': '10',
            'check_version': 2,
            'ready_to_deliver': True,
            'target_pair_found': True,
        }
        self.assertFalse(simulation.mission10_answer_matches('b2297+b2458', stale))
        text = simulation.build_mission10_evidence_report_text(stale)
        self.assertIn('Build a controlled anaerobic', text)
        self.assertNotIn('Evidence complete', text)

    def test_explicit_empty_report_does_not_load_saved_evidence(self):
        completed = self._complete_report()
        with patch.object(simulation, 'load_mission10_robust_design_check', return_value=completed) as loader:
            text = simulation.build_mission10_evidence_report_text({})
            self.assertFalse(simulation.mission10_answer_matches('b2297+b2458', {}))
        loader.assert_not_called()
        self.assertIn('Build a controlled anaerobic', text)
        self.assertNotIn('Evidence complete', text)

    def test_report_explains_or_redundancy_and_uses_no_cross_objective_values(self):
        report = self._complete_report()
        text = simulation.build_mission10_evidence_report_text(report)
        self.assertIn('OR-type GPR redundancy', text)
        self.assertIn('same visible biomass-optimal FBA solution', text)
        self.assertIn('b2297 (pta) + b2458 (eutD)', text)
        self.assertNotIn('D-lactate', text)
        self.assertNotIn('hidden product objective is used to calculate', text)

    def test_remote_wrapper_reuses_visible_result_without_hidden_requests(self):
        visible = object()
        expected = {'visible': True}
        with patch.object(simulation, 'run_mission10_robust_design_check', return_value=expected) as runner:
            observed = simulation.run_mission10_robust_design_check_remote('unused-url', visible)
        self.assertIs(observed, expected)
        runner.assert_called_once_with(visible)

    def test_local_checker_contains_no_hidden_simulation_calls(self):
        source = inspect.getsource(simulation.run_mission10_robust_design_check)
        self.assertNotIn('_simulate_flux_in_biomass_solution', source)
        self.assertNotIn('simulate(', source)
        self.assertIn('simulation_results', source)

    def test_mission_ui_has_progression_guard_clear_and_answer_input(self):
        source = (CODE_DIR / 'mission10.py').read_text(encoding='utf-8')
        self.assertIn('is_mission10_unlocked', source)
        self.assertIn('clear_mission10_robust_design_check()', source)
        self.assertIn("text_input('Winning gene pair: '", source)
        self.assertIn('mission10_answer_matches', source)

    def test_ethanol_and_acetate_are_fixed_at_maximum_growth(self):
        try:
            from cobra.flux_analysis import flux_variability_analysis
        except Exception as exc:
            self.skipTest(f'COBRApy FVA unavailable: {exc}')

        expected = {
            'baseline': ((), 8.279455, 8.503585),
            'b2297+b2458': (('b2297', 'b2458'), 16.584256, 0.0),
            'b2297+b1241': (('b2297', 'b1241'), 8.279455, 8.503585),
            'b2297+b0351': (('b2297', 'b0351'), 8.279455, 8.503585),
            'b2458+b1241': (('b2458', 'b1241'), 8.279455, 8.503585),
            'b2458+b0351': (('b2458', 'b0351'), 8.279455, 8.503585),
            'b1241+b0351': (('b1241', 'b0351'), 0.0, 0.146027),
        }
        for label, (genes, expected_ethanol, expected_acetate) in expected.items():
            model = simulation.model.copy()
            model.reactions.get_by_id(simulation.MISSION10_OXYGEN_REACTION).lower_bound = 0.0
            for reaction_id in disabled_reaction_ids(model, set(genes)):
                model.reactions.get_by_id(reaction_id).bounds = (0.0, 0.0)
            model.objective = simulation.MISSION10_GROWTH_OBJECTIVE
            solution = model.optimize()
            self.assertEqual(solution.status, 'optimal', label)
            fva = flux_variability_analysis(
                model,
                reaction_list=[simulation.MISSION10_TARGET_FLUX, simulation.MISSION10_COMPETING_FLUX],
                fraction_of_optimum=1.0,
            )
            for reaction_id, expected_value in (
                (simulation.MISSION10_TARGET_FLUX, expected_ethanol),
                (simulation.MISSION10_COMPETING_FLUX, expected_acetate),
            ):
                minimum = float(fva.loc[reaction_id, 'minimum'])
                maximum = float(fva.loc[reaction_id, 'maximum'])
                self.assertAlmostEqual(minimum, maximum, delta=1e-4, msg=f'{label}:{reaction_id}')
                self.assertAlmostEqual(minimum, expected_value, delta=1e-3, msg=f'{label}:{reaction_id}')


if __name__ == '__main__':
    unittest.main()
