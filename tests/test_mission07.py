"""Regression tests for Mission 07 controlled objective comparison.

Run from the project root with:
    python3 -m unittest discover -s tests -p "test_mission07.py"
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


class Mission07RegressionTests(unittest.TestCase):
    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.reactions = simulation._build_default_reactions_data()

    def _simulate(self, objective, method=None, genes=None, reactions=None):
        genes = dict(genes or self.genes)
        reactions = reactions or self.reactions
        simul, constraints = simulation._build_local_constraints(genes, reactions)
        simul.objective = objective
        result = simul.simulate(
            method=method or simulation.MISSION07_METHOD,
            constraints=constraints,
        )
        objective_result = simulation._normalise_result(result)
        flux_getter = lambda reaction_id: simulation._extract_flux(result, reaction_id)
        production_fluxes = simulation._build_production_flux_data(
            [simulation.MISSION07_TARGET_FLUX],
            flux_getter=flux_getter,
        )
        objective_raw = simulation._as_float_or_none(
            simulation._extract_flux(result, objective)
        )
        if objective_raw is not None:
            production_fluxes['objective_raw'] = objective_raw
        biomass_raw = simulation._as_float_or_none(
            simulation._extract_flux(result, simulation.MISSION07_BIOMASS_OBJECTIVE)
        )
        if biomass_raw is not None:
            production_fluxes['biomass_raw'] = biomass_raw
        medium_fluxes = simulation._build_medium_flux_data(flux_getter=flux_getter)
        return objective_result, production_fluxes, medium_fluxes, genes, result

    def _record(
        self,
        objective,
        report=None,
        method=None,
        genes=None,
        reactions=None,
        tracked=True,
        objective_result=None,
        production_fluxes=None,
        medium_fluxes=None,
    ):
        genes = dict(genes or self.genes)
        reactions = reactions or self.reactions
        if objective_result is None and production_fluxes is None and medium_fluxes is None:
            objective_result, production_fluxes, medium_fluxes, genes, _result = self._simulate(
                objective,
                method=method,
                genes=genes,
                reactions=reactions,
            )
        selected = [simulation.MISSION07_TARGET_FLUX] if tracked else []
        with (
            patch.object(simulation, 'save_mission07_objective_check'),
            patch.object(simulation, '_read_selected_production_fluxes', return_value=selected),
        ):
            return simulation._build_mission07_data(
                method or simulation.MISSION07_METHOD,
                objective,
                objective_result,
                genes,
                reactions,
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                existing_report=report,
            )

    @staticmethod
    def _synthetic_flux_data(biomass, ethanol, oxygen_uptake, include_biomass=True):
        production = {
            'selected_ids': [simulation.MISSION07_TARGET_FLUX],
            'objective_raw': float(ethanol),
            'items': [{
                'reaction_id': simulation.MISSION07_TARGET_FLUX,
                'raw_flux': float(ethanol),
                'production_flux': round(max(float(ethanol), 0.0), 3),
            }],
        }
        if include_biomass:
            production['biomass_raw'] = float(biomass)
        medium = {
            'items': [{
                'reaction_id': simulation.MISSION07_OXYGEN_REACTION,
                'raw_flux': -float(oxygen_uptake),
                'uptake_flux': float(oxygen_uptake),
                'secretion_flux': 0.0,
            }],
        }
        return production, medium

    def test_progression_requires_mission06(self):
        self.assertFalse(simulation.is_mission07_unlocked([]))
        self.assertFalse(simulation.is_mission07_unlocked(['05']))
        self.assertTrue(simulation.is_mission07_unlocked(['06']))

    def test_biomass_objective_reference_values(self):
        report = self._record(simulation.MISSION07_BIOMASS_OBJECTIVE)
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertTrue(report['reference_recorded'])
        self.assertFalse(report['target_recorded'])
        reference = report['reference_run']
        self.assertAlmostEqual(reference['biomass_flux'], 0.873922, places=3)
        self.assertAlmostEqual(reference['ethanol_flux'], 0.0, places=3)
        self.assertAlmostEqual(reference['oxygen_uptake'], 21.799493, places=3)
        self.assertFalse(report['evidence_ready'])

    def test_ethanol_objective_values_include_zero_biomass_from_same_solution(self):
        report = self._record(simulation.MISSION07_TARGET_OBJECTIVE)
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertFalse(report['reference_recorded'])
        self.assertTrue(report['target_recorded'])
        target = report['target_run']
        self.assertAlmostEqual(target['ethanol_flux'], 20.0, places=3)
        self.assertAlmostEqual(target['biomass_flux'], 0.0, places=3)
        self.assertAlmostEqual(target['oxygen_uptake'], 0.0, places=3)
        self.assertFalse(report['evidence_ready'])

    def test_both_runs_are_required_and_can_be_recorded_in_either_order(self):
        target_first = self._record(simulation.MISSION07_TARGET_OBJECTIVE)
        self.assertFalse(target_first['evidence_ready'])
        complete = self._record(
            simulation.MISSION07_BIOMASS_OBJECTIVE,
            report=target_first,
        )
        self.assertTrue(complete['reference_recorded'])
        self.assertTrue(complete['target_recorded'])
        self.assertTrue(complete['evidence_ready'])
        self.assertTrue(complete['ready_to_deliver'])

    def test_repeated_run_updates_one_slot_without_losing_other_evidence(self):
        report = self._record(simulation.MISSION07_BIOMASS_OBJECTIVE)
        report = self._record(simulation.MISSION07_TARGET_OBJECTIVE, report=report)
        original_target = dict(report['target_run'])
        report = self._record(simulation.MISSION07_BIOMASS_OBJECTIVE, report=report)
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['target_run'], original_target)
        self.assertEqual(report['current_run_type'], 'reference')

    def test_invalid_runs_do_not_erase_complete_evidence(self):
        report = self._record(simulation.MISSION07_BIOMASS_OBJECTIVE)
        report = self._record(simulation.MISSION07_TARGET_OBJECTIVE, report=report)
        expected_reference = dict(report['reference_run'])
        expected_target = dict(report['target_run'])

        changed_environment = dict(self.reactions)
        oxygen_index = list(simulation.REACTIONS.index).index('EX_o2_e')
        changed_environment[f'reaction_{oxygen_index}_lb'] = False
        knocked_out = dict(self.genes)
        knocked_out['b2278'] = False
        product, medium = self._synthetic_flux_data(0.0, 20.0, 0.0)

        cases = [
            dict(method='pFBA', message='Use FBA'),
            dict(reactions=changed_environment, message='default medium'),
            dict(genes=knocked_out, message='all genes active'),
            dict(tracked=False, message='Track EX_etoh_e'),
            dict(objective='EX_ac_e', message='Compare only'),
        ]
        for case in cases:
            candidate = self._record(
                case.get('objective', simulation.MISSION07_TARGET_OBJECTIVE),
                report=report,
                method=case.get('method'),
                genes=case.get('genes'),
                reactions=case.get('reactions'),
                tracked=case.get('tracked', True),
                objective_result=20.0,
                production_fluxes=product,
                medium_fluxes=medium,
            )
            self.assertFalse(candidate['current_run_valid'])
            self.assertEqual(candidate['reference_run'], expected_reference)
            self.assertEqual(candidate['target_run'], expected_target)
            self.assertTrue(candidate['evidence_ready'])
            self.assertTrue(any(case['message'] in issue for issue in candidate['current_issues']))

    def test_target_run_requires_biomass_flux_from_visible_solution(self):
        product, medium = self._synthetic_flux_data(
            biomass=0.0,
            ethanol=20.0,
            oxygen_uptake=0.0,
            include_biomass=False,
        )
        candidate = self._record(
            simulation.MISSION07_TARGET_OBJECTIVE,
            objective_result=20.0,
            production_fluxes=product,
            medium_fluxes=medium,
        )
        self.assertFalse(candidate['current_run_valid'])
        self.assertTrue(any('biomass' in issue.lower() for issue in candidate['current_issues']))
        self.assertFalse(candidate['target_recorded'])

    def test_target_run_rejects_positive_growth_even_with_high_ethanol(self):
        product, medium = self._synthetic_flux_data(0.1, 20.0, 0.0)
        candidate = self._record(
            simulation.MISSION07_TARGET_OBJECTIVE,
            objective_result=20.0,
            production_fluxes=product,
            medium_fluxes=medium,
        )
        self.assertFalse(candidate['current_run_valid'])
        self.assertTrue(any('no predicted growth' in issue for issue in candidate['current_issues']))

    def test_legacy_single_run_report_is_discarded(self):
        legacy = {
            'mission_id': '07',
            'check_version': 2,
            'selected_objective': simulation.MISSION07_TARGET_OBJECTIVE,
            'ready_to_deliver': True,
        }
        report = self._record(
            simulation.MISSION07_BIOMASS_OBJECTIVE,
            report=legacy,
        )
        self.assertTrue(report['reference_recorded'])
        self.assertFalse(report['target_recorded'])
        self.assertFalse(report['evidence_ready'])
        self.assertEqual(report['check_version'], 3)

    def test_explicit_empty_state_does_not_load_or_invent_old_evidence(self):
        report = self._record(
            simulation.MISSION07_BIOMASS_OBJECTIVE,
            report={},
        )
        self.assertTrue(report['reference_recorded'])
        self.assertFalse(report['target_recorded'])

    def test_report_compares_flux_profiles_without_subtracting_objective_values(self):
        report = self._record(simulation.MISSION07_BIOMASS_OBJECTIVE)
        report = self._record(simulation.MISSION07_TARGET_OBJECTIVE, report=report)
        text = simulation.build_mission07_objective_comparison_report_text(report)
        self.assertIn('Biomass-objective run', text)
        self.assertIn('Ethanol-objective run', text)
        self.assertIn('must not be subtracted', text)
        self.assertNotIn('19.126', text)
        self.assertNotIn('Objective delta', text)
        self.assertIn('no predicted growth', text)

    def test_validator_never_launches_a_hidden_simulation(self):
        source = inspect.getsource(simulation.run_mission07_objective_check)
        builder_source = inspect.getsource(simulation._build_mission07_data)
        self.assertNotIn('.simulate(', source)
        self.assertNotIn('.simulate(', builder_source)
        self.assertNotIn('_simulate_', source)
        self.assertNotIn('_simulate_', builder_source)

    def test_web_result_preserves_biomass_flux_from_backend_solution(self):
        fake_response = {
            'status': 'ok',
            'objective': simulation.MISSION07_TARGET_OBJECTIVE,
            'result': 20.0,
            'fluxes': {
                simulation.MISSION07_TARGET_OBJECTIVE: 20.0,
                simulation.MISSION07_BIOMASS_OBJECTIVE: 0.0,
                simulation.MISSION07_OXYGEN_REACTION: 0.0,
            },
        }
        payload = {
            'method': simulation.MISSION07_METHOD,
            'objective': simulation.MISSION07_TARGET_OBJECTIVE,
            'gene_knockouts': [],
            'env_conditions': {},
        }
        with (
            patch.object(simulation, '_build_request_payload', return_value=payload),
            patch.object(simulation, '_read_selected_production_fluxes', return_value=[simulation.MISSION07_TARGET_FLUX]),
            patch.object(simulation, '_http_post_json', return_value=fake_response),
        ):
            result = simulation.run_simul_remote('http://example.invalid')
        self.assertEqual(result[0], simulation.MISSION07_TARGET_OBJECTIVE)
        self.assertAlmostEqual(result[2]['biomass_raw'], 0.0, places=6)
        self.assertAlmostEqual(
            simulation._mission07_target_flux(result[2]),
            20.0,
            places=6,
        )

    def test_objective_optima_are_flux_robust(self):
        try:
            from cobra.flux_analysis import flux_variability_analysis
        except Exception as exc:  # pragma: no cover
            self.skipTest(f'COBRApy FVA unavailable: {exc}')

        biomass_model = simulation.model.copy()
        biomass_model.objective = simulation.MISSION07_BIOMASS_OBJECTIVE
        solution = biomass_model.optimize()
        self.assertEqual(solution.status, 'optimal')
        biomass_fva = flux_variability_analysis(
            biomass_model,
            reaction_list=[simulation.MISSION07_TARGET_FLUX],
            fraction_of_optimum=1.0,
        )
        self.assertAlmostEqual(
            float(biomass_fva.loc[simulation.MISSION07_TARGET_FLUX, 'minimum']),
            0.0,
            delta=1e-5,
        )
        self.assertAlmostEqual(
            float(biomass_fva.loc[simulation.MISSION07_TARGET_FLUX, 'maximum']),
            0.0,
            delta=1e-5,
        )

        ethanol_model = simulation.model.copy()
        ethanol_model.objective = simulation.MISSION07_TARGET_OBJECTIVE
        solution = ethanol_model.optimize()
        self.assertEqual(solution.status, 'optimal')
        ethanol_fva = flux_variability_analysis(
            ethanol_model,
            reaction_list=[
                simulation.MISSION07_BIOMASS_OBJECTIVE,
                simulation.MISSION07_OXYGEN_REACTION,
            ],
            fraction_of_optimum=1.0,
        )
        for reaction_id in (
            simulation.MISSION07_BIOMASS_OBJECTIVE,
            simulation.MISSION07_OXYGEN_REACTION,
        ):
            self.assertAlmostEqual(
                float(ethanol_fva.loc[reaction_id, 'minimum']),
                0.0,
                delta=1e-5,
            )
            self.assertAlmostEqual(
                float(ethanol_fva.loc[reaction_id, 'maximum']),
                0.0,
                delta=1e-5,
            )


if __name__ == '__main__':
    unittest.main()
