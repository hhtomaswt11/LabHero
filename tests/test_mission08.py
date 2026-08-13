"""Regression tests for Mission 08 constraint-impact comparison.

Run from the project root with:
    python3 tests/test_mission08.py
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


class Mission08RegressionTests(unittest.TestCase):
    def setUp(self):
        self.genes = simulation._build_active_genes_data()
        self.default_reactions = simulation._build_default_reactions_data()
        self.constrained_reactions = dict(self.default_reactions)
        oxygen_index = list(simulation.REACTIONS.index).index(
            simulation.MISSION08_OXYGEN_REACTION
        )
        self.constrained_reactions[f'reaction_{oxygen_index}_lb'] = False

    def _simulate(self, reactions=None):
        reactions = reactions or self.default_reactions
        simul, constraints = simulation._build_local_constraints(
            self.genes,
            reactions,
        )
        simul.objective = simulation.MISSION08_TARGET_OBJECTIVE
        result = simul.simulate(
            method=simulation.MISSION08_METHOD,
            constraints=constraints,
        )
        objective_result = simulation._normalise_result(result)
        flux_getter = lambda reaction_id: simulation._extract_flux(result, reaction_id)
        production_fluxes = simulation._build_production_flux_data(
            [simulation.MISSION08_TARGET_FLUX],
            flux_getter=flux_getter,
        )
        objective_raw = simulation._as_float_or_none(
            simulation._extract_flux(result, simulation.MISSION08_TARGET_OBJECTIVE)
        )
        if objective_raw is not None:
            production_fluxes['objective_raw'] = objective_raw
        biomass_raw = simulation._as_float_or_none(
            simulation._extract_flux(result, simulation.MISSION08_BIOMASS_OBJECTIVE)
        )
        if biomass_raw is not None:
            production_fluxes['biomass_raw'] = biomass_raw
        medium_fluxes = simulation._build_medium_flux_data(flux_getter=flux_getter)
        return objective_result, production_fluxes, medium_fluxes

    def _record(
        self,
        reactions=None,
        report=None,
        method=None,
        objective=None,
        genes=None,
        tracked=True,
        objective_result=None,
        production_fluxes=None,
        medium_fluxes=None,
    ):
        reactions = reactions or self.default_reactions
        genes = dict(genes or self.genes)
        objective = objective or simulation.MISSION08_TARGET_OBJECTIVE
        if objective_result is None and production_fluxes is None and medium_fluxes is None:
            objective_result, production_fluxes, medium_fluxes = self._simulate(
                reactions=reactions,
            )
        selected = [simulation.MISSION08_TARGET_FLUX] if tracked else []
        with (
            patch.object(simulation, 'save_mission08_constraint_check'),
            patch.object(simulation, '_read_selected_production_fluxes', return_value=selected),
        ):
            return simulation._build_mission08_data(
                method or simulation.MISSION08_METHOD,
                objective,
                objective_result,
                genes,
                reactions,
                production_fluxes=production_fluxes,
                medium_fluxes=medium_fluxes,
                existing_report=report,
            )

    @staticmethod
    def _synthetic_flux_data(
        d_lactate=20.0,
        biomass=0.0,
        oxygen_uptake=0.0,
        include_biomass=True,
        include_oxygen=True,
    ):
        production = {
            'selected_ids': [simulation.MISSION08_TARGET_FLUX],
            'objective_raw': float(d_lactate),
            'items': [{
                'reaction_id': simulation.MISSION08_TARGET_FLUX,
                'raw_flux': float(d_lactate),
                'production_flux': round(max(float(d_lactate), 0.0), 3),
            }],
        }
        if include_biomass:
            production['biomass_raw'] = float(biomass)
        medium = {'items': []}
        if include_oxygen:
            medium['items'].append({
                'reaction_id': simulation.MISSION08_OXYGEN_REACTION,
                'raw_flux': -float(oxygen_uptake),
                'uptake_flux': float(oxygen_uptake),
                'secretion_flux': 0.0,
            })
        return production, medium

    def _complete_report(self):
        report = self._record(reactions=self.default_reactions)
        return self._record(
            reactions=self.constrained_reactions,
            report=report,
        )

    def test_progression_requires_mission07(self):
        self.assertFalse(simulation.is_mission08_unlocked([]))
        self.assertFalse(simulation.is_mission08_unlocked(['06']))
        self.assertTrue(simulation.is_mission08_unlocked(['07']))

    def test_product_and_reaction_use_specific_d_lactate_terminology(self):
        self.assertEqual(simulation.MISSION08_TARGET_PRODUCT, 'D-lactate')
        self.assertEqual(simulation.MISSION08_TARGET_OBJECTIVE, 'EX_lac__D_e')
        self.assertEqual(simulation.MISSION08_TARGET_FLUX, 'EX_lac__D_e')

    def test_default_medium_direct_d_lactate_optimum(self):
        report = self._record(reactions=self.default_reactions)
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertTrue(report['default_recorded'])
        self.assertFalse(report['constrained_recorded'])
        run = report['default_run']
        self.assertAlmostEqual(run['d_lactate_flux'], 20.0, places=3)
        self.assertAlmostEqual(run['biomass_flux'], 0.0, places=3)
        self.assertAlmostEqual(run['oxygen_uptake'], 0.0, places=3)
        self.assertEqual(run['environment_type'], 'default')
        self.assertFalse(report['evidence_ready'])

    def test_oxygen_constrained_direct_d_lactate_optimum(self):
        report = self._record(reactions=self.constrained_reactions)
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertFalse(report['default_recorded'])
        self.assertTrue(report['constrained_recorded'])
        run = report['constrained_run']
        self.assertAlmostEqual(run['d_lactate_flux'], 20.0, places=3)
        self.assertAlmostEqual(run['biomass_flux'], 0.0, places=3)
        self.assertAlmostEqual(run['oxygen_uptake'], 0.0, places=3)
        self.assertEqual(run['environment_type'], 'oxygen_constrained')
        self.assertFalse(report['evidence_ready'])

    def test_both_runs_required_and_can_be_recorded_in_either_order(self):
        constrained_first = self._record(reactions=self.constrained_reactions)
        self.assertFalse(constrained_first['evidence_ready'])
        complete = self._record(
            reactions=self.default_reactions,
            report=constrained_first,
        )
        self.assertTrue(complete['default_recorded'])
        self.assertTrue(complete['constrained_recorded'])
        self.assertTrue(complete['fluxes_equivalent'])
        self.assertTrue(complete['optimum_unchanged'])
        self.assertTrue(complete['evidence_ready'])
        self.assertTrue(complete['ready_to_deliver'])

    def test_repeated_run_updates_one_slot_without_losing_other_evidence(self):
        report = self._complete_report()
        original_constrained = dict(report['constrained_run'])
        report = self._record(
            reactions=self.default_reactions,
            report=report,
        )
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['constrained_run'], original_constrained)
        self.assertEqual(report['current_run_type'], 'default')

    def test_invalid_runs_do_not_erase_complete_evidence(self):
        report = self._complete_report()
        expected_default = dict(report['default_run'])
        expected_constrained = dict(report['constrained_run'])
        product, medium = self._synthetic_flux_data()

        knocked_out = dict(self.genes)
        knocked_out['b2278'] = False
        extra_environment = dict(self.default_reactions)
        glucose_index = list(simulation.REACTIONS.index).index('EX_glc__D_e')
        extra_environment[f'reaction_{glucose_index}_lb'] = False

        cases = [
            dict(method='pFBA', message='Use FBA'),
            dict(method='lMOMA', message='Use FBA'),
            dict(method='ROOM', message='Use FBA'),
            dict(objective='EX_etoh_e', message='EX_lac__D_e'),
            dict(genes=knocked_out, message='all genes active'),
            dict(reactions=extra_environment, message='environmental bounds'),
            dict(tracked=False, message='Track EX_lac__D_e'),
        ]
        for case in cases:
            candidate = self._record(
                report=report,
                reactions=case.get('reactions', self.default_reactions),
                method=case.get('method'),
                objective=case.get('objective'),
                genes=case.get('genes'),
                tracked=case.get('tracked', True),
                objective_result=20.0,
                production_fluxes=product,
                medium_fluxes=medium,
            )
            self.assertFalse(candidate['current_run_valid'])
            self.assertEqual(candidate['default_run'], expected_default)
            self.assertEqual(candidate['constrained_run'], expected_constrained)
            self.assertTrue(candidate['evidence_ready'])
            self.assertTrue(any(case['message'] in issue for issue in candidate['current_issues']))

    def test_visible_solution_must_include_biomass_and_oxygen(self):
        product, medium = self._synthetic_flux_data(include_biomass=False)
        missing_biomass = self._record(
            objective_result=20.0,
            production_fluxes=product,
            medium_fluxes=medium,
        )
        self.assertFalse(missing_biomass['current_run_valid'])
        self.assertTrue(any('biomass' in issue.lower() for issue in missing_biomass['current_issues']))

        product, medium = self._synthetic_flux_data(include_oxygen=False)
        missing_oxygen = self._record(
            objective_result=20.0,
            production_fluxes=product,
            medium_fluxes=medium,
        )
        self.assertFalse(missing_oxygen['current_run_valid'])
        self.assertTrue(any('oxygen' in issue.lower() for issue in missing_oxygen['current_issues']))

    def test_direct_optimum_rejects_positive_growth_or_oxygen_use(self):
        product, medium = self._synthetic_flux_data(biomass=0.1)
        positive_growth = self._record(
            objective_result=20.0,
            production_fluxes=product,
            medium_fluxes=medium,
        )
        self.assertFalse(positive_growth['current_run_valid'])
        self.assertTrue(any('no predicted growth' in issue for issue in positive_growth['current_issues']))

        product, medium = self._synthetic_flux_data(oxygen_uptake=1.0)
        oxygen_using = self._record(
            objective_result=20.0,
            production_fluxes=product,
            medium_fluxes=medium,
        )
        self.assertFalse(oxygen_using['current_run_valid'])
        self.assertTrue(any('zero oxygen uptake' in issue for issue in oxygen_using['current_issues']))

    def test_objective_value_must_match_visible_d_lactate_flux(self):
        product, medium = self._synthetic_flux_data(d_lactate=18.0)
        candidate = self._record(
            objective_result=20.0,
            production_fluxes=product,
            medium_fluxes=medium,
        )
        self.assertFalse(candidate['current_run_valid'])
        self.assertTrue(any('does not match' in issue for issue in candidate['current_issues']))

    def test_legacy_single_run_report_is_discarded(self):
        legacy = {
            'mission_id': '08',
            'check_version': 2,
            'selected_objective': simulation.MISSION08_TARGET_OBJECTIVE,
            'oxygen_lower_bound_closed': True,
            'ready_to_deliver': True,
        }
        report = self._record(
            reactions=self.default_reactions,
            report=legacy,
        )
        self.assertTrue(report['default_recorded'])
        self.assertFalse(report['constrained_recorded'])
        self.assertFalse(report['evidence_ready'])
        self.assertEqual(report['check_version'], 4)

    def test_explicit_empty_state_does_not_load_or_invent_old_evidence(self):
        report = self._record(
            reactions=self.default_reactions,
            report={},
        )
        self.assertTrue(report['default_recorded'])
        self.assertFalse(report['constrained_recorded'])

    def test_report_identifies_unchanged_optimum_without_causal_claim(self):
        report = self._complete_report()
        text = simulation.build_mission08_constraint_comparison_report_text(report)
        self.assertIn('Default-medium run', text)
        self.assertIn('Oxygen-constrained run', text)
        self.assertIn('did not change the direct D-lactate optimum', text)
        self.assertIn('closing oxygen did not increase', text)
        self.assertIn('already used zero oxygen', text)
        self.assertIn('no predicted growth', text)
        self.assertNotIn('Constrained production setup found', text)
        self.assertNotIn('oxygen increased D-lactate', text)

    def test_incomplete_report_does_not_reveal_unchanged_optimum_conclusion(self):
        report = self._record(reactions=self.default_reactions)
        text = simulation.build_mission08_constraint_comparison_report_text(report)
        self.assertIn('Evidence incomplete', text)
        self.assertIn('do not decide whether closing oxygen changes the optimum', text)
        self.assertNotIn('closing oxygen did not increase', text)
        self.assertNotIn('did not change the direct D-lactate optimum', text)

    def test_validator_never_launches_a_hidden_simulation(self):
        source = inspect.getsource(simulation.run_mission08_constraint_check)
        builder_source = inspect.getsource(simulation._build_mission08_data)
        self.assertNotIn('.simulate(', source)
        self.assertNotIn('.simulate(', builder_source)
        self.assertNotIn('_simulate_', source)
        self.assertNotIn('_simulate_', builder_source)

    def test_web_result_preserves_biomass_and_d_lactate_from_backend_solution(self):
        fake_response = {
            'status': 'ok',
            'objective': simulation.MISSION08_TARGET_OBJECTIVE,
            'result': 20.0,
            'fluxes': {
                simulation.MISSION08_TARGET_OBJECTIVE: 20.0,
                simulation.MISSION08_BIOMASS_OBJECTIVE: 0.0,
                simulation.MISSION08_OXYGEN_REACTION: 0.0,
            },
        }
        payload = {
            'method': simulation.MISSION08_METHOD,
            'objective': simulation.MISSION08_TARGET_OBJECTIVE,
            'gene_knockouts': [],
            'env_conditions': {},
        }
        with (
            patch.object(simulation, '_build_request_payload', return_value=payload),
            patch.object(simulation, '_read_selected_production_fluxes', return_value=[simulation.MISSION08_TARGET_FLUX]),
            patch.object(simulation, '_http_post_json', return_value=fake_response),
        ):
            result = simulation.run_simul_remote('http://example.invalid')
        self.assertEqual(result[0], simulation.MISSION08_TARGET_OBJECTIVE)
        self.assertAlmostEqual(result[2]['biomass_raw'], 0.0, places=6)
        self.assertAlmostEqual(simulation._mission08_target_flux(result[2]), 20.0, places=6)

    def test_default_and_constrained_runs_robustly_preserve_the_same_optimum(self):
        try:
            from cobra.flux_analysis import flux_variability_analysis
        except Exception as exc:  # pragma: no cover
            self.skipTest(f'COBRApy FVA unavailable: {exc}')

        for oxygen_closed in (False, True):
            candidate_model = simulation.model.copy()
            candidate_model.objective = simulation.MISSION08_TARGET_OBJECTIVE
            if oxygen_closed:
                candidate_model.reactions.get_by_id(
                    simulation.MISSION08_OXYGEN_REACTION
                ).lower_bound = 0.0
            solution = candidate_model.optimize()
            self.assertEqual(solution.status, 'optimal')
            self.assertAlmostEqual(
                float(solution.objective_value),
                20.0,
                delta=1e-5,
            )
            fva = flux_variability_analysis(
                candidate_model,
                reaction_list=[
                    simulation.MISSION08_BIOMASS_OBJECTIVE,
                    simulation.MISSION08_OXYGEN_REACTION,
                ],
                fraction_of_optimum=1.0,
            )
            for reaction_id in (
                simulation.MISSION08_BIOMASS_OBJECTIVE,
                simulation.MISSION08_OXYGEN_REACTION,
            ):
                self.assertAlmostEqual(
                    float(fva.loc[reaction_id, 'minimum']),
                    0.0,
                    delta=1e-5,
                )
                self.assertAlmostEqual(
                    float(fva.loc[reaction_id, 'maximum']),
                    0.0,
                    delta=1e-5,
                )


if __name__ == '__main__':
    unittest.main()
