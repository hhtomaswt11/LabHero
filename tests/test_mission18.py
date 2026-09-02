"""Regression tests for Mission 18 binding export constraints.

Run from the project root with:
    python3 tests/test_mission18.py
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


class Mission18RegressionTests(unittest.TestCase):
    BASELINE_GROWTH = 0.211662950
    ACETATE_GROWTH = 0.189173105
    BASELINE_PROFILE = {
        'EX_ac_e': 8.503585278,
        'EX_etoh_e': 8.279455380,
        'EX_for_e': 17.804674218,
        'EX_succ_e': 0.0,
        'EX_lac__D_e': 0.0,
    }
    ACETATE_PROFILE = {
        'EX_ac_e': 0.0,
        'EX_etoh_e': 16.584255741,
        'EX_for_e': 3.956347393,
        'EX_succ_e': 0.0,
        'EX_lac__D_e': 0.0,
    }

    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.panel = list(simulation.MISSION18_REQUIRED_TRACKED_FLUXES)

    def _reactions(self, closed_upper=None):
        reactions = simulation._build_default_reactions_data()
        oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION18_OXYGEN_REACTION)
        reactions[f'reaction_{oxygen_index}_lb'] = False
        if closed_upper:
            export_index = list(simulation.REACTIONS.index).index(closed_upper)
            reactions[f'reaction_{export_index}_ub'] = False
        return reactions

    def _profile(self, closed_upper=None):
        if closed_upper == 'EX_ac_e':
            return dict(self.ACETATE_PROFILE)
        return dict(self.BASELINE_PROFILE)

    def _growth(self, closed_upper=None):
        return self.ACETATE_GROWTH if closed_upper == 'EX_ac_e' else self.BASELINE_GROWTH

    def _medium(self, closed_upper=None, missing=None, glucose_uptake=10.0, oxygen_uptake=0.0):
        missing = set(missing or [])
        raw = {
            simulation.MISSION18_GLUCOSE_REACTION: -float(glucose_uptake),
            simulation.MISSION18_OXYGEN_REACTION: -float(oxygen_uptake),
            **self._profile(closed_upper),
        }
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

    def _production(self, closed_upper=None, missing=None, override=None):
        missing = set(missing or [])
        values = self._profile(closed_upper)
        if override:
            values.update(override)
        return {
            'selected_ids': list(self.panel),
            'items': [
                {
                    'reaction_id': reaction_id,
                    'production_flux': float(values[reaction_id]),
                }
                for reaction_id in self.panel
                if reaction_id not in missing
            ],
        }

    def _record(
        self,
        closed_upper=None,
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
        if result is None:
            result = self._growth(closed_upper)
        if medium is None:
            medium = self._medium(closed_upper)
        if production is None:
            production = self._production(closed_upper)
        with patch.object(simulation, 'save_mission18_export_bottleneck_check'):
            return simulation._build_mission18_data(
                method or simulation.MISSION18_METHOD,
                objective or simulation.MISSION18_GROWTH_OBJECTIVE,
                result,
                dict(genes or self.genes),
                dict(reactions or self._reactions(closed_upper)),
                production_fluxes=production,
                medium_fluxes=medium,
                existing_report=report,
                selected_fluxes=list(self.panel if selected is None else selected),
                objective_error=error,
            )

    def _baseline(self):
        return self._record()

    def _complete_screen(self, order=None):
        report = self._baseline()
        for reaction_id in order or simulation.MISSION18_CANDIDATE_EXPORTS:
            report = self._record(reaction_id, report=report)
        return report

    def test_progression_and_redesign_constants(self):
        self.assertFalse(simulation.is_mission18_unlocked([]))
        self.assertFalse(simulation.is_mission18_unlocked(['16']))
        self.assertTrue(simulation.is_mission18_unlocked(['17']))
        self.assertEqual(simulation.MISSION18_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION18_CANDIDATE_EXPORTS, ['EX_ac_e', 'EX_succ_e'])
        self.assertNotIn('EX_pyr_e', simulation.MISSION18_REQUIRED_MEDIUM_FLUXES)
        self.assertFalse(hasattr(simulation, 'MISSION18_MIN_GROWTH'))
        self.assertEqual(len(simulation.MISSION18_REQUIRED_TRACKED_FLUXES), 5)

    def test_environment_reader_is_order_independent_and_legacy_compatible(self):
        reactions = self._reactions('EX_ac_e')
        status = simulation._mission18_environment_status(reactions)
        self.assertTrue(status['bounds_complete'])
        self.assertTrue(status['oxygen_lower_bound_closed'])
        self.assertEqual(status['closed_candidate_upper_bounds'], ['EX_ac_e'])
        self.assertEqual(status['unexpected_environment_changes'], [])
        self.assertEqual(simulation._mission18_environment_status(dict(reversed(list(reactions.items())))), status)
        legacy = {f'widget_{i}': value for i, value in enumerate(reactions.values())}
        legacy_status = simulation._mission18_environment_status(legacy)
        self.assertEqual(legacy_status['closed_candidate_upper_bounds'], ['EX_ac_e'])

    def test_incomplete_explicit_bounds_are_rejected(self):
        reactions = self._reactions()
        reactions.pop('reaction_0_ub')
        report = self._record(reactions=reactions)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('environmental-bound payload is incomplete', ' '.join(report['current_issues']))

    def test_baseline_records_anaerobic_growth_and_export_profile(self):
        report = self._baseline()
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertTrue(report['baseline_ready'])
        baseline = report['baseline_run']
        self.assertAlmostEqual(baseline['growth'], self.BASELINE_GROWTH, delta=1e-6)
        self.assertAlmostEqual(baseline['glucose_uptake'], 10.0, delta=1e-6)
        self.assertAlmostEqual(baseline['oxygen_uptake'], 0.0, delta=1e-6)
        for reaction_id, expected in self.BASELINE_PROFILE.items():
            self.assertAlmostEqual(baseline['tracked_flux_values'][reaction_id], expected, delta=1e-6)

    def test_candidate_trial_before_baseline_is_rejected(self):
        report = self._record('EX_ac_e')
        self.assertFalse(report['current_run_valid'])
        self.assertIn('anaerobic baseline', ' '.join(report['current_issues']))
        self.assertEqual(report['candidate_trials'], {})

    def test_acetate_upper_closure_records_viable_redistributed_profile(self):
        report = self._record('EX_ac_e', report=self._baseline())
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        trial = report['candidate_trials']['EX_ac_e']
        self.assertAlmostEqual(trial['growth'], self.ACETATE_GROWTH, delta=1e-6)
        self.assertGreaterEqual(trial['baseline_fraction'], simulation.MISSION18_MIN_BINDING_VIABILITY_RATIO)
        for reaction_id, expected in self.ACETATE_PROFILE.items():
            self.assertAlmostEqual(trial['tracked_flux_values'][reaction_id], expected, delta=1e-6)

    def test_succinate_upper_closure_records_baseline_like_control(self):
        report = self._record('EX_succ_e', report=self._baseline())
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        trial = report['candidate_trials']['EX_succ_e']
        self.assertAlmostEqual(trial['growth'], self.BASELINE_GROWTH, delta=1e-6)
        self.assertAlmostEqual(trial['baseline_fraction'], 1.0, delta=1e-6)
        self.assertEqual(trial['tracked_flux_values'], self._baseline()['baseline_run']['tracked_flux_values'])

    def test_complete_screen_derives_one_binding_and_one_nonbinding_constraint(self):
        report = self._complete_screen()
        self.assertTrue(report['screen_complete'])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['relationship_supported'])
        self.assertEqual(report['binding_candidates'], ['EX_ac_e'])
        self.assertEqual(report['nonbinding_candidates'], ['EX_succ_e'])
        self.assertEqual(report['intermediate_candidates'], [])

    def test_trial_order_is_irrelevant_and_repetition_updates_without_duplication(self):
        report = self._complete_screen(order=['EX_succ_e', 'EX_ac_e'])
        self.assertTrue(report['relationship_supported'])
        repeated = self._record('EX_succ_e', report=report)
        self.assertEqual(repeated['valid_trial_count'], 2)
        self.assertEqual(len(repeated['candidate_trials']), 2)

    def test_wrong_method_objective_or_knockout_is_rejected(self):
        baseline = self._baseline()
        self.assertFalse(self._record('EX_ac_e', report=baseline, method='pFBA')['current_run_valid'])
        self.assertFalse(self._record('EX_ac_e', report=baseline, objective='EX_etoh_e')['current_run_valid'])
        genes = dict(self.genes)
        genes[next(iter(genes))] = False
        self.assertFalse(self._record('EX_ac_e', report=baseline, genes=genes)['current_run_valid'])

    def test_environment_requires_oxygen_closure_and_only_one_candidate_upper_bound(self):
        reactions = simulation._build_default_reactions_data()
        no_oxygen_closure = self._record(reactions=reactions)
        self.assertFalse(no_oxygen_closure['current_run_valid'])
        self.assertIn('oxygen lower bound', ' '.join(no_oxygen_closure['current_issues']))

        baseline = self._baseline()
        reactions = self._reactions('EX_ac_e')
        succ_index = list(simulation.REACTIONS.index).index('EX_succ_e')
        reactions[f'reaction_{succ_index}_ub'] = False
        multiple = self._record('EX_ac_e', report=baseline, reactions=reactions)
        self.assertFalse(multiple['current_run_valid'])
        self.assertIn('exactly one', ' '.join(multiple['current_issues']))

    def test_medium_and_production_reports_are_mandatory_and_missing_is_not_zero(self):
        missing_medium = self._record(medium=self._medium(missing=['EX_ac_e']))
        self.assertFalse(missing_medium['current_run_valid'])
        self.assertIn('Exchange Flux Report is missing', ' '.join(missing_medium['current_issues']))

        missing_production = self._record(production=self._production(missing=['EX_ac_e']))
        self.assertFalse(missing_production['current_run_valid'])
        self.assertIn('Production Flux report is missing', ' '.join(missing_production['current_issues']))

    def test_complete_panel_must_be_selected_and_numeric_evidence_must_match(self):
        selected = [flux_id for flux_id in self.panel if flux_id != 'EX_lac__D_e']
        missing_selection = self._record(selected=selected)
        self.assertFalse(missing_selection['current_run_valid'])
        self.assertIn('complete Mission 18 product/byproduct panel', ' '.join(missing_selection['current_issues']))

        inconsistent = self._record(production=self._production(override={'EX_ac_e': 1.0}))
        self.assertFalse(inconsistent['current_run_valid'])
        self.assertIn('same visible solution', ' '.join(inconsistent['current_issues']))

    def test_glucose_and_oxygen_medium_controls_are_numerically_enforced(self):
        wrong_glucose = self._record(medium=self._medium(glucose_uptake=8.0))
        self.assertFalse(wrong_glucose['current_run_valid'])
        self.assertIn('default glucose uptake protocol', ' '.join(wrong_glucose['current_issues']))

        wrong_oxygen = self._record(medium=self._medium(oxygen_uptake=1.0))
        self.assertFalse(wrong_oxygen['current_run_valid'])
        self.assertIn('did not eliminate oxygen uptake', ' '.join(wrong_oxygen['current_issues']))

    def test_closed_candidate_export_must_be_numerically_zero(self):
        baseline = self._baseline()
        report = self._record(
            'EX_ac_e',
            report=baseline,
            production=self._production('EX_ac_e', override={'EX_ac_e': 0.5}),
            medium=self._medium('EX_ac_e'),
        )
        self.assertFalse(report['current_run_valid'])
        self.assertIn('did not block export', ' '.join(report['current_issues']))

    def test_invalid_attempt_preserves_complete_evidence(self):
        complete = self._complete_screen()
        invalid = self._record('EX_ac_e', report=complete, method='pFBA')
        self.assertFalse(invalid['current_run_recorded'])
        self.assertTrue(invalid['baseline_ready'])
        self.assertTrue(invalid['screen_complete'])
        self.assertTrue(invalid['evidence_ready'])
        text = simulation.build_mission18_binding_export_report_text(invalid)
        self.assertIn('Latest run was not recorded', text)
        self.assertIn('Previously valid Mission 18 evidence remains available', text)

    def test_direct_binding_route_answers_are_accepted_and_extras_rejected(self):
        report = self._complete_screen()
        for answer in ('acetate', 'EX_ac_e', 'acetate exchange', 'acetato'):
            self.assertTrue(simulation.mission18_answer_matches(answer, report), answer)
        for answer in ('succinate', 'EX_succ_e', 'ethanol', 'both', 'acetate and succinate', 'acetate and ethanol', 'acetate + formate'):
            self.assertFalse(simulation.mission18_answer_matches(answer, report), answer)
        self.assertFalse(simulation.mission18_answer_matches('acetate', self._baseline()))

    def test_report_presents_comparison_without_printing_the_answer(self):
        report = self._complete_screen()
        text = simulation.build_mission18_binding_export_report_text(report)
        self.assertIn('Baseline predicted growth rate: 0.212 h^-1', text)
        self.assertIn('Candidate trials recorded: 2/2', text)
        self.assertIn('predicted growth rate 0.189 h^-1; 89.4% of baseline', text)
        self.assertIn('predicted growth rate 0.212 h^-1; 100.0% of baseline', text)
        self.assertIn('Which upper-bound closure created', text)
        self.assertNotIn('Answer: acetate', text.lower())
        self.assertNotIn('Acetate is the binding constraint', text)

    def test_remote_wrapper_uses_visible_result_only_and_state_is_json_serialisable(self):
        report = self._complete_screen()
        json.dumps(report)
        source = inspect.getsource(simulation.run_mission18_export_bottleneck_check_remote)
        self.assertNotIn('_http_post_json', source)
        self.assertIn('run_mission18_export_bottleneck_check(simulation_results)', source)
        builder = inspect.getsource(simulation._build_mission18_data)
        self.assertNotIn('.simulate(', builder)
        self.assertNotIn('_simulate_', builder)

    def test_ui_and_documentation_match_the_reconstruction(self):
        source = (CODE_DIR / 'mission18.py').read_text(encoding='utf-8')
        self.assertIn('is_mission18_unlocked', source)
        self.assertIn('initialise_mission18_binding_export_screen()', source)
        self.assertIn("if '18' in self.missions_activated", source)
        self.assertIn('Binding export route:', source)
        self.assertIn('mission18_answer_matches', source)
        self.assertNotIn('EX_pyr_e', source)
        window = (CODE_DIR / 'window.py').read_text(encoding='utf-8')
        self.assertIn('run_mission18_export_bottleneck_check_remote', window)
        self.assertIn('build_mission18_binding_export_report_text', window)
        mission_doc = (PROJECT_ROOT / 'data' / 'missions' / 'mission18.md').read_text(encoding='utf-8')
        self.assertIn('Binding Export Constraints', mission_doc)
        self.assertIn('binding and non-binding', mission_doc)
        overview = (PROJECT_ROOT / 'MISSION_PROGRESS_OVERVIEW.md').read_text(encoding='utf-8')
        self.assertIn('Mission 18 — Binding Export Constraints', overview)

    def test_real_fba_values_for_baseline_and_two_upper_bound_trials(self):
        try:
            baseline_result, baseline_production, baseline_medium = simulation._simulate_local_objective_with_production_fluxes(
                simulation.MISSION18_METHOD,
                simulation.MISSION18_GROWTH_OBJECTIVE,
                dict(self.genes),
                self._reactions(),
                list(self.panel),
            )
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'MEWpy/COBRApy unavailable: {exc}')

        self.assertAlmostEqual(float(baseline_result), self.BASELINE_GROWTH, delta=1e-3)
        baseline_values = simulation._mission18_measured_production_values(baseline_production)
        for reaction_id, expected in self.BASELINE_PROFILE.items():
            self.assertAlmostEqual(baseline_values[reaction_id], expected, delta=1e-3)
        _raw, uptake, _secretion = simulation._medium_flux_maps(baseline_medium)
        self.assertAlmostEqual(uptake['EX_glc__D_e'], 10.0, delta=1e-3)
        self.assertAlmostEqual(uptake['EX_o2_e'], 0.0, delta=1e-3)

        for reaction_id, expected_growth, expected_profile in (
            ('EX_ac_e', self.ACETATE_GROWTH, self.ACETATE_PROFILE),
            ('EX_succ_e', self.BASELINE_GROWTH, self.BASELINE_PROFILE),
        ):
            result, production, _medium = simulation._simulate_local_objective_with_production_fluxes(
                simulation.MISSION18_METHOD,
                simulation.MISSION18_GROWTH_OBJECTIVE,
                dict(self.genes),
                self._reactions(reaction_id),
                list(self.panel),
            )
            self.assertAlmostEqual(float(result), expected_growth, delta=1e-3, msg=reaction_id)
            values = simulation._mission18_measured_production_values(production)
            for flux_id, expected in expected_profile.items():
                self.assertAlmostEqual(values[flux_id], expected, delta=1e-3, msg=(reaction_id, flux_id))

    def test_real_fva_confirms_binding_and_nonbinding_baseline_states(self):
        try:
            from cobra.flux_analysis import flux_variability_analysis
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'COBRApy FVA unavailable: {exc}')
        if simulation.model is None:
            self.skipTest('Desktop metabolic model unavailable in this runtime.')

        expected_profiles = {
            None: self.BASELINE_PROFILE,
            'EX_ac_e': self.ACETATE_PROFILE,
            'EX_succ_e': self.BASELINE_PROFILE,
        }
        for closed_upper, expected_profile in expected_profiles.items():
            model = simulation.model
            with model:
                model.reactions.get_by_id('EX_o2_e').lower_bound = 0.0
                if closed_upper:
                    model.reactions.get_by_id(closed_upper).upper_bound = 0.0
                fva = flux_variability_analysis(
                    model,
                    reaction_list=list(self.panel),
                    fraction_of_optimum=1.0,
                )
                for reaction_id, expected in expected_profile.items():
                    self.assertAlmostEqual(
                        float(fva.loc[reaction_id, 'minimum']),
                        expected,
                        delta=1e-3,
                        msg=(closed_upper, reaction_id, 'minimum'),
                    )
                    self.assertAlmostEqual(
                        float(fva.loc[reaction_id, 'maximum']),
                        expected,
                        delta=1e-3,
                        msg=(closed_upper, reaction_id, 'maximum'),
                    )


if __name__ == '__main__':
    unittest.main()
