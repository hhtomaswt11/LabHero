"""Regression tests for Mission 32 Respiratory Complex Cut-Set.

Run from the project root with:
    python3 tests/test_mission32.py
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


class Mission32RegressionTests(unittest.TestCase):
    CONTROL = (0.873921507, 10.0, 21.799493, 0.0, 0.0, 0.0, 518.422086, 48)
    CROSS = (0.211662950, 10.0, 0.0, 8.503585, 8.279455, 17.804674, 335.650617, 47)

    def _genes(self, condition, *, extra=None, incomplete=False):
        genes = simulation._build_active_genes_data()
        for gene_id in simulation.MISSION32_CONDITION_GENES.get(condition, []):
            genes[gene_id] = False
        if extra:
            genes[extra] = False
        if incomplete:
            genes.pop(next(iter(genes)))
        return genes

    def _reactions(self, *, changed=None, upper_changed=None, incomplete=False):
        reactions = simulation._build_default_reactions_data()
        if changed:
            index = list(simulation.REACTIONS.index).index(changed)
            reactions[f'reaction_{index}_lb'] = not reactions[f'reaction_{index}_lb']
        if upper_changed:
            index = list(simulation.REACTIONS.index).index(upper_changed)
            reactions[f'reaction_{index}_ub'] = not reactions[f'reaction_{index}_ub']
        if incomplete:
            reactions.pop(next(iter(reactions)))
        return reactions

    def _disabled(self, condition):
        return [simulation.MISSION32_TARGET_REACTION] if condition == 'cross_branch_pair' else []

    def _expected(self, condition):
        return self.CROSS if condition == 'cross_branch_pair' else self.CONTROL

    def _production(self, growth, total, active, *, biomass=None, diagnostics=None, error=None):
        result = {
            'selected_ids': [],
            'items': [],
            'biomass_raw': growth if biomass is None else biomass,
            'method_diagnostics': {
                'method': simulation.MISSION32_METHOD,
                'objective_reaction': simulation.MISSION32_GROWTH_OBJECTIVE,
                'primary_objective_flux': growth,
                'method_score': total,
                'method_score_name': simulation.MISSION32_EXPECTED_SCORE_NAME,
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
        glucose_uptake,
        oxygen_uptake,
        acetate,
        ethanol,
        formate,
        *,
        missing=None,
        oxygen_raw=None,
        glucose_raw=None,
        error=None,
    ):
        rows = [
            (simulation.MISSION32_GLUCOSE_REACTION, -glucose_uptake if glucose_raw is None else glucose_raw),
            (simulation.MISSION32_OXYGEN_REACTION, -oxygen_uptake if oxygen_raw is None else oxygen_raw),
            (simulation.MISSION32_ACETATE_REACTION, acetate),
            (simulation.MISSION32_ETHANOL_REACTION, ethanol),
            (simulation.MISSION32_FORMATE_REACTION, formate),
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
        condition,
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
        growth, glucose, oxygen, acetate, ethanol, formate, total, active = self._expected(condition)
        if objective_result is None:
            objective_result = growth
        if production is None:
            production = self._production(growth, total, active)
        if medium is None:
            medium = self._medium(glucose, oxygen, acetate, ethanol, formate)
        with (
            patch.object(simulation, 'save_mission32_respiratory_cut_set_check'),
            patch.object(
                simulation,
                '_mission32_disabled_reactions',
                return_value=self._disabled(condition) if disabled is None else disabled,
            ),
        ):
            return simulation._build_mission32_data(
                method or simulation.MISSION32_METHOD,
                objective or simulation.MISSION32_GROWTH_OBJECTIVE,
                objective_result,
                genes if genes is not None else self._genes(condition),
                reactions if reactions is not None else self._reactions(),
                production_fluxes=production,
                medium_fluxes=medium,
                existing_report={} if existing is None else existing,
                objective_error=objective_error,
            )

    def _complete(self, order=None):
        report = {}
        for condition in (order or simulation.MISSION32_CONDITION_ORDER):
            report = self._record(condition, existing=report)
        return report

    def test_constants_progression_and_nested_gpr(self):
        self.assertEqual(simulation.MISSION32_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION32_METHOD, 'pFBA')
        self.assertEqual(simulation.MISSION32_REQUIRED_RUN_COUNT, 6)
        self.assertEqual(simulation.MISSION32_TARGET_REACTION, 'CYTBD')
        self.assertEqual(simulation.MISSION32_BRANCH_GENES['cbdAB'], ['b0978', 'b0979'])
        self.assertEqual(simulation.MISSION32_BRANCH_GENES['cydAB'], ['b0733', 'b0734'])
        self.assertFalse(simulation.is_mission32_unlocked(['30']))
        self.assertTrue(simulation.is_mission32_unlocked(['31']))

    def test_initial_state_requires_six_conditions(self):
        with patch.object(simulation, 'save_mission32_respiratory_cut_set_check'):
            report = simulation.initialise_mission32_respiratory_cut_set_screen()
        self.assertEqual(report['recorded_run_count'], 0)
        self.assertEqual(report['required_run_count'], 6)
        self.assertEqual(report['missing_conditions'], simulation.MISSION32_CONDITION_ORDER)
        self.assertFalse(report['evidence_ready'])

    def test_condition_and_branch_classification(self):
        for condition in simulation.MISSION32_CONDITION_ORDER:
            genes = simulation.MISSION32_CONDITION_GENES[condition]
            self.assertEqual(simulation._mission32_condition_for_knockouts(genes), condition)
        self.assertIsNone(simulation._mission32_condition_for_knockouts(['b0979']))
        self.assertEqual(
            simulation._mission32_branch_status(['b0978', 'b0733']),
            {'cbdAB': 'broken', 'cydAB': 'broken'},
        )
        self.assertEqual(
            simulation._mission32_branch_status(['b0978', 'b0979']),
            {'cbdAB': 'broken', 'cydAB': 'active'},
        )

    def test_complete_screen_supports_one_unique_cut_set(self):
        report = self._complete()
        self.assertEqual(report['recorded_run_count'], 6)
        self.assertEqual(report['missing_conditions'], [])
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['cut_set_candidates'], ['cross_branch_pair'])
        self.assertEqual(report['unique_tested_cut_set'], 'cross_branch_pair')
        self.assertEqual(report['unique_tested_cut_set_genes'], ['b0978', 'b0733'])
        self.assertTrue(report['control_pattern_supported'])
        self.assertTrue(report['unique_cut_set_supported'])
        self.assertEqual(report['branch_status_by_condition']['cross_branch_pair'], {'cbdAB': 'broken', 'cydAB': 'broken'})
        self.assertEqual(report['oxygen_uptake_by_condition']['cross_branch_pair'], 0.0)
        self.assertTrue(report['cytbd_disabled_by_condition']['cross_branch_pair'])
        self.assertGreater(report['fermentation_profile_by_condition']['cross_branch_pair']['formate'], 17.0)
        self.assertTrue(report['ready_to_deliver'])

    def test_any_run_order_is_accepted(self):
        order = list(reversed(simulation.MISSION32_CONDITION_ORDER))
        report = self._complete(order)
        self.assertTrue(report['unique_cut_set_supported'])
        self.assertEqual(report['recorded_run_count'], 6)

    def test_control_rows_remain_respiratory(self):
        report = self._complete()
        for condition in simulation.MISSION32_CONDITION_ORDER[:-1]:
            run = report['runs'][condition]
            self.assertAlmostEqual(run['growth'], self.CONTROL[0], delta=1e-6)
            self.assertAlmostEqual(run['oxygen_uptake'], self.CONTROL[2], delta=1e-6)
            self.assertFalse(run['cytbd_disabled'])
            self.assertNotIn('CYTBD', run['disabled_reactions'])

    def test_cross_branch_row_is_viable_nonrespiratory_and_fermentative(self):
        report = self._complete()
        run = report['runs']['cross_branch_pair']
        self.assertEqual(run['status'], 'ok')
        self.assertAlmostEqual(run['growth'], self.CROSS[0], delta=1e-6)
        self.assertAlmostEqual(run['oxygen_uptake'], 0.0, delta=1e-9)
        self.assertTrue(run['cytbd_disabled'])
        self.assertIn('CYTBD', run['disabled_reactions'])
        self.assertGreater(run['acetate_secretion'], 8.0)
        self.assertGreater(run['ethanol_secretion'], 8.0)
        self.assertGreater(run['formate_secretion'], 17.0)

    def test_growth_retention_is_derived_from_recorded_wild_type(self):
        report = self._complete()
        self.assertAlmostEqual(report['growth_retention_by_condition']['wild_type'], 1.0, delta=1e-9)
        self.assertAlmostEqual(
            report['growth_retention_by_condition']['cross_branch_pair'],
            self.CROSS[0] / self.CONTROL[0],
            delta=1e-6,
        )

    def test_same_branch_pairs_do_not_disable_cytbd(self):
        for condition in ('cbd_branch_pair', 'cyd_branch_pair'):
            report = self._record(condition)
            run = report['runs'][condition]
            self.assertFalse(run['cytbd_disabled'])
            self.assertNotEqual(run['branch_status']['cbdAB'], run['branch_status']['cydAB'])

    def test_repeated_condition_updates_without_duplication(self):
        first = self._record('single_b0978')
        second = self._record('single_b0978', existing=first)
        self.assertEqual(second['recorded_run_count'], 1)
        self.assertEqual(len([run for run in second['runs'].values() if run]), 1)

    def test_invalid_attempt_preserves_previous_evidence(self):
        report = self._complete()
        invalid = self._record(
            'wild_type',
            existing=report,
            method='FBA',
        )
        self.assertFalse(invalid['current_run_recorded'])
        self.assertEqual(invalid['recorded_run_count'], 6)
        self.assertTrue(invalid['unique_cut_set_supported'])
        self.assertEqual(invalid['runs'], report['runs'])
        self.assertIn('Use pFBA', ' '.join(invalid['current_issues']))

    def test_wrong_objective_and_changed_environment_are_rejected(self):
        wrong_objective = self._record('wild_type', objective='EX_ac_e')
        self.assertFalse(wrong_objective['current_run_recorded'])
        changed = self._record(
            'wild_type',
            reactions=self._reactions(changed=simulation.MISSION32_OXYGEN_REACTION),
        )
        self.assertFalse(changed['current_run_recorded'])
        upper = self._record(
            'wild_type',
            reactions=self._reactions(upper_changed=simulation.MISSION32_ACETATE_REACTION),
        )
        self.assertFalse(upper['current_run_recorded'])

    def test_incomplete_payload_and_unlisted_genotype_are_rejected(self):
        incomplete_genes = self._record('wild_type', genes=self._genes('wild_type', incomplete=True))
        self.assertFalse(incomplete_genes['current_run_recorded'])
        incomplete_bounds = self._record('wild_type', reactions=self._reactions(incomplete=True))
        self.assertFalse(incomplete_bounds['current_run_recorded'])
        unlisted = self._record('wild_type', genes=self._genes('wild_type', extra='b0979'))
        self.assertFalse(unlisted['current_run_recorded'])

    def test_extra_third_knockout_is_rejected(self):
        report = self._record(
            'cross_branch_pair',
            genes=self._genes('cross_branch_pair', extra='b0979'),
            disabled=['CYTBD'],
        )
        self.assertFalse(report['current_run_recorded'])
        self.assertIsNone(report['current_condition'])

    def test_infeasible_is_never_accepted_as_a_numeric_row(self):
        growth, glucose, oxygen, acetate, ethanol, formate, total, active = self.CROSS
        report = self._record(
            'cross_branch_pair',
            objective_result='INFEASIBLE',
            production=self._production(growth, total, active),
            medium=self._medium(glucose, oxygen, acetate, ethanol, formate),
        )
        self.assertFalse(report['current_run_recorded'])
        self.assertIn('INFEASIBLE', ' '.join(report['current_issues']))

    def test_missing_exchange_value_is_not_fabricated_as_zero(self):
        growth, glucose, oxygen, acetate, ethanol, formate, total, active = self.CROSS
        report = self._record(
            'cross_branch_pair',
            medium=self._medium(
                glucose, oxygen, acetate, ethanol, formate,
                missing=simulation.MISSION32_OXYGEN_REACTION,
            ),
        )
        self.assertFalse(report['current_run_recorded'])
        self.assertIn('Numeric oxygen', ' '.join(report['current_issues']))

    def test_missing_byproduct_evidence_is_rejected(self):
        growth, glucose, oxygen, acetate, ethanol, formate, total, active = self.CROSS
        report = self._record(
            'cross_branch_pair',
            medium=self._medium(
                glucose, oxygen, acetate, ethanol, formate,
                missing=simulation.MISSION32_FORMATE_REACTION,
            ),
        )
        self.assertFalse(report['current_run_recorded'])
        self.assertIn('acetate, ethanol and formate', ' '.join(report['current_issues']))

    def test_gpr_inconsistency_is_rejected(self):
        report = self._record('cross_branch_pair', disabled=[])
        self.assertFalse(report['current_run_recorded'])
        self.assertIn('GPR', ' '.join(report['current_issues']))
        control = self._record('wild_type', disabled=['CYTBD'])
        self.assertFalse(control['current_run_recorded'])

    def test_diagnostics_are_strictly_validated(self):
        growth, glucose, oxygen, acetate, ethanol, formate, total, active = self.CONTROL
        cases = [
            self._production(growth, total, active, biomass=growth + 0.1),
            self._production(growth, total, active, diagnostics={'method': 'FBA'}),
            self._production(growth, total, active, diagnostics={'method_score_name': 'wrong'}),
            self._production(growth, total, active, diagnostics={'total_absolute_flux': total + 1.0}),
            self._production(growth, total, active, diagnostics={'active_reaction_count': None}),
        ]
        for production in cases:
            with self.subTest(production=production):
                report = self._record('wild_type', production=production)
                self.assertFalse(report['current_run_recorded'])

    def test_cross_branch_requires_reduced_viable_growth_not_zero(self):
        growth, glucose, oxygen, acetate, ethanol, formate, total, active = self.CROSS
        zero = self._record(
            'cross_branch_pair',
            objective_result=0.0,
            production=self._production(0.0, total, active),
        )
        self.assertFalse(zero['current_run_recorded'])
        high = self._record(
            'cross_branch_pair',
            objective_result=0.8,
            production=self._production(0.8, total, active),
        )
        self.assertFalse(high['current_run_recorded'])

    def test_cross_branch_requires_zero_oxygen_and_byproducts(self):
        growth, glucose, oxygen, acetate, ethanol, formate, total, active = self.CROSS
        oxygen_bad = self._record(
            'cross_branch_pair',
            medium=self._medium(glucose, 2.0, acetate, ethanol, formate),
        )
        self.assertFalse(oxygen_bad['current_run_recorded'])
        byproduct_bad = self._record(
            'cross_branch_pair',
            medium=self._medium(glucose, oxygen, acetate, ethanol, 0.0),
        )
        self.assertFalse(byproduct_bad['current_run_recorded'])

    def test_answer_aliases_and_rejections(self):
        report = self._complete()
        for answer in (
            'b0978 + b0733',
            'b0733 and b0978',
            'cbdA + cydA',
            'cross-branch pair',
            'one gene from each branch',
            'uma subunidade de cada complexo',
        ):
            with self.subTest(answer=answer):
                self.assertTrue(simulation.mission32_answer_matches(answer, report))
        for answer in (
            'b0978',
            'b0733',
            'b0978+b0979',
            'b0733+b0734',
            'CYTBD',
            'oxygen',
            'b0978+b0733+b0979',
        ):
            with self.subTest(answer=answer):
                self.assertFalse(simulation.mission32_answer_matches(answer, report))

    def test_answer_requires_complete_ready_evidence(self):
        report = self._record('cross_branch_pair')
        self.assertFalse(simulation.mission32_answer_matches('b0978+b0733', report))

    def test_report_presents_evidence_without_explicit_answer_sentence(self):
        report = self._complete()
        text = simulation.build_mission32_respiratory_cut_set_report_text(report)
        self.assertIn('Evidence complete.', text)
        self.assertIn('Cross-branch phenotype:', text)
        self.assertIn('Other cross-branch combinations', text)
        self.assertNotIn('The answer is', text)
        self.assertNotIn('Submit b0978', text)
        self.assertIn('Question:', text)

    def test_invalid_report_mentions_preserved_evidence(self):
        report = self._complete()
        invalid = self._record('wild_type', existing=report, method='FBA')
        text = simulation.build_mission32_respiratory_cut_set_report_text(invalid)
        self.assertIn('Latest run was not recorded:', text)
        self.assertIn('Previously valid Mission 32 cut-set evidence remains available.', text)
        self.assertIn('Evidence complete.', text)

    def test_state_is_json_serialisable(self):
        json.dumps(self._complete())

    def test_remote_wrapper_reuses_visible_result_without_http(self):
        sentinel = {'ok': True}
        with patch.object(simulation, 'run_mission32_respiratory_cut_set_check', return_value=sentinel) as local:
            self.assertIs(
                simulation.run_mission32_respiratory_cut_set_check_remote('https://unused', ('visible',)),
                sentinel,
            )
        local.assert_called_once_with(('visible',))
        source = inspect.getsource(simulation.run_mission32_respiratory_cut_set_check_remote)
        self.assertNotIn('_http_post_json', source)

    def test_save_load_web_contract_round_trip(self):
        sample = {'mission_id': '32', 'check_version': 2, 'nested': {'value': 1}}
        original_web = save_load._IS_WEB
        original_store = dict(save_load._MEMSTORE)
        try:
            save_load._IS_WEB = True
            save_load._MEMSTORE.clear()
            save_load.save_mission32_respiratory_cut_set_check(sample)
            self.assertEqual(save_load.load_mission32_respiratory_cut_set_check(), sample)
            save_load.clear_mission32_respiratory_cut_set_check()
            self.assertIsNone(save_load.load_mission32_respiratory_cut_set_check())
        finally:
            save_load._IS_WEB = original_web
            save_load._MEMSTORE.clear()
            save_load._MEMSTORE.update(original_store)

    def test_save_load_desktop_contract_round_trip(self):
        sample = {'mission_id': '32', 'check_version': 2, 'nested': {'value': 2}}
        original_web = save_load._IS_WEB
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with patch.object(
                    save_load,
                    'get_save_path',
                    side_effect=lambda filename: str(Path(tmpdir) / filename),
                ):
                    save_load._IS_WEB = False
                    save_load.save_mission32_respiratory_cut_set_check(sample)
                    self.assertEqual(save_load.load_mission32_respiratory_cut_set_check(), sample)
                    save_load.clear_mission32_respiratory_cut_set_check()
                    self.assertIsNone(save_load.load_mission32_respiratory_cut_set_check())
        finally:
            save_load._IS_WEB = original_web

    def test_dr_chen_player_level_and_window_wiring(self):
        mission32 = (PROJECT_ROOT / 'code' / 'mission32.py').read_text()
        player = (PROJECT_ROOT / 'code' / 'player.py').read_text()
        level = (PROJECT_ROOT / 'code' / 'level.py').read_text()
        window = (PROJECT_ROOT / 'code' / 'window.py').read_text()
        self.assertIn('class Mission32', mission32)
        self.assertIn('graphics/dialogues/chen.jpg', mission32)
        self.assertIn('talk_32', player)
        self.assertIn("name == 'Mission32'", player)
        self.assertIn('from mission32 import Mission32', level)
        self.assertIn("obj.name == 'Mission32'", level)
        self.assertIn('self.talk_32_active', level)
        self.assertIn("('32', list(MISSION32_GENE_NAMES))", window)
        self.assertIn('run_mission32_respiratory_cut_set_check', window)
        self.assertIn("label_id='mission32_respiratory_cut_set_check'", window)
        window_tree = ast.parse(window)
        defined_functions = {
            node.name for node in window_tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertIn('_build_mission32_text', defined_functions)

    def test_backend_pfba_contract_when_dependencies_exist(self):
        backend_dir = PROJECT_ROOT / 'backend'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        try:
            from app.schemas import SimulateRequest
            from app.simulator import simulate as backend_simulate
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'Backend MEWpy/COBRApy unavailable: {exc}')

        default_env = simulation._build_default_env_conditions_payload()
        for condition, expected in (
            ('wild_type', self.CONTROL),
            ('cross_branch_pair', self.CROSS),
        ):
            request = SimulateRequest(
                method=simulation.MISSION32_METHOD,
                objective=simulation.MISSION32_GROWTH_OBJECTIVE,
                gene_knockouts=simulation.MISSION32_CONDITION_GENES[condition],
                env_conditions=default_env,
            )
            result = backend_simulate(request)
            self.assertEqual(result.status, 'ok')
            self.assertAlmostEqual(result.primary_objective_flux, expected[0], delta=1e-6)
            self.assertEqual(result.method_score_name, simulation.MISSION32_EXPECTED_SCORE_NAME)
            self.assertIsNotNone(result.fluxes)
            self.assertAlmostEqual(max(-result.fluxes['EX_o2_e'], 0.0), expected[2], delta=1e-5)
            self.assertAlmostEqual(max(result.fluxes['EX_ac_e'], 0.0), expected[3], delta=1e-5)
            self.assertAlmostEqual(max(result.fluxes['EX_etoh_e'], 0.0), expected[4], delta=1e-5)
            self.assertAlmostEqual(max(result.fluxes['EX_for_e'], 0.0), expected[5], delta=1e-5)

    def test_existing_tiled_object_is_used_and_no_new_backend_endpoint_added(self):
        map_text = (PROJECT_ROOT / 'data' / 'map_lb.tmx').read_text()
        backend = (PROJECT_ROOT / 'backend' / 'app' / 'main.py').read_text()
        self.assertIn('name="Mission32"', map_text)
        self.assertNotIn('name="Mission33"', map_text)
        self.assertIn('/simulate', backend)
        self.assertNotIn('/mission32', backend.lower())

    def test_dialogue_lines_are_short_and_documentation_exists(self):
        mission32 = (PROJECT_ROOT / 'code' / 'mission32.py').read_text()
        for fragment in (
            'Dr. Li is still completing your network training.',
            'Simple redundancy can hide inside a more complex GPR.',
            'Keep the aerobic default medium fixed.',
            'You separated a broken branch from a disabled reaction.',
        ):
            self.assertIn(fragment, mission32)
            self.assertLessEqual(len(fragment), 70)
        doc = (PROJECT_ROOT / 'data' / 'missions' / 'mission32.md').read_text()
        self.assertIn('Respiratory Complex Cut-Set', doc)
        self.assertIn('Dr. Chen', doc)
        self.assertIn('(b0978 AND b0979) OR (b0733 AND b0734)', doc)
        self.assertIn('INFEASIBLE', doc)
        self.assertIn('/simulate', doc)

    def test_sbml_contains_expected_nested_cytbd_gpr(self):
        model_path = PROJECT_ROOT / 'data' / 'models' / 'e_coli_core.xml.gz'
        ns = {
            'sbml': 'http://www.sbml.org/sbml/level3/version1/core',
            'fbc': 'http://www.sbml.org/sbml/level3/version1/fbc/version2',
        }
        with gzip.open(model_path, 'rb') as handle:
            root = ET.parse(handle).getroot()
        model = root.find('sbml:model', ns)
        reaction = next(
            item for item in model.find('sbml:listOfReactions', ns)
            if item.attrib['id'] == 'R_CYTBD'
        )
        association = reaction.find('fbc:geneProductAssociation', ns)
        text = ET.tostring(association, encoding='unicode')
        for gene_id in ('G_b0978', 'G_b0979', 'G_b0733', 'G_b0734'):
            self.assertIn(gene_id, text)
        self.assertEqual(len(association.findall('.//fbc:and', ns)), 2)
        self.assertEqual(len(association.findall('.//fbc:or', ns)), 1)

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
        cytbd = reaction_index['R_CYTBD']
        objective = np.zeros(len(reactions))
        objective[biomass] = -1.0

        for label, expected, disable_cytbd in (
            ('control', self.CONTROL, False),
            ('cross', self.CROSS, True),
        ):
            current = list(bounds)
            if disable_cytbd:
                current[cytbd] = (0.0, 0.0)
            primary = linprog(
                objective,
                A_eq=matrix,
                b_eq=np.zeros(len(species)),
                bounds=current,
                method='highs',
            )
            self.assertTrue(primary.success, (label, primary.message))
            self.assertAlmostEqual(primary.x[biomass], expected[0], delta=1e-6)

            count = len(reactions)
            secondary_objective = np.concatenate([np.zeros(count), np.ones(count)])
            secondary_matrix = np.hstack([matrix, np.zeros((len(species), count))])
            biomass_row = np.zeros(2 * count)
            biomass_row[biomass] = 1.0
            secondary_matrix = np.vstack([secondary_matrix, biomass_row])
            secondary_rhs = np.append(np.zeros(len(species)), primary.x[biomass])
            abs_constraints = []
            for index in range(count):
                positive = np.zeros(2 * count)
                positive[index] = 1.0
                positive[count + index] = -1.0
                abs_constraints.append(positive)
                negative = np.zeros(2 * count)
                negative[index] = -1.0
                negative[count + index] = -1.0
                abs_constraints.append(negative)
            secondary = linprog(
                secondary_objective,
                A_ub=np.array(abs_constraints),
                b_ub=np.zeros(2 * count),
                A_eq=secondary_matrix,
                b_eq=secondary_rhs,
                bounds=current + [(0.0, None)] * count,
                method='highs',
            )
            self.assertTrue(secondary.success)
            fluxes = secondary.x[:count]
            expected_fluxes = {
                'R_EX_glc__D_e': -expected[1],
                'R_EX_o2_e': -expected[2],
                'R_EX_ac_e': expected[3],
                'R_EX_etoh_e': expected[4],
                'R_EX_for_e': expected[5],
            }
            for reaction_id, value in expected_fluxes.items():
                self.assertAlmostEqual(fluxes[reaction_index[reaction_id]], value, delta=1e-5)
            self.assertAlmostEqual(sum(abs(value) for value in fluxes), expected[6], delta=1e-5)
            self.assertEqual(sum(abs(value) > 1e-9 for value in fluxes), expected[7])


if __name__ == '__main__':
    unittest.main()
