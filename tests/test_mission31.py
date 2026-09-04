"""Regression tests for Mission 31 Environmental Suppression Matrix.

Run from the project root with:
    python3 tests/test_mission31.py
"""
from __future__ import annotations

import ast
import gzip
import inspect
import json
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

try:
    import pygame  # noqa: F401
except ModuleNotFoundError:
    pygame_stub = types.ModuleType('pygame')
    pygame_stub.Vector2 = lambda *args: tuple(args)
    sys.modules['pygame'] = pygame_stub

try:
    import pygame_menu  # noqa: F401
except ModuleNotFoundError:
    class _Theme:
        def copy(self):
            return _Theme()
    pygame_menu_stub = types.ModuleType('pygame_menu')
    pygame_menu_stub.themes = types.SimpleNamespace(THEME_GREEN=_Theme())
    pygame_menu_stub.font = types.SimpleNamespace(FONT_MUNRO='munro')
    pygame_menu_stub.widgets = types.SimpleNamespace(MENUBAR_STYLE_SIMPLE='simple')
    sys.modules['pygame_menu'] = pygame_menu_stub

_original_platform = sys.platform
try:
    import mewpy  # noqa: F401
    import cobra  # noqa: F401
except ModuleNotFoundError:
    sys.platform = 'emscripten'

import save_load  # noqa: E402
import simulation  # noqa: E402
sys.platform = _original_platform


