"""Regression tests for Mission 19 method comparison.

Run from the project root with:
    python3 tests/test_mission19.py
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


class Mission19RegressionTests(unittest.TestCase):
    WT_GROWTH = 0.873921507
    FBA_MUTANT_GROWTH = 0.858307408
    LMOMA_MUTANT_GROWTH = 0.803444768
    LMOMA_SCORE = 39.785201039
    WT_PROFILE = {
        'EX_ac_e': 0.0,
        'EX_etoh_e': 0.0,
        'EX_for_e': 0.0,
        'EX_lac__D_e': 0.0,
        'EX_succ_e': 0.0,
    }
    FBA_MUTANT_PROFILE = dict(WT_PROFILE)
    LMOMA_MUTANT_PROFILE = {
        'EX_ac_e': 0.121755614,
        'EX_etoh_e': 0.0,
        'EX_for_e': 0.0,
        'EX_lac__D_e': 0.157367511,
        'EX_succ_e': 0.0,
    }

    def setUp(self):
        self.active_genes = simulation._build_active_genes_data()
        self.default_reactions = simulation._build_default_reactions_data()
        self.panel = list(simulation.MISSION19_REQUIRED_TRACKED_FLUXES)

    def _genes(self, knockout=None):
        genes = dict(self.active_genes)
        if knockout:
            genes[knockout] = False
        return genes

    def _production(self, method, growth, profile, score=None, missing=None, selected=None, biomass=None, primary=None, score_name=None):
        missing = set(missing or [])
        selected = list(self.panel if selected is None else selected)
        if biomass is None:
            biomass = growth
        if primary is None:
            primary = growth
        if score is None:
            score = growth if method == 'FBA' else self.LMOMA_SCORE
        if score_name is None:
            score_name = simulation._method_score_label(method)
        return {
            'selected_ids': selected,
            'items': [
                {
                    'reaction_id': reaction_id,
                    'production_flux': float(profile[reaction_id]),
                }
                for reaction_id in self.panel
                if reaction_id not in missing
            ],
            'biomass_raw': biomass,
            'method_diagnostics': {
                'method': method,
                'objective_reaction': simulation.MISSION19_GROWTH_OBJECTIVE,
                'primary_objective_flux': primary,
                'method_score': score,
                'method_score_name': score_name,
                'total_absolute_flux': None,
                'active_reaction_count': None,
            },
        }

    def _record(
        self,
        run_type,
        report=None,
        method=None,
        genes=None,
        reactions=None,
        objective=None,
        result=None,
        production=None,
        selected=None,
        error=None,
    ):
        if run_type == 'baseline':
            method = method or 'FBA'
            genes = genes or self._genes()
            result = self.WT_GROWTH if result is None else result
            production = production or self._production(method, result, self.WT_PROFILE)
        elif run_type == 'fba_mutant':
            method = method or 'FBA'
            genes = genes or self._genes(simulation.MISSION19_TARGET_GENE)
            result = self.FBA_MUTANT_GROWTH if result is None else result
            production = production or self._production(method, result, self.FBA_MUTANT_PROFILE)
        elif run_type == 'lmoma_mutant':
            method = method or 'lMOMA'
            genes = genes or self._genes(simulation.MISSION19_TARGET_GENE)
            result = self.LMOMA_MUTANT_GROWTH if result is None else result
            production = production or self._production(method, result, self.LMOMA_MUTANT_PROFILE, score=self.LMOMA_SCORE)
        else:
            method = method or 'pFBA'
            genes = genes or self._genes(simulation.MISSION19_TARGET_GENE)
            result = self.FBA_MUTANT_GROWTH if result is None else result
            production = production or self._production(method, result, self.FBA_MUTANT_PROFILE)

        with patch.object(simulation, 'save_mission19_perturbation_check'):
            return simulation._build_mission19_data(
                method,
                objective or simulation.MISSION19_GROWTH_OBJECTIVE,
                result,
                dict(genes),
                dict(reactions or self.default_reactions),
                production_fluxes=production,
                existing_report=report,
                selected_fluxes=list(self.panel if selected is None else selected),
                objective_error=error,
            )

    def _baseline(self):
        return self._record('baseline')

    def _complete(self, order=('fba_mutant', 'lmoma_mutant')):
        report = self._baseline()
        for run_type in order:
            report = self._record(run_type, report=report)
        return report

    def test_progression_and_redesign_constants(self):
        self.assertFalse(simulation.is_mission19_unlocked([]))
        self.assertFalse(simulation.is_mission19_unlocked(['17']))
        self.assertTrue(simulation.is_mission19_unlocked(['18']))
        self.assertEqual(simulation.MISSION19_CHECK_VERSION, 3)
        self.assertEqual(simulation.MISSION19_TARGET_GENE, 'b0728')
        self.assertEqual(simulation.MISSION19_TARGET_GENE_NAME, 'sucC')
        self.assertEqual(simulation.MISSION19_EXPECTED_DISABLED_REACTIONS, ['SUCOAS'])
        self.assertFalse(hasattr(simulation, 'MISSION19_MIN_GROWTH'))

    def test_gpr_effect_uses_sucoas_and_old_acka_target_is_noop(self):
        self.assertEqual(simulation._mission19_disabled_reactions(['b0728']), ['SUCOAS'])
        self.assertEqual(simulation._mission19_disabled_reactions(['b2296']), [])
        if simulation.model is not None:
            self.assertEqual(sorted(simulation.disabled_reaction_ids(simulation.model, ['b0728'])), ['SUCOAS'])
            self.assertEqual(simulation.disabled_reaction_ids(simulation.model, ['b2296']), [])

    def test_initial_state_is_json_serialisable(self):
        with patch.object(simulation, 'save_mission19_perturbation_check'):
            report = simulation.initialise_mission19_method_comparison()
        self.assertFalse(report['baseline_ready'])
        self.assertFalse(report['comparison_ready'])
        json.dumps(report)

    def test_wild_type_fba_baseline_records_visible_values(self):
        report = self._baseline()
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        self.assertTrue(report['baseline_ready'])
        self.assertEqual(report['current_run_type'], 'baseline')
        self.assertAlmostEqual(report['baseline_run']['growth'], self.WT_GROWTH, delta=1e-6)
        self.assertEqual(report['baseline_run']['tracked_flux_values'], self.WT_PROFILE)

    def test_mutant_run_before_baseline_is_rejected(self):
        report = self._record('fba_mutant')
        self.assertFalse(report['current_run_valid'])
        self.assertIn('wild-type FBA baseline', ' '.join(report['current_issues']))
        self.assertIsNone(report['fba_mutant_run'])

    def test_fba_mutant_records_real_gpr_effect_and_viable_growth(self):
        report = self._record('fba_mutant', report=self._baseline())
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        run = report['fba_mutant_run']
        self.assertEqual(run['knocked_out_genes'], ['b0728'])
        self.assertEqual(run['disabled_reactions'], ['SUCOAS'])
        self.assertAlmostEqual(run['growth'], self.FBA_MUTANT_GROWTH, delta=1e-6)

    def test_lmoma_mutant_records_biomass_score_and_flux_profile_separately(self):
        report = self._record('lmoma_mutant', report=self._baseline())
        self.assertTrue(report['current_run_valid'], report['current_issues'])
        run = report['lmoma_mutant_run']
        self.assertAlmostEqual(run['growth'], self.LMOMA_MUTANT_GROWTH, delta=1e-6)
        diagnostics = run['method_diagnostics']
        self.assertAlmostEqual(diagnostics['method_score'], self.LMOMA_SCORE, delta=1e-6)
        self.assertEqual(diagnostics['method_score_name'], simulation.MISSION19_LMOMA_SCORE_NAME)
        self.assertNotAlmostEqual(run['growth'], diagnostics['method_score'], delta=1e-3)
        self.assertAlmostEqual(run['tracked_flux_values']['EX_ac_e'], self.LMOMA_MUTANT_PROFILE['EX_ac_e'], delta=1e-6)
        self.assertAlmostEqual(run['tracked_flux_values']['EX_lac__D_e'], self.LMOMA_MUTANT_PROFILE['EX_lac__D_e'], delta=1e-6)

    def test_complete_comparison_derives_lower_viable_lmoma_response(self):
        report = self._complete()
        self.assertTrue(report['comparison_ready'])
        self.assertTrue(report['same_controlled_setup'])
        self.assertTrue(report['relationship_supported'])
        self.assertEqual(report['lower_biomass_method'], 'lMOMA')
        self.assertGreaterEqual(report['growth_ratios']['fba_mutant_vs_wt'], simulation.MISSION19_MIN_MUTANT_VIABILITY_RATIO)
        self.assertGreaterEqual(report['growth_ratios']['lmoma_mutant_vs_wt'], simulation.MISSION19_MIN_MUTANT_VIABILITY_RATIO)
        self.assertGreater(report['tracked_flux_differences']['EX_ac_e'], simulation.MISSION19_MIN_PROFILE_DIFFERENCE)

    def test_mutant_order_is_irrelevant_and_repetition_updates_without_loss(self):
        report = self._complete(order=('lmoma_mutant', 'fba_mutant'))
        self.assertTrue(report['relationship_supported'])
        repeated = self._record('fba_mutant', report=report)
        self.assertTrue(repeated['comparison_ready'])
        self.assertIsNotNone(repeated['lmoma_mutant_run'])

    def test_repeated_valid_baseline_preserves_mutant_evidence(self):
        report = self._complete()
        repeated = self._record('baseline', report=report)
        self.assertTrue(repeated['comparison_ready'])
        self.assertIsNotNone(repeated['fba_mutant_run'])
        self.assertIsNotNone(repeated['lmoma_mutant_run'])

    def test_wrong_objective_environment_or_gene_is_rejected(self):
        baseline = self._baseline()
        wrong_objective = self._record('fba_mutant', report=baseline, objective='EX_etoh_e')
        self.assertFalse(wrong_objective['current_run_valid'])

        reactions = dict(self.default_reactions)
        reactions['reaction_0_lb'] = not bool(reactions['reaction_0_lb'])
        wrong_environment = self._record('fba_mutant', report=baseline, reactions=reactions)
        self.assertFalse(wrong_environment['current_run_valid'])
        self.assertIn('environmental bound', ' '.join(wrong_environment['current_issues']))

        wrong_gene = self._record('fba_mutant', report=baseline, genes=self._genes('b2296'))
        self.assertFalse(wrong_gene['current_run_valid'])
        self.assertIn('b0728', ' '.join(wrong_gene['current_issues']))

    def test_only_fba_and_lmoma_are_valid_for_target_runs(self):
        baseline = self._baseline()
        invalid = self._record('invalid', report=baseline, method='pFBA')
        self.assertFalse(invalid['current_run_valid'])
        self.assertIn('FBA and lMOMA only', ' '.join(invalid['current_issues']))

    def test_complete_panel_must_be_selected_and_numerically_measured(self):
        baseline = self._baseline()
        selected = self.panel[:-1]
        missing_selection = self._record('fba_mutant', report=baseline, selected=selected)
        self.assertFalse(missing_selection['current_run_valid'])
        self.assertIn('complete Mission 19 product/byproduct panel', ' '.join(missing_selection['current_issues']))

        production = self._production('FBA', self.FBA_MUTANT_GROWTH, self.FBA_MUTANT_PROFILE, missing=['EX_ac_e'])
        missing_value = self._record('fba_mutant', report=baseline, production=production)
        self.assertFalse(missing_value['current_run_valid'])
        self.assertIn('missing numeric Mission 19 values', ' '.join(missing_value['current_issues']))

    def test_visible_biomass_and_method_diagnostics_are_mandatory(self):
        baseline = self._baseline()
        no_biomass = self._production('FBA', self.FBA_MUTANT_GROWTH, self.FBA_MUTANT_PROFILE, biomass=None)
        no_biomass.pop('biomass_raw')
        report = self._record('fba_mutant', report=baseline, production=no_biomass)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('missing the biomass-reaction flux', ' '.join(report['current_issues']))

        no_diagnostics = self._production('FBA', self.FBA_MUTANT_GROWTH, self.FBA_MUTANT_PROFILE)
        no_diagnostics.pop('method_diagnostics')
        report = self._record('fba_mutant', report=baseline, production=no_diagnostics)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('Method diagnostics are missing', ' '.join(report['current_issues']))

    def test_visible_objective_biomass_and_primary_flux_must_agree(self):
        baseline = self._baseline()
        inconsistent = self._production('FBA', self.FBA_MUTANT_GROWTH, self.FBA_MUTANT_PROFILE, biomass=0.5, primary=0.5)
        report = self._record('fba_mutant', report=baseline, production=inconsistent)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('displayed biomass', ' '.join(report['current_issues']))

        inconsistent = self._production('FBA', self.FBA_MUTANT_GROWTH, self.FBA_MUTANT_PROFILE, primary=0.5)
        report = self._record('fba_mutant', report=baseline, production=inconsistent)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('Method diagnostics and biomass evidence', ' '.join(report['current_issues']))

    def test_lmoma_score_is_required_positive_and_correctly_labelled(self):
        baseline = self._baseline()
        missing_score = self._production('lMOMA', self.LMOMA_MUTANT_GROWTH, self.LMOMA_MUTANT_PROFILE, score=None)
        missing_score['method_diagnostics']['method_score'] = None
        report = self._record('lmoma_mutant', report=baseline, production=missing_score)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('adjustment score is missing', ' '.join(report['current_issues']))

        wrong_label = self._production('lMOMA', self.LMOMA_MUTANT_GROWTH, self.LMOMA_MUTANT_PROFILE, score_name='solver_objective_value')
        report = self._record('lmoma_mutant', report=baseline, production=wrong_label)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('expected method semantics', ' '.join(report['current_issues']))

    def test_invalid_attempt_preserves_complete_evidence(self):
        complete = self._complete()
        invalid = self._record('invalid', report=complete, method='pFBA')
        self.assertFalse(invalid['current_run_recorded'])
        self.assertTrue(invalid['comparison_ready'])
        self.assertTrue(invalid['evidence_ready'])
        text = simulation.build_mission19_method_comparison_report_text(invalid)
        self.assertIn('Latest run was not recorded', text)
        self.assertIn('Previously valid Mission 19 evidence remains available', text)

    def test_direct_method_answers_are_accepted_and_extra_methods_rejected(self):
        report = self._complete()
        for answer in ('lMOMA', 'linear MOMA', 'linear minimization of metabolic adjustment'):
            self.assertTrue(simulation.mission19_answer_matches(answer, report), answer)
        for answer in ('FBA', 'pFBA', 'ROOM', 'both', 'lMOMA and FBA', 'b0728', 'lMOMA ROOM'):
            self.assertFalse(simulation.mission19_answer_matches(answer, report), answer)
        self.assertFalse(simulation.mission19_answer_matches('lMOMA', self._baseline()))

    def test_report_shows_evidence_without_printing_the_answer(self):
        report = self._complete()
        text = simulation.build_mission19_method_comparison_report_text(report)
        self.assertIn('Wild-type FBA baseline', text)
        self.assertIn('Predicted growth rate: 0.874 h^-1', text)
        self.assertIn('b0728 mutant under FBA', text)
        self.assertIn('Predicted growth rate: 0.858 h^-1', text)
        self.assertIn('b0728 mutant under lMOMA', text)
        self.assertIn('Predicted growth rate: 0.803 h^-1', text)
        self.assertIn('lMOMA adjustment score: 39.785', text)
        self.assertIn('Which method predicted the lower viable biomass response', text)
        self.assertNotIn('Answer: lMOMA', text)
        self.assertNotIn('lMOMA predicted the lower', text)

    def test_remote_wrapper_uses_visible_result_only_and_state_is_json_serialisable(self):
        report = self._complete()
        json.dumps(report)
        source = inspect.getsource(simulation.run_mission19_perturbation_check_remote)
        self.assertNotIn('_http_post_json', source)
        self.assertIn('run_mission19_perturbation_check(simulation_results)', source)
        for func in (simulation._build_mission19_data, simulation.run_mission19_perturbation_check):
            source = inspect.getsource(func)
            self.assertNotIn('_simulate_local_reaction_flux', source)
            self.assertNotIn('.simulate(', source)

    def test_general_results_and_backend_expose_lmoma_score_semantics(self):
        window = (CODE_DIR / 'window.py').read_text(encoding='utf-8')
        self.assertIn('{LMOMA_DISPLAY_NAME} adjustment criterion', window)
        self.assertIn('The adjustment score is not biomass', window)
        backend = (PROJECT_ROOT / 'backend' / 'app' / 'simulator.py').read_text(encoding='utf-8')
        self.assertIn('total_absolute_flux_adjustment', backend)
        self.assertEqual(simulation._method_score_label('lMOMA'), simulation.MISSION19_LMOMA_SCORE_NAME)

    def test_ui_documentation_and_deployment_notes_match_reconstruction(self):
        source = (CODE_DIR / 'mission19.py').read_text(encoding='utf-8')
        self.assertIn('is_mission19_unlocked', source)
        self.assertIn('initialise_mission19_method_comparison()', source)
        self.assertIn('Binding export route:', (CODE_DIR / 'mission18.py').read_text(encoding='utf-8'))
        self.assertIn('Method: ', source)
        self.assertIn('mission19_answer_matches', source)
        self.assertNotIn('b2296', source)
        window = (CODE_DIR / 'window.py').read_text(encoding='utf-8')
        self.assertIn('run_mission19_perturbation_check_remote', window)
        mission_doc = (PROJECT_ROOT / 'data' / 'missions' / 'mission19.md').read_text(encoding='utf-8')
        self.assertIn('Re-optimisation vs Minimal Adjustment', mission_doc)
        self.assertIn('No hidden simulation', mission_doc)
        overview = (PROJECT_ROOT / 'MISSION_PROGRESS_OVERVIEW.md').read_text(encoding='utf-8')
        self.assertIn('Mission 19 — Re-optimisation vs Minimal Adjustment', overview)
        deploy = (PROJECT_ROOT / 'deploy' / 'README.md').read_text(encoding='utf-8')
        self.assertNotIn("Mission 19's perturbation helper", deploy)

    def test_lmoma_uses_explicit_wild_type_reference_in_desktop_and_backend(self):
        local_source = inspect.getsource(simulation._simulate_local_lmoma_with_reference)
        self.assertIn('reference_solution = reference_model.optimize()', local_source)
        self.assertIn('moma(mutant_model, solution=reference_solution, linear=True)', local_source)
        self.assertIn('reference_has_no_gene_knockouts', local_source)
        self.assertNotIn("simul.simulate(method='lMOMA'", local_source)

        backend = (PROJECT_ROOT / 'backend' / 'app' / 'simulator.py').read_text(encoding='utf-8')
        self.assertIn('def _simulate_lmoma_with_explicit_reference', backend)
        self.assertIn('reference_solution = reference_model.optimize()', backend)
        self.assertIn('moma(mutant_model, solution=reference_solution, linear=True)', backend)
        self.assertIn('if req.method == "lMOMA"', backend)

    def test_mission19_highlights_b0728_and_uses_clear_lmoma_label(self):
        window = (CODE_DIR / 'window.py').read_text(encoding='utf-8')
        self.assertIn("('19', [MISSION19_TARGET_GENE])", window)
        self.assertIn("(LMOMA_DISPLAY_NAME, 'lmoma')", window)
        self.assertEqual(simulation.LMOMA_DISPLAY_NAME, 'Linear MOMA (lMOMA)')
        self.assertEqual(simulation._normalise_method_name(simulation.LMOMA_DISPLAY_NAME), 'lMOMA')
        self.assertEqual(simulation._normalise_method_name('lMOMA'), 'lMOMA')

    def test_window_uses_public_method_normaliser_available_through_star_import(self):
        self.assertTrue(hasattr(simulation, 'normalise_method_name'))
        self.assertEqual(simulation.normalise_method_name(simulation.LMOMA_DISPLAY_NAME), 'lMOMA')
        self.assertEqual(simulation.normalise_method_name('FBA'), 'FBA')

        imported_names = {}
        exec('from simulation import *', imported_names)
        self.assertIn('normalise_method_name', imported_names)
        self.assertNotIn('_normalise_method_name', imported_names)

        window = (CODE_DIR / 'window.py').read_text(encoding='utf-8')
        self.assertIn('normalise_method_name(selected)', window)
        self.assertIn('normalise_method_name(method_name)', window)
        self.assertNotIn('_normalise_method_name(', window)

    def test_lmoma_reference_metadata_is_json_safe_and_explicit(self):
        try:
            _result, production, _medium = simulation._simulate_local_objective_with_production_fluxes(
                'lMOMA',
                simulation.MISSION19_GROWTH_OBJECTIVE,
                self._genes(simulation.MISSION19_TARGET_GENE),
                dict(self.default_reactions),
                list(self.panel),
            )
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'MEWpy/COBRApy unavailable: {exc}')
        diagnostics = production['method_diagnostics']
        self.assertEqual(diagnostics['reference_method'], 'FBA')
        self.assertTrue(diagnostics['reference_uses_same_environment'])
        self.assertTrue(diagnostics['reference_has_no_gene_knockouts'])
        self.assertEqual(diagnostics['gpr_disabled_reactions'], ['SUCOAS'])
        json.dumps(diagnostics)

    def test_real_solver_values_for_wt_fba_fba_mutant_and_lmoma_mutant(self):
        genes_wt = self._genes()
        genes_mutant = self._genes(simulation.MISSION19_TARGET_GENE)
        try:
            wt_result, wt_production, _ = simulation._simulate_local_objective_with_production_fluxes(
                'FBA', simulation.MISSION19_GROWTH_OBJECTIVE, genes_wt,
                dict(self.default_reactions), list(self.panel),
            )
            fba_result, fba_production, _ = simulation._simulate_local_objective_with_production_fluxes(
                'FBA', simulation.MISSION19_GROWTH_OBJECTIVE, genes_mutant,
                dict(self.default_reactions), list(self.panel),
            )
            lmoma_result, lmoma_production, _ = simulation._simulate_local_objective_with_production_fluxes(
                'lMOMA', simulation.MISSION19_GROWTH_OBJECTIVE, genes_mutant,
                dict(self.default_reactions), list(self.panel),
            )
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'MEWpy/COBRApy unavailable: {exc}')

        self.assertAlmostEqual(float(wt_result), self.WT_GROWTH, delta=1e-3)
        self.assertAlmostEqual(float(fba_result), self.FBA_MUTANT_GROWTH, delta=1e-3)
        self.assertAlmostEqual(float(lmoma_result), self.LMOMA_MUTANT_GROWTH, delta=1e-3)
        self.assertAlmostEqual(float(lmoma_production['biomass_raw']), self.LMOMA_MUTANT_GROWTH, delta=1e-3)
        diagnostics = lmoma_production['method_diagnostics']
        self.assertEqual(diagnostics['method_score_name'], simulation.MISSION19_LMOMA_SCORE_NAME)
        self.assertAlmostEqual(float(diagnostics['method_score']), self.LMOMA_SCORE, delta=1e-2)
        values = simulation._mission19_measured_production_values(lmoma_production)
        self.assertAlmostEqual(values['EX_ac_e'], self.LMOMA_MUTANT_PROFILE['EX_ac_e'], delta=1e-3)
        self.assertAlmostEqual(values['EX_lac__D_e'], self.LMOMA_MUTANT_PROFILE['EX_lac__D_e'], delta=1e-3)

    def test_backend_lmoma_matches_desktop_explicit_reference_contract(self):
        backend_dir = PROJECT_ROOT / 'backend'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        try:
            from app.schemas import SimulateRequest
            from app.simulator import simulate as backend_simulate
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'Backend MEWpy/COBRApy unavailable: {exc}')

        env_conditions = simulation._build_envconditions_from_reactions(
            dict(self.default_reactions), simulation.REACTIONS
        )
        response = backend_simulate(SimulateRequest(
            method='lMOMA',
            objective=simulation.MISSION19_GROWTH_OBJECTIVE,
            gene_knockouts=[simulation.MISSION19_TARGET_GENE],
            env_conditions=env_conditions,
        ))
        self.assertEqual(response.status, 'ok', response.message)
        self.assertAlmostEqual(float(response.primary_objective_flux), self.LMOMA_MUTANT_GROWTH, delta=1e-3)
        self.assertAlmostEqual(float(response.method_score), self.LMOMA_SCORE, delta=1e-2)
        self.assertEqual(response.method_score_name, simulation.MISSION19_LMOMA_SCORE_NAME)
        self.assertAlmostEqual(float(response.fluxes['EX_ac_e']), self.LMOMA_MUTANT_PROFILE['EX_ac_e'], delta=1e-3)
        self.assertAlmostEqual(float(response.fluxes['EX_lac__D_e']), self.LMOMA_MUTANT_PROFILE['EX_lac__D_e'], delta=1e-3)

    def test_lmoma_values_match_independent_linear_formulation(self):
        try:
            import gzip
            import xml.etree.ElementTree as ET
            import numpy as np
            from scipy.optimize import linprog
        except Exception as exc:
            self.skipTest(f'SciPy/XML dependencies unavailable: {exc}')

        model_path = PROJECT_ROOT / 'data' / 'models' / 'e_coli_core.xml.gz'
        ns = {
            'sbml': 'http://www.sbml.org/sbml/level3/version1/core',
            'fbc': 'http://www.sbml.org/sbml/level3/version1/fbc/version2',
        }
        with gzip.open(model_path, 'rb') as handle:
            root = ET.parse(handle).getroot()
        model_element = root.find('sbml:model', ns)
        species = [item.attrib['id'] for item in model_element.find('sbml:listOfSpecies', ns)]
        species_index = {item: index for index, item in enumerate(species)}
        parameters = {
            item.attrib['id']: float(item.attrib['value'])
            for item in model_element.find('sbml:listOfParameters', ns)
        }
        reaction_elements = list(model_element.find('sbml:listOfReactions', ns))
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

        biomass = reaction_index['R_BIOMASS_Ecoli_core_w_GAM']
        objective = np.zeros(len(reactions))
        objective[biomass] = -1.0
        wt = linprog(objective, A_eq=matrix, b_eq=np.zeros(len(species)), bounds=bounds, method='highs')
        self.assertTrue(wt.success)

        mutant_bounds = list(bounds)
        mutant_bounds[reaction_index['R_SUCOAS']] = (0.0, 0.0)
        count = len(reactions)
        lmoma_objective = np.concatenate([np.zeros(count), np.ones(count)])
        equality = np.hstack([matrix, np.zeros((matrix.shape[0], count))])
        inequalities = np.vstack([
            np.hstack([np.eye(count), -np.eye(count)]),
            np.hstack([-np.eye(count), -np.eye(count)]),
        ])
        inequality_rhs = np.concatenate([wt.x, -wt.x])
        lmoma = linprog(
            lmoma_objective,
            A_ub=inequalities,
            b_ub=inequality_rhs,
            A_eq=equality,
            b_eq=np.zeros(len(species)),
            bounds=mutant_bounds + [(0.0, None)] * count,
            method='highs',
        )
        self.assertTrue(lmoma.success)
        self.assertAlmostEqual(lmoma.x[biomass], self.LMOMA_MUTANT_GROWTH, delta=1e-6)
        self.assertAlmostEqual(lmoma.fun, self.LMOMA_SCORE, delta=1e-6)
        self.assertAlmostEqual(lmoma.x[reaction_index['R_EX_ac_e']], self.LMOMA_MUTANT_PROFILE['EX_ac_e'], delta=1e-6)
        self.assertAlmostEqual(lmoma.x[reaction_index['R_EX_lac__D_e']], self.LMOMA_MUTANT_PROFILE['EX_lac__D_e'], delta=1e-6)


if __name__ == '__main__':
    unittest.main()