class Mission31RegressionTests(unittest.TestCase):
    EXPECTED = {
        'EX_fru_e': {
            'wild_type': (0.873921507, 10.0, 21.799493, 518.700363, 48),
            'aconitase_double': (0.0, 0.932222, 1.864444, 55.933333, 26),
        },
        'EX_pyr_e': {
            'wild_type': (0.291224780, 10.0, 12.270099, 254.890246, 48),
            'aconitase_double': (0.0, 3.728889, 1.864444, 57.797778, 15),
        },
        'EX_succ_e': {
            'wild_type': (0.397563015, 10.0, 17.621884, 334.041931, 46),
            'aconitase_double': (0.0, 2.097500, 3.146250, 67.120000, 21),
        },
        'EX_glu__L_e': {
            'wild_type': (0.598731725, 10.0, 18.828478, 347.987543, 46),
            'aconitase_double': (0.576235631, 10.0, 19.811819, 403.945660, 45),
        },
    }

    def _genes(self, genotype, *, extra_knockout=None, incomplete=False):
        genes = simulation._build_active_genes_data()
        if genotype == 'aconitase_double':
            genes[simulation.MISSION31_GENE_A] = False
            genes[simulation.MISSION31_GENE_B] = False
        elif genotype == 'single_a':
            genes[simulation.MISSION31_GENE_A] = False
        elif genotype == 'single_b':
            genes[simulation.MISSION31_GENE_B] = False
        if extra_knockout:
            genes[extra_knockout] = False
        if incomplete:
            genes.pop(next(iter(genes)))
        return genes

    def _reactions(
        self,
        source,
        *,
        glucose_closed=True,
        extra_source=None,
        oxygen_changed=False,
        upper_changed=None,
        incomplete=False,
    ):
        reactions = simulation._build_default_reactions_data()
        glucose_index = list(simulation.REACTIONS.index).index(simulation.MISSION31_GLUCOSE_REACTION)
        source_index = list(simulation.REACTIONS.index).index(source)
        if glucose_closed:
            reactions[f'reaction_{glucose_index}_lb'] = False
        reactions[f'reaction_{source_index}_lb'] = True
        if extra_source:
            extra_index = list(simulation.REACTIONS.index).index(extra_source)
            reactions[f'reaction_{extra_index}_lb'] = True
        if oxygen_changed:
            oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION31_OXYGEN_REACTION)
            reactions[f'reaction_{oxygen_index}_lb'] = False
        if upper_changed:
            upper_index = list(simulation.REACTIONS.index).index(upper_changed)
            reactions[f'reaction_{upper_index}_ub'] = not reactions[f'reaction_{upper_index}_ub']
        if incomplete:
            reactions.pop(next(iter(reactions)))
        return reactions

    def _disabled(self, genotype):
        if genotype == 'aconitase_double':
            return list(simulation.MISSION31_TARGET_REACTIONS)
        return []

    def _production(self, growth, total, active, *, biomass=None, diagnostics=None, error=None):
        result = {
            'selected_ids': [],
            'items': [],
            'biomass_raw': growth if biomass is None else biomass,
            'method_diagnostics': {
                'method': simulation.MISSION31_METHOD,
                'objective_reaction': simulation.MISSION31_GROWTH_OBJECTIVE,
                'primary_objective_flux': growth,
                'method_score': total,
                'method_score_name': simulation.MISSION31_EXPECTED_SCORE_NAME,
                'total_absolute_flux': total,
                'active_reaction_count': active,
            },
        }
        if diagnostics:
            result['method_diagnostics'].update(diagnostics)
        if error:
            result['error'] = error
        return result

    def _medium(
        self,
        source,
        source_uptake,
        oxygen_uptake,
        *,
        glucose_raw=0.0,
        source_raw=None,
        oxygen_raw=None,
        missing=None,
        error=None,
    ):
        source_raw = -source_uptake if source_raw is None else source_raw
        oxygen_raw = -oxygen_uptake if oxygen_raw is None else oxygen_raw
        rows = [
            (simulation.MISSION31_GLUCOSE_REACTION, glucose_raw),
            (source, source_raw),
            (simulation.MISSION31_OXYGEN_REACTION, oxygen_raw),
        ]
        items = []
        for reaction_id, raw in rows:
            if reaction_id == missing:
                continue
            items.append({
                'reaction_id': reaction_id,
                'raw_flux': raw,
                'uptake_flux': max(-float(raw), 0.0),
                'secretion_flux': max(float(raw), 0.0),
            })
        result = {'items': items}
        if error:
            result['error'] = error
        return result

    def _record(
        self,
        source,
        genotype,
        *,
        existing=None,
        method=None,
        objective=None,
        objective_result=None,
        genes=None,
        reactions=None,
        production=None,
        medium=None,
        objective_error=None,
        disabled=None,
    ):
        growth, source_uptake, oxygen_uptake, total, active = self.EXPECTED[source][genotype]
        if objective_result is None:
            objective_result = growth
        if production is None:
            production = self._production(growth, total, active)
        if medium is None:
            medium = self._medium(source, source_uptake, oxygen_uptake)
        with (
            patch.object(simulation, 'save_mission31_environmental_suppression_check'),
            patch.object(
                simulation,
                '_mission31_disabled_reactions',
                return_value=self._disabled(genotype) if disabled is None else disabled,
            ),
        ):
            return simulation._build_mission31_data(
                method or simulation.MISSION31_METHOD,
                objective or simulation.MISSION31_GROWTH_OBJECTIVE,
                objective_result,
                genes if genes is not None else self._genes(genotype),
                reactions if reactions is not None else self._reactions(source),
                production_fluxes=production,
                medium_fluxes=medium,
                existing_report={} if existing is None else existing,
                objective_error=objective_error,
            )

    def _complete(self, order=None):
        order = order or [
            (source, genotype)
            for source in simulation.MISSION31_SOURCE_ORDER
            for genotype in simulation.MISSION31_GENOTYPE_ORDER
        ]
        report = {}
        for source, genotype in order:
            report = self._record(source, genotype, existing=report)
        return report

    def test_constants_and_progression(self):
        self.assertEqual(simulation.MISSION31_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION31_METHOD, 'pFBA')
        self.assertEqual(simulation.MISSION31_REQUIRED_RUN_COUNT, 8)
        self.assertEqual(simulation.MISSION31_DOUBLE_KNOCKOUT, ['b0118', 'b1276'])
        self.assertEqual(simulation.MISSION31_TARGET_REACTIONS, ['ACONTa', 'ACONTb'])
        self.assertFalse(simulation.is_mission31_unlocked(['29']))
        self.assertTrue(simulation.is_mission31_unlocked(['30']))

    def test_initial_state_requires_eight_matrix_cells(self):
        with patch.object(simulation, 'save_mission31_environmental_suppression_check'):
            report = simulation.initialise_mission31_environmental_suppression_matrix()
        self.assertEqual(report['recorded_run_count'], 0)
        self.assertEqual(report['required_run_count'], 8)
        self.assertEqual(len(report['missing_conditions']), 8)
        self.assertFalse(report['evidence_ready'])

    def test_complete_matrix_supports_one_unique_environmental_suppression(self):
        report = self._complete()
        self.assertEqual(report['recorded_run_count'], 8)
        self.assertEqual(report['missing_conditions'], [])
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['suppression_candidates'], ['EX_glu__L_e'])
        self.assertEqual(report['unique_suppression_source'], 'EX_glu__L_e')
        self.assertTrue(report['non_suppression_controls_supported'])
        self.assertTrue(report['unique_suppression_supported'])
        self.assertTrue(report['ready_to_deliver'])

    def test_growth_retentions_match_expected_matrix(self):
        report = self._complete()
        self.assertEqual(report['growth_retention_by_source']['EX_fru_e'], 0.0)
        self.assertEqual(report['growth_retention_by_source']['EX_pyr_e'], 0.0)
        self.assertEqual(report['growth_retention_by_source']['EX_succ_e'], 0.0)
        self.assertAlmostEqual(report['growth_retention_by_source']['EX_glu__L_e'], 0.962427, delta=1e-6)

    def test_runs_can_arrive_in_any_order(self):
        order = [
            ('EX_glu__L_e', 'aconitase_double'),
            ('EX_pyr_e', 'wild_type'),
            ('EX_fru_e', 'aconitase_double'),
            ('EX_succ_e', 'wild_type'),
            ('EX_glu__L_e', 'wild_type'),
            ('EX_fru_e', 'wild_type'),
            ('EX_pyr_e', 'aconitase_double'),
            ('EX_succ_e', 'aconitase_double'),
        ]
        report = self._complete(order)
        self.assertTrue(report['unique_suppression_supported'])
        self.assertEqual(report['missing_conditions'], [])

    def test_seven_runs_remain_incomplete(self):
        order = [
            (source, genotype)
            for source in simulation.MISSION31_SOURCE_ORDER
            for genotype in simulation.MISSION31_GENOTYPE_ORDER
        ][:-1]
        report = self._complete(order)
        self.assertEqual(report['recorded_run_count'], 7)
        self.assertFalse(report['evidence_ready'])
        self.assertIn('EX_glu__L_e:aconitase_double', report['missing_conditions'])

    def test_repeated_cell_updates_without_duplication(self):
        report = self._complete()
        updated = self._record('EX_glu__L_e', 'aconitase_double', existing=report)
        self.assertEqual(updated['recorded_run_count'], 8)
        self.assertEqual(updated['missing_conditions'], [])
        self.assertTrue(updated['current_run_recorded'])

    def test_feasible_numeric_zero_is_valid_and_not_infeasible(self):
        report = self._record('EX_fru_e', 'aconitase_double')
        self.assertTrue(report['current_run_recorded'])
        run = report['source_trials']['EX_fru_e']['aconitase_double']
        self.assertEqual(run['status'], 'ok')
        self.assertEqual(run['growth'], 0.0)
        self.assertGreater(run['source_uptake'], 0.0)

    def test_infeasible_is_rejected_instead_of_becoming_zero(self):
        growth, source_uptake, oxygen, total, active = self.EXPECTED['EX_fru_e']['aconitase_double']
        report = self._record(
            'EX_fru_e',
            'aconitase_double',
            objective_result='Status: INFEASIBLE',
            production=self._production(growth, total, active, error='Simulation infeasible'),
            medium=self._medium('EX_fru_e', source_uptake, oxygen, error='Simulation infeasible'),
        )
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(any('INFEASIBLE' in issue for issue in report['current_issues']))

    def test_positive_uptake_without_growth_is_not_classified_as_suppression(self):
        report = self._complete()
        self.assertGreater(report['source_trials']['EX_pyr_e']['aconitase_double']['source_uptake'], 0.0)
        self.assertNotIn('EX_pyr_e', report['suppression_candidates'])

    def test_second_strong_double_growth_removes_unique_support(self):
        complete = self._complete()
        source = 'EX_succ_e'
        _, source_uptake, oxygen, total, active = self.EXPECTED[source]['aconitase_double']
        growth = 0.38
        report = self._record(
            source,
            'aconitase_double',
            existing=complete,
            objective_result=growth,
            production=self._production(growth, total, active),
            medium=self._medium(source, source_uptake, oxygen),
        )
        self.assertEqual(set(report['suppression_candidates']), {'EX_succ_e', 'EX_glu__L_e'})
        self.assertIsNone(report['unique_suppression_source'])
        self.assertFalse(report['unique_suppression_supported'])

    def test_low_glutamate_growth_removes_suppression_support(self):
        complete = self._complete()
        source = 'EX_glu__L_e'
        _, source_uptake, oxygen, total, active = self.EXPECTED[source]['aconitase_double']
        growth = 0.0
        report = self._record(
            source,
            'aconitase_double',
            existing=complete,
            objective_result=growth,
            production=self._production(growth, total, active),
            medium=self._medium(source, source_uptake, oxygen),
        )
        self.assertEqual(report['suppression_candidates'], [])
        self.assertFalse(report['unique_suppression_supported'])

    def test_wrong_method_and_objective_are_rejected(self):
        report = self._record('EX_fru_e', 'wild_type', method='FBA')
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(any('pFBA' in issue for issue in report['current_issues']))
        report = self._record('EX_fru_e', 'wild_type', objective='EX_ac_e')
        self.assertFalse(report['current_run_recorded'])

    def test_incomplete_gene_payload_single_and_extra_knockouts_are_rejected(self):
        report = self._record('EX_fru_e', 'wild_type', genes=self._genes('wild_type', incomplete=True))
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(any('gene-state payload' in issue for issue in report['current_issues']))
        report = self._record('EX_fru_e', 'wild_type', genes=self._genes('single_a'))
        self.assertFalse(report['current_run_recorded'])
        report = self._record(
            'EX_fru_e',
            'aconitase_double',
            genes=self._genes('aconitase_double', extra_knockout='b1723'),
        )
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(any('exact' in issue.lower() for issue in report['current_issues']))

    def test_environment_requires_glucose_closed_and_one_listed_source(self):
        report = self._record(
            'EX_fru_e', 'wild_type', reactions=self._reactions('EX_fru_e', glucose_closed=False)
        )
        self.assertFalse(report['current_run_recorded'])
        report = self._record(
            'EX_fru_e',
            'wild_type',
            reactions=self._reactions('EX_fru_e', extra_source='EX_pyr_e'),
        )
        self.assertFalse(report['current_run_recorded'])
        report = self._record(
            'EX_fru_e',
            'wild_type',
            reactions=self._reactions('EX_akg_e'),
        )
        self.assertFalse(report['current_run_recorded'])

    def test_oxygen_upper_bounds_and_payload_must_remain_controlled(self):
        report = self._record(
            'EX_fru_e',
            'wild_type',
            reactions=self._reactions('EX_fru_e', oxygen_changed=True),
        )
        self.assertFalse(report['current_run_recorded'])
        report = self._record(
            'EX_fru_e',
            'wild_type',
            reactions=self._reactions('EX_fru_e', upper_changed='EX_fru_e'),
        )
        self.assertFalse(report['current_run_recorded'])
        report = self._record(
            'EX_fru_e',
            'wild_type',
            reactions=self._reactions('EX_fru_e', incomplete=True),
        )
        self.assertFalse(report['current_run_recorded'])

    def test_glucose_exchange_must_be_measured_and_zero(self):
        growth, source_uptake, oxygen, total, active = self.EXPECTED['EX_fru_e']['wild_type']
        report = self._record(
            'EX_fru_e', 'wild_type',
            medium=self._medium('EX_fru_e', source_uptake, oxygen, missing=simulation.MISSION31_GLUCOSE_REACTION),
        )
        self.assertFalse(report['current_run_recorded'])
        report = self._record(
            'EX_fru_e', 'wild_type',
            medium=self._medium('EX_fru_e', source_uptake, oxygen, glucose_raw=-1.0),
        )
        self.assertFalse(report['current_run_recorded'])

    def test_source_exchange_must_be_positive_consumption_within_capacity(self):
        growth, _source_uptake, oxygen, total, active = self.EXPECTED['EX_fru_e']['wild_type']
        report = self._record(
            'EX_fru_e', 'wild_type',
            medium=self._medium('EX_fru_e', 0.0, oxygen),
        )
        self.assertFalse(report['current_run_recorded'])
        report = self._record(
            'EX_fru_e', 'wild_type',
            medium=self._medium('EX_fru_e', 1.0, oxygen, source_raw=1.0),
        )
        self.assertFalse(report['current_run_recorded'])
        report = self._record(
            'EX_fru_e', 'wild_type',
            medium=self._medium('EX_fru_e', 11.0, oxygen),
        )
        self.assertFalse(report['current_run_recorded'])

    def test_oxygen_exchange_must_be_measured_aerobic_and_not_secreted(self):
        _growth, source_uptake, _oxygen, _total, _active = self.EXPECTED['EX_fru_e']['wild_type']
        report = self._record(
            'EX_fru_e', 'wild_type',
            medium=self._medium('EX_fru_e', source_uptake, 0.0),
        )
        self.assertFalse(report['current_run_recorded'])
        report = self._record(
            'EX_fru_e', 'wild_type',
            medium=self._medium('EX_fru_e', source_uptake, 1.0, oxygen_raw=1.0),
        )
        self.assertFalse(report['current_run_recorded'])
        report = self._record(
            'EX_fru_e', 'wild_type',
            medium=self._medium('EX_fru_e', source_uptake, 1.0, missing=simulation.MISSION31_OXYGEN_REACTION),
        )
        self.assertFalse(report['current_run_recorded'])

    def test_biomass_and_pfba_diagnostics_are_strictly_validated(self):
        growth, source_uptake, oxygen, total, active = self.EXPECTED['EX_fru_e']['wild_type']
        report = self._record(
            'EX_fru_e', 'wild_type',
            production=self._production(growth, total, active, biomass=growth - 0.1),
        )
        self.assertFalse(report['current_run_recorded'])
        report = self._record(
            'EX_fru_e', 'wild_type',
            production=self._production(growth, total, active, diagnostics={'method': 'FBA'}),
        )
        self.assertFalse(report['current_run_recorded'])
        report = self._record(
            'EX_fru_e', 'wild_type',
            production=self._production(growth, total, active, diagnostics={'method_score': total + 1.0}),
        )
        self.assertFalse(report['current_run_recorded'])
        report = self._record(
            'EX_fru_e', 'wild_type',
            production=self._production(growth, total, active, diagnostics={'active_reaction_count': None}),
        )
        self.assertFalse(report['current_run_recorded'])

    def test_gpr_pattern_is_required_for_both_genotypes(self):
        report = self._record('EX_fru_e', 'aconitase_double', disabled=['ACONTa'])
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(any('both aconitase' in issue for issue in report['current_issues']))
        report = self._record('EX_fru_e', 'wild_type', disabled=['ACONTa'])
        self.assertFalse(report['current_run_recorded'])

    def test_invalid_attempt_preserves_complete_evidence(self):
        complete = self._complete()
        invalid = self._record(
            'EX_fru_e',
            'wild_type',
            existing=complete,
            method='FBA',
        )
        self.assertFalse(invalid['current_run_recorded'])
        self.assertEqual(invalid['recorded_run_count'], 8)
        self.assertTrue(invalid['evidence_ready'])
        self.assertTrue(invalid['unique_suppression_supported'])
        text = simulation.build_mission31_environmental_suppression_report_text(invalid)
        self.assertIn('Previously valid Mission 31 matrix evidence remains available', text)

    def test_answer_validation_accepts_only_the_supported_source(self):
        report = self._complete()
        for answer in (
            'EX_glu__L_e', 'glutamate', 'L-glutamate', 'glu', 'glutamato', 'L-glutamato'
        ):
            self.assertTrue(simulation.mission31_answer_matches(answer, report), answer)
        for answer in (
            'EX_akg_e', '2-oxoglutarate', 'fructose', 'pyruvate', 'succinate',
            'b0118', 'b1276', 'aconitase', 'glucose', 'glu randomtext'
        ):
            self.assertFalse(simulation.mission31_answer_matches(answer, report), answer)

    def test_report_is_evidence_based_status_aware_and_not_answer_explicit(self):
        text = simulation.build_mission31_environmental_suppression_report_text(self._complete())
        self.assertIn('Runs recorded: 8/8', text)
        self.assertIn('EX_glu__L_e | 0.599 | 0.576 | 96.2%', text)
        self.assertIn('positive replacement-source uptake is not by itself a rescue', text)
        self.assertIn('0.000 is also distinct from an INFEASIBLE', text)
        self.assertIn('Evidence complete', text)
        self.assertNotIn('The answer is glutamate', text)
        self.assertNotIn('Submit EX_glu__L_e', text)

    def test_report_and_state_are_json_serialisable(self):
        report = self._complete()
        json.dumps(report)
        self.assertIsInstance(simulation.build_mission31_environmental_suppression_report_text(report), str)

    def test_replacement_source_uses_shared_minus_ten_open_capacity(self):
        self.assertEqual(simulation.resolve_exchange_bound_value(0.0, True, 'lower'), -10.0)
        status = simulation._mission31_environment_status(self._reactions('EX_fru_e'))
        self.assertTrue(status['replacement_medium_ready'])
        self.assertEqual(status['source'], 'EX_fru_e')

    def test_remote_wrapper_reuses_visible_result_and_makes_no_http_request(self):
        visible = ('objective', 1.0, {}, {})
        sentinel = {'ok': True}
        with patch.object(simulation, 'run_mission31_environmental_suppression_check', return_value=sentinel) as wrapped:
            result = simulation.run_mission31_environmental_suppression_check_remote('https://unused', visible)
        self.assertIs(result, sentinel)
        wrapped.assert_called_once_with(visible)
        source = inspect.getsource(simulation.run_mission31_environmental_suppression_check_remote)
        self.assertNotIn('_http_post_json', source)

    def test_save_load_web_contract_round_trip(self):
        sample = {'mission_id': '31', 'check_version': 2, 'nested': {'value': 1}}
        original_web = save_load._IS_WEB
        original_store = dict(save_load._MEMSTORE)
        try:
            save_load._IS_WEB = True
            save_load._MEMSTORE.clear()
            save_load.save_mission31_environmental_suppression_check(sample)
            self.assertEqual(save_load.load_mission31_environmental_suppression_check(), sample)
            save_load.clear_mission31_environmental_suppression_check()
            self.assertIsNone(save_load.load_mission31_environmental_suppression_check())
        finally:
            save_load._IS_WEB = original_web
            save_load._MEMSTORE.clear()
            save_load._MEMSTORE.update(original_store)

    def test_save_load_desktop_contract_round_trip(self):
        sample = {'mission_id': '31', 'check_version': 2, 'nested': {'value': 2}}
        original_web = save_load._IS_WEB
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with patch.object(
                    save_load,
                    'get_save_path',
                    side_effect=lambda filename: str(Path(tmpdir) / filename),
                ):
                    save_load._IS_WEB = False
                    save_load.save_mission31_environmental_suppression_check(sample)
                    self.assertEqual(save_load.load_mission31_environmental_suppression_check(), sample)
                    save_load.clear_mission31_environmental_suppression_check()
                    self.assertIsNone(save_load.load_mission31_environmental_suppression_check())
        finally:
            save_load._IS_WEB = original_web

    def test_dr_li_progression_and_window_wiring(self):
        mission29 = (PROJECT_ROOT / 'code' / 'mission29.py').read_text()
        mission31 = (PROJECT_ROOT / 'code' / 'mission31.py').read_text()
        window = (PROJECT_ROOT / 'code' / 'window.py').read_text()
        self.assertIn('Mission31_info', mission29)
        self.assertIn('self.menu31', mission29)
        self.assertIn("elif '30' in self.missions_completed", mission29)
        self.assertIn("if '31' in self.missions_completed", mission29)
        self.assertIn('graphics/dialogues/li.jpg', mission29)
        self.assertIn('Environmental Suppression Matrix', mission31)
        self.assertIn("('31', [MISSION31_GENE_A, MISSION31_GENE_B])", window)
        self.assertIn('run_mission31_environmental_suppression_check', window)
        self.assertIn("label_id='mission31_environmental_suppression_check'", window)
        window_tree = ast.parse(window)
        defined_functions = {
            node.name for node in window_tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertIn('_build_mission31_text', defined_functions)
        for required_name in (
            'MISSION31_CHECK_VERSION',
            'MISSION31_METHOD',
            'MISSION31_GROWTH_OBJECTIVE',
            'MISSION31_GENE_A',
            'MISSION31_GENE_B',
            'build_mission31_environmental_suppression_report_text',
            'initialise_mission31_environmental_suppression_matrix',
            'is_mission31_unlocked',
            'mission31_answer_matches',
        ):
            self.assertTrue(hasattr(simulation, required_name), required_name)

    def test_no_new_tiled_interaction_or_backend_endpoint_is_required(self):
        level = (PROJECT_ROOT / 'code' / 'level.py').read_text()
        map_text = (PROJECT_ROOT / 'data' / 'map_lb.tmx').read_text()
        backend = (PROJECT_ROOT / 'backend' / 'app' / 'main.py').read_text()
        self.assertIn('Mission29', level)
        self.assertNotIn("obj.name == 'Mission31'", level)
        self.assertNotIn('name="Mission31"', map_text)
        self.assertIn('/simulate', backend)
        self.assertNotIn('/mission31', backend.lower())

    def test_save_load_contract_and_documentation_exist(self):
        save_source = (PROJECT_ROOT / 'code' / 'save_load.py').read_text()
        for name in (
            'save_mission31_environmental_suppression_check',
            'load_mission31_environmental_suppression_check',
            'clear_mission31_environmental_suppression_check',
        ):
            self.assertIn(name, save_source)
        doc = (PROJECT_ROOT / 'data' / 'missions' / 'mission31.md').read_text()
        self.assertIn('Environmental Suppression Matrix', doc)
        self.assertIn('Dr. Li', doc)
        self.assertIn('b0118', doc)
        self.assertIn('b1276', doc)
        self.assertIn('EX_glu__L_e', doc)
        self.assertIn('INFEASIBLE', doc)

    def test_independent_sbml_primary_and_pfba_values(self):
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
            bounds.append((
                parameters[reaction.attrib[f"{{{ns['fbc']}}}lowerFluxBound"]],
                parameters[reaction.attrib[f"{{{ns['fbc']}}}upperFluxBound"]],
            ))
            reactants = reaction.find('sbml:listOfReactants', ns)
            if reactants is not None:
                for item in reactants:
                    matrix[species_index[item.attrib['species']], column] -= float(item.attrib.get('stoichiometry', '1'))
            products = reaction.find('sbml:listOfProducts', ns)
            if products is not None:
                for item in products:
                    matrix[species_index[item.attrib['species']], column] += float(item.attrib.get('stoichiometry', '1'))

        biomass = reaction_index['R_BIOMASS_Ecoli_core_w_GAM']
        glucose = reaction_index['R_EX_glc__D_e']
        oxygen = reaction_index['R_EX_o2_e']
        aconta = reaction_index['R_ACONTa']
        acontb = reaction_index['R_ACONTb']
        objective = np.zeros(len(reactions))
        objective[biomass] = -1.0

        for source_id in simulation.MISSION31_SOURCE_ORDER:
            source = reaction_index[f'R_{source_id}']
            for genotype in simulation.MISSION31_GENOTYPE_ORDER:
                current = list(bounds)
                current[glucose] = (0.0, current[glucose][1])
                current[source] = (-10.0, current[source][1])
                if genotype == 'aconitase_double':
                    current[aconta] = (0.0, 0.0)
                    current[acontb] = (0.0, 0.0)

                primary = linprog(
                    objective,
                    A_eq=matrix,
                    b_eq=np.zeros(len(species)),
                    bounds=current,
                    method='highs',
                )
                self.assertTrue(primary.success, (source_id, genotype, primary.message))
                expected_growth, expected_uptake, expected_oxygen, expected_total, expected_active = self.EXPECTED[source_id][genotype]
                self.assertAlmostEqual(primary.x[biomass], expected_growth, delta=1e-6)

                reaction_count = len(reactions)
                secondary_objective = np.concatenate([np.zeros(reaction_count), np.ones(reaction_count)])
                secondary_matrix = np.hstack([matrix, np.zeros((len(species), reaction_count))])
                biomass_row = np.zeros(2 * reaction_count)
                biomass_row[biomass] = 1.0
                secondary_matrix = np.vstack([secondary_matrix, biomass_row])
                secondary_rhs = np.append(np.zeros(len(species)), primary.x[biomass])
                abs_constraints = []
                for index in range(reaction_count):
                    positive = np.zeros(2 * reaction_count)
                    positive[index] = 1.0
                    positive[reaction_count + index] = -1.0
                    abs_constraints.append(positive)
                    negative = np.zeros(2 * reaction_count)
                    negative[index] = -1.0
                    negative[reaction_count + index] = -1.0
                    abs_constraints.append(negative)
                secondary = linprog(
                    secondary_objective,
                    A_ub=np.array(abs_constraints),
                    b_ub=np.zeros(2 * reaction_count),
                    A_eq=secondary_matrix,
                    b_eq=secondary_rhs,
                    bounds=current + [(0.0, None)] * reaction_count,
                    method='highs',
                )
                self.assertTrue(secondary.success)
                fluxes = secondary.x[:reaction_count]
                self.assertAlmostEqual(max(-fluxes[source], 0.0), expected_uptake, delta=1e-5)
                self.assertAlmostEqual(max(-fluxes[oxygen], 0.0), expected_oxygen, delta=1e-5)
                self.assertAlmostEqual(sum(abs(value) for value in fluxes), expected_total, delta=1e-5)
                self.assertEqual(sum(abs(value) > 1e-9 for value in fluxes), expected_active)


if __name__ == '__main__':
    unittest.main()
