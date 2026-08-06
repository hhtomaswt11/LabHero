"""Regression tests for Mission 33 Reference-State Adjustment Footprint.

Run from the project root with:
    python3 tests/test_mission33.py
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


class Mission33RegressionTests(unittest.TestCase):
    AEROBIC_REFERENCE = {
        'growth': 0.873921507,
        'oxygen': 21.799493,
        'glucose': 10.0,
        'cytbd': 43.598985,
        'score': 518.422086,
        'total': 518.422086,
        'active': 48,
    }
    AEROBIC_ROOM = {
        'growth': 0.064334,
        'oxygen': 0.0,
        'glucose': 7.789928,
        'cytbd': 0.0,
        'score': 45.0,
        'total': 210.236688,
        'active': 59,
    }
    CLOSED_REFERENCE = {
        'growth': 0.211662950,
        'oxygen': 0.0,
        'glucose': 10.0,
        'cytbd': 0.0,
        'score': 335.650617,
        'total': 335.650617,
        'active': 47,
    }
    CLOSED_ROOM = {
        'growth': 0.205196,
        'oxygen': 0.0,
        'glucose': 9.788325,
        'cytbd': 0.0,
        'score': 0.0,
        'total': 328.849497,
        'active': 54,
    }

    def _genes(self, mutant=False, *, extra=None, incomplete=False):
        genes = simulation._build_active_genes_data()
        if mutant:
            for gene_id in simulation.MISSION33_TARGET_GENES:
                genes[gene_id] = False
        if extra:
            genes[extra] = False
        if incomplete:
            genes.pop(next(iter(genes)))
        return genes

    def _reactions(self, context, *, extra_change=None, incomplete=False):
        reactions = simulation._build_default_reactions_data()
        if context == 'oxygen_closed':
            index = list(simulation.REACTIONS.index).index(simulation.MISSION33_OXYGEN_REACTION)
            reactions[f'reaction_{index}_lb'] = False
        if extra_change:
            index = list(simulation.REACTIONS.index).index(extra_change)
            key = f'reaction_{index}_lb'
            reactions[key] = not reactions[key]
        if incomplete:
            reactions.pop(next(iter(reactions)))
        return reactions

    def _data_for_run(self, run_id):
        return {
            'aerobic_reference': self.AEROBIC_REFERENCE,
            'aerobic_room_mutant': self.AEROBIC_ROOM,
            'oxygen_closed_reference': self.CLOSED_REFERENCE,
            'oxygen_closed_room_mutant': self.CLOSED_ROOM,
        }[run_id]

    def _production(self, run_id, *, diagnostics=None, missing=None, error=None):
        data = self._data_for_run(run_id)
        is_room = run_id.endswith('_room_mutant')
        context = 'oxygen_closed' if run_id.startswith('oxygen_closed') else 'aerobic'
        reference = self.CLOSED_REFERENCE if context == 'oxygen_closed' else self.AEROBIC_REFERENCE
        method = simulation.MISSION33_MUTANT_METHOD if is_room else simulation.MISSION33_REFERENCE_METHOD
        score_name = (
            simulation.MISSION33_ROOM_SCORE_NAME
            if is_room else simulation.MISSION33_PFBA_SCORE_NAME
        )
        method_diagnostics = {
            'method': method,
            'objective_reaction': simulation.MISSION33_GROWTH_OBJECTIVE,
            'primary_objective_flux': data['growth'],
            'method_score': data['score'],
            'method_score_name': score_name,
            'total_absolute_flux': data['total'],
            'active_reaction_count': data['active'],
            'cytbd_flux': data['cytbd'],
        }
        if is_room:
            method_diagnostics.update({
                'reference_method': simulation.MISSION33_REFERENCE_METHOD,
                'reference_objective_reaction': simulation.MISSION33_GROWTH_OBJECTIVE,
                'reference_primary_objective_flux': reference['growth'],
                'reference_uses_same_environment': True,
                'reference_has_no_gene_knockouts': True,
                'reference_cytbd_flux': reference['cytbd'],
                'room_delta': simulation.ROOM_DEFAULT_DELTA,
                'room_epsilon': simulation.ROOM_DEFAULT_EPSILON,
                'room_linear': simulation.ROOM_DEFAULT_LINEAR,
            })
        if diagnostics:
            method_diagnostics.update(diagnostics)
        if missing:
            method_diagnostics.pop(missing, None)
        result = {
            'selected_ids': [],
            'items': [],
            'objective_raw': data['growth'],
            'biomass_raw': data['growth'],
            'method_diagnostics': method_diagnostics,
        }
        if error:
            result['error'] = error
        return result

    def _medium(self, run_id, *, missing=None, error=None):
        data = self._data_for_run(run_id)
        rows = [
            (simulation.MISSION33_GLUCOSE_REACTION, -data['glucose']),
            (simulation.MISSION33_OXYGEN_REACTION, -data['oxygen']),
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
        run_id,
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
        data = self._data_for_run(run_id)
        context = 'oxygen_closed' if run_id.startswith('oxygen_closed') else 'aerobic'
        mutant = run_id.endswith('_room_mutant')
        if method is None:
            method = simulation.MISSION33_MUTANT_METHOD if mutant else simulation.MISSION33_REFERENCE_METHOD
        if objective_result is None:
            objective_result = data['growth']
        if production is None:
            production = self._production(run_id)
        if medium is None:
            medium = self._medium(run_id)
        expected_disabled = [simulation.MISSION33_TARGET_REACTION] if mutant else []
        with (
            patch.object(simulation, 'save_mission33_reference_adjustment_check'),
            patch.object(
                simulation,
                '_mission33_disabled_reactions',
                return_value=expected_disabled if disabled is None else disabled,
            ),
        ):
            return simulation._build_mission33_data(
                method,
                objective or simulation.MISSION33_GROWTH_OBJECTIVE,
                objective_result,
                genes if genes is not None else self._genes(mutant),
                reactions if reactions is not None else self._reactions(context),
                production_fluxes=production,
                medium_fluxes=medium,
                existing_report={} if existing is None else existing,
                objective_error=objective_error,
            )

    def _complete(self, order=None):
        report = {}
        for run_id in (order or simulation.MISSION33_RUN_ORDER):
            report = self._record(run_id, existing=report)
        return report

    def test_constants_and_progression(self):
        self.assertEqual(simulation.MISSION33_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION33_REFERENCE_METHOD, 'pFBA')
        self.assertEqual(simulation.MISSION33_MUTANT_METHOD, 'ROOM')
        self.assertEqual(simulation.MISSION33_TARGET_REACTION, 'CYTBD')
        self.assertEqual(simulation.MISSION33_TARGET_GENES, ['b0978', 'b0733'])
        self.assertEqual(simulation.MISSION33_REQUIRED_RUN_COUNT, 4)
        self.assertFalse(simulation.is_mission33_unlocked(['31']))
        self.assertTrue(simulation.is_mission33_unlocked(['32']))

    def test_initial_state_requires_four_visible_runs(self):
        with patch.object(simulation, 'save_mission33_reference_adjustment_check'):
            report = simulation.initialise_mission33_reference_adjustment_screen()
        self.assertEqual(report['recorded_run_count'], 0)
        self.assertEqual(report['missing_runs'], simulation.MISSION33_RUN_ORDER)
        self.assertFalse(report['evidence_ready'])

    def test_exact_environment_classification(self):
        self.assertEqual(
            simulation._mission33_environment_context(self._reactions('aerobic'))['context'],
            'aerobic',
        )
        self.assertEqual(
            simulation._mission33_environment_context(self._reactions('oxygen_closed'))['context'],
            'oxygen_closed',
        )
        status = simulation._mission33_environment_context(
            self._reactions('oxygen_closed', extra_change='EX_glc__D_e')
        )
        self.assertIsNone(status['context'])

    def test_run_classification_requires_method_genotype_and_context(self):
        self.assertEqual(
            simulation._mission33_run_id('pFBA', [], 'aerobic'),
            'aerobic_reference',
        )
        self.assertEqual(
            simulation._mission33_run_id('ROOM', ['b0733', 'b0978'], 'oxygen_closed'),
            'oxygen_closed_room_mutant',
        )
        self.assertIsNone(simulation._mission33_run_id('ROOM', [], 'aerobic'))
        self.assertIsNone(simulation._mission33_run_id('pFBA', ['b0978'], 'aerobic'))

    def test_complete_screen_supports_reference_state_explanation(self):
        report = self._complete()
        self.assertEqual(report['recorded_run_count'], 4)
        self.assertEqual(report['missing_runs'], [])
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['zero_adjustment_contexts'], ['oxygen_closed'])
        self.assertEqual(report['positive_adjustment_contexts'], ['aerobic'])
        self.assertEqual(report['reference_target_inactive_contexts'], ['oxygen_closed'])
        self.assertTrue(report['zero_footprint_explained'])
        self.assertTrue(report['ready_to_deliver'])
        self.assertAlmostEqual(report['room_score_by_context']['aerobic'], 45.0)
        self.assertAlmostEqual(report['room_score_by_context']['oxygen_closed'], 0.0)

    def test_any_run_order_is_accepted(self):
        report = self._complete(list(reversed(simulation.MISSION33_RUN_ORDER)))
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['recorded_run_count'], 4)

    def test_repeated_run_updates_without_duplication(self):
        report = self._complete()
        updated = self._record('aerobic_room_mutant', existing=report)
        self.assertEqual(updated['recorded_run_count'], 4)
        self.assertTrue(updated['evidence_ready'])

    def test_invalid_attempt_preserves_complete_evidence(self):
        report = self._complete()
        invalid = self._record(
            'aerobic_room_mutant',
            existing=report,
            method='FBA',
        )
        self.assertEqual(invalid['recorded_run_count'], 4)
        self.assertTrue(invalid['evidence_ready'])
        self.assertFalse(invalid['latest_attempt']['recorded'])
        self.assertEqual(invalid['runs'], report['runs'])

    def test_wrong_method_objective_and_genotype_are_rejected(self):
        cases = [
            dict(method='FBA'),
            dict(objective='EX_ac_e'),
            dict(genes=self._genes(False)),
            dict(genes=self._genes(True, extra='b0979')),
            dict(genes=self._genes(True, incomplete=True)),
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                report = self._record('aerobic_room_mutant', **kwargs)
                self.assertFalse(report['current_run_recorded'])
                self.assertTrue(report['current_issues'])

    def test_extra_environment_change_and_incomplete_bounds_are_rejected(self):
        for reactions in (
            self._reactions('aerobic', extra_change='EX_glc__D_e'),
            self._reactions('aerobic', incomplete=True),
        ):
            report = self._record('aerobic_reference', reactions=reactions)
            self.assertFalse(report['current_run_recorded'])

    def test_missing_exchange_and_method_diagnostics_are_rejected(self):
        cases = [
            dict(medium=self._medium('aerobic_reference', missing='EX_o2_e')),
            dict(medium=self._medium('aerobic_reference', missing='EX_glc__D_e')),
            dict(production=self._production('aerobic_reference', missing='method_score')),
            dict(production=self._production('aerobic_reference', missing='cytbd_flux')),
            dict(production=self._production('aerobic_reference', missing='active_reaction_count')),
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                report = self._record('aerobic_reference', **kwargs)
                self.assertFalse(report['current_run_recorded'])

    def test_infeasible_and_missing_values_are_not_fabricated_as_zero(self):
        report = self._record(
            'oxygen_closed_room_mutant',
            objective_result='Status: INFEASIBLE',
        )
        self.assertFalse(report['current_run_recorded'])
        production = self._production('oxygen_closed_room_mutant')
        production.pop('biomass_raw')
        production.pop('objective_raw')
        production['method_diagnostics']['primary_objective_flux'] = None
        report = self._record(
            'oxygen_closed_room_mutant',
            objective_result='not available',
            production=production,
        )
        self.assertFalse(report['current_run_recorded'])

    def test_room_requires_integer_score_zero_cytbd_and_measurable_glucose(self):
        cases = [
            self._production('aerobic_room_mutant', diagnostics={'method_score': 45.5}),
            self._production('aerobic_room_mutant', diagnostics={'cytbd_flux': 0.25}),
            self._production('aerobic_room_mutant', missing='cytbd_flux'),
        ]
        for production in cases:
            with self.subTest(production=production):
                report = self._record('aerobic_room_mutant', production=production)
                self.assertFalse(report['current_run_recorded'])

        medium = self._medium('aerobic_room_mutant')
        for item in medium['items']:
            if item['reaction_id'] == simulation.MISSION33_GLUCOSE_REACTION:
                item['raw_flux'] = 0.0
                item['uptake_flux'] = 0.0
        report = self._record('aerobic_room_mutant', medium=medium)
        self.assertFalse(report['current_run_recorded'])

    def test_room_metadata_is_strictly_validated(self):
        bad_metadata = [
            {'reference_method': 'FBA'},
            {'reference_objective_reaction': 'EX_ac_e'},
            {'reference_uses_same_environment': False},
            {'reference_has_no_gene_knockouts': False},
            {'reference_primary_objective_flux': None},
            {'reference_cytbd_flux': None},
            {'room_linear': True},
            {'room_delta': 0.10},
            {'room_epsilon': 0.10},
            {'method_score_name': 'primary_objective_flux'},
        ]
        for override in bad_metadata:
            with self.subTest(override=override):
                report = self._record(
                    'aerobic_room_mutant',
                    production=self._production('aerobic_room_mutant', diagnostics=override),
                )
                self.assertFalse(report['current_run_recorded'])

    def test_room_reference_metadata_must_match_visible_reference(self):
        report = self._record('aerobic_reference')
        mismatch = self._production(
            'aerobic_room_mutant',
            diagnostics={'reference_cytbd_flux': 0.0},
        )
        report = self._record(
            'aerobic_room_mutant', existing=report, production=mismatch
        )
        for run_id in ('oxygen_closed_reference', 'oxygen_closed_room_mutant'):
            report = self._record(run_id, existing=report)
        self.assertFalse(report['reference_match_by_context']['aerobic'])
        self.assertFalse(report['evidence_ready'])

    def test_positive_and_zero_score_pattern_is_required(self):
        report = {}
        for run_id in simulation.MISSION33_RUN_ORDER:
            production = None
            if run_id == 'aerobic_room_mutant':
                production = self._production(run_id, diagnostics={'method_score': 0.0})
            report = self._record(run_id, existing=report, production=production)
        self.assertFalse(report['zero_footprint_explained'])
        self.assertFalse(report['evidence_ready'])

    def test_answer_is_short_functional_state_not_numeric_context_or_gene_name(self):
        report = self._complete()
        accepted = [
            'unused',
            'idle',
            'not used',
            'functionally unused',
            'unutilised',
            'unutilized',
            'não utilizada',
            'não usado',
            'sem uso',
        ]
        for answer in accepted:
            self.assertTrue(simulation.mission33_answer_matches(answer, report), answer)
        for answer in (
            '0',
            '0.000',
            'zero',
            'zero flux',
            'inactive',
            'anaerobic',
            'anaeróbio',
            'oxygen closed',
            'b0978+b0733',
            'CYTBD',
            'ROOM',
            'CYTBD was already inactive in the reference',
        ):
            self.assertFalse(simulation.mission33_answer_matches(answer, report), answer)

    def test_report_is_evidence_based_and_does_not_reveal_answer(self):
        report = self._complete()
        text = simulation.build_mission33_reference_adjustment_report_text(report)
        self.assertIn('Runs recorded: 4/4', text)
        self.assertIn('43.599', text)
        self.assertIn('45.000', text)
        self.assertIn('0.000', text)
        self.assertIn('CYTBD was already', text)
        self.assertNotIn('The answer is', text)
        self.assertNotIn('Submit anaerobic', text)
        self.assertNotIn('Submit CYTBD', text)

    def test_state_is_json_serialisable(self):
        report = self._complete()
        encoded = json.dumps(report)
        decoded = json.loads(encoded)
        self.assertTrue(decoded['evidence_ready'])
        self.assertEqual(decoded['zero_adjustment_contexts'], ['oxygen_closed'])

    def test_save_load_persistence_round_trip(self):
        report = self._complete()
        original_web = save_load._IS_WEB
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(save_load, '_IS_WEB', False),
                patch.object(save_load, 'get_save_path', side_effect=lambda name: str(Path(directory) / name)),
            ):
                save_load.save_mission33_reference_adjustment_check(report)
                loaded = save_load.load_mission33_reference_adjustment_check()
                self.assertEqual(loaded, report)
                save_load.clear_mission33_reference_adjustment_check()
                self.assertIsNone(save_load.load_mission33_reference_adjustment_check())
        save_load._IS_WEB = original_web

    def test_local_room_uses_explicit_pfba_reference_before_knockouts(self):
        source = inspect.getsource(simulation._simulate_local_room_with_reference)
        self.assertIn('reference_solution = pfba(reference_model)', source)
        self.assertIn('solve_integer_room_highs(', source)
        self.assertIn('reference_solution,', source)
        self.assertIn('delta=ROOM_DEFAULT_DELTA', source)
        self.assertIn('epsilon=ROOM_DEFAULT_EPSILON', source)
        self.assertIn('time_limit_seconds=ROOM_HIGHS_TIME_LIMIT_SECONDS', source)
        self.assertLess(source.index('reference_solution = pfba(reference_model)'), source.index('mutant_model = model.copy()'))
        self.assertIn("'reference_has_no_gene_knockouts': True", source)
        self.assertIn("'reference_uses_same_environment': True", source)

    def test_local_room_builds_reference_before_mutant_knockout(self):
        class FakeModelCopy:
            def __init__(self, name):
                self.name = name
                self.objective = None
                self.applied = []

        class FakeBaseModel:
            def __init__(self):
                self.copies = []

            def copy(self):
                copy_model = FakeModelCopy(f'copy_{len(self.copies)}')
                self.copies.append(copy_model)
                return copy_model

        reference_solution = types.SimpleNamespace(
            status='optimal',
            fluxes={
                simulation.MISSION33_GROWTH_OBJECTIVE: self.AEROBIC_REFERENCE['growth'],
                simulation.MISSION33_TARGET_REACTION: self.AEROBIC_REFERENCE['cytbd'],
            },
        )
        room_solution = types.SimpleNamespace(
            status='optimal',
            objective_value=45.0,
            fluxes={
                simulation.MISSION33_GROWTH_OBJECTIVE: self.AEROBIC_ROOM['growth'],
                simulation.MISSION33_TARGET_REACTION: 0.0,
            },
        )
        calls = {}

        def fake_pfba(reference_model):
            calls['pfba_model'] = reference_model
            return reference_solution

        def fake_room_solver(mutant_model, reference_solution_arg, **kwargs):
            calls['room_model'] = mutant_model
            calls['room_reference_solution'] = reference_solution_arg
            calls['room_kwargs'] = kwargs
            return room_solution

        fake_flux_analysis = types.ModuleType('cobra.flux_analysis')
        fake_flux_analysis.pfba = fake_pfba
        fake_cobra = types.ModuleType('cobra')
        fake_cobra.flux_analysis = fake_flux_analysis
        base_model = FakeBaseModel()

        def record_constraints(copy_model, constraints):
            copy_model.applied.append(dict(constraints))

        with (
            patch.dict(sys.modules, {
                'cobra': fake_cobra,
                'cobra.flux_analysis': fake_flux_analysis,
            }),
            patch.object(simulation, 'model', base_model),
            patch.object(
                simulation,
                '_build_envconditions_from_reactions',
                return_value={'EX_o2_e': (-1000.0, 1000.0)},
            ),
            patch.object(simulation, '_knocked_out_genes', return_value=['b0978', 'b0733']),
            patch.object(simulation, 'disabled_reaction_ids', return_value=['CYTBD']),
            patch.object(simulation, '_apply_constraints_to_cobra_model', side_effect=record_constraints),
            patch.object(simulation, 'solve_integer_room_highs', side_effect=fake_room_solver),
        ):
            result, score, metadata = simulation._simulate_local_room_with_reference(
                simulation.MISSION33_GROWTH_OBJECTIVE,
                self._genes(True),
                self._reactions('aerobic'),
            )

        self.assertIs(result, room_solution)
        self.assertEqual(score, 45.0)
        self.assertEqual(len(base_model.copies), 2)
        reference_model, mutant_model = base_model.copies
        self.assertIs(calls['pfba_model'], reference_model)
        self.assertIs(calls['room_model'], mutant_model)
        self.assertEqual(reference_model.applied, [{'EX_o2_e': (-1000.0, 1000.0)}])
        self.assertEqual(
            mutant_model.applied,
            [
                {'EX_o2_e': (-1000.0, 1000.0)},
                {'CYTBD': (0.0, 0.0)},
            ],
        )
        self.assertIs(calls['room_reference_solution'], reference_solution)
        self.assertEqual(calls['room_kwargs']['delta'], simulation.ROOM_DEFAULT_DELTA)
        self.assertEqual(calls['room_kwargs']['epsilon'], simulation.ROOM_DEFAULT_EPSILON)
        self.assertEqual(
            calls['room_kwargs']['time_limit_seconds'],
            simulation.ROOM_HIGHS_TIME_LIMIT_SECONDS,
        )
        self.assertEqual(metadata['reference_method'], 'pFBA')
        self.assertTrue(metadata['reference_has_no_gene_knockouts'])
        self.assertAlmostEqual(metadata['reference_cytbd_flux'], 43.598985)
        self.assertEqual(metadata['gpr_disabled_reactions'], ['CYTBD'])

    def test_highs_room_solver_has_integer_formulation_and_safety_limit(self):
        room_solver = (PROJECT_ROOT / 'code' / 'room_milp.py').read_text()
        backend_solver = (PROJECT_ROOT / 'backend' / 'app' / 'room_milp.py').read_text()
        for source in (room_solver, backend_solver):
            self.assertIn('from scipy.optimize import Bounds, LinearConstraint, milp', source)
            self.assertIn('np.ones(reaction_count, dtype=int)', source)
            self.assertIn('mip_rel_gap', source)
            self.assertIn('time_limit', source)
            self.assertIn('ROOM_HIGHS_TIME_LIMIT_SECONDS = 12.0', source)
            self.assertNotIn('cobra.flux_analysis import room', source)

    def test_highs_room_helper_solves_a_small_integer_problem(self):
        from room_milp import solve_integer_room_highs

        class Metabolite:
            def __init__(self, metabolite_id):
                self.id = metabolite_id

        class Reaction:
            def __init__(self, reaction_id, lower, upper, metabolites):
                self.id = reaction_id
                self.lower_bound = lower
                self.upper_bound = upper
                self.metabolites = metabolites

        metabolite = Metabolite('A_c')
        uptake = Reaction('UPTAKE', 0.0, 10.0, {metabolite: 1.0})
        use = Reaction('USE', 0.0, 0.0, {metabolite: -1.0})
        fake_model = types.SimpleNamespace(
            reactions=[uptake, use],
            metabolites=[metabolite],
        )
        reference = types.SimpleNamespace(
            fluxes={'UPTAKE': 10.0, 'USE': 10.0},
        )

        result = solve_integer_room_highs(
            fake_model,
            reference,
            time_limit_seconds=5.0,
        )

        self.assertEqual(result.status, 'optimal')
        self.assertEqual(result.objective_value, 2.0)
        self.assertAlmostEqual(result.fluxes['UPTAKE'], 0.0, delta=1e-8)
        self.assertAlmostEqual(result.fluxes['USE'], 0.0, delta=1e-8)
        self.assertEqual(result.room_solver, 'scipy-highs-milp')

    def test_backend_room_uses_same_explicit_reference_contract(self):
        backend_text = (PROJECT_ROOT / 'backend' / 'app' / 'simulator.py').read_text()
        self.assertIn('def _simulate_room_with_explicit_reference', backend_text)
        self.assertIn('reference_solution = pfba(reference_model)', backend_text)
        self.assertIn('solve_integer_room_highs(', backend_text)
        self.assertIn('reference_solution,', backend_text)
        self.assertIn('delta=_ROOM_DELTA', backend_text)
        self.assertIn('epsilon=_ROOM_EPSILON', backend_text)
        self.assertIn('time_limit_seconds=ROOM_HIGHS_TIME_LIMIT_SECONDS', backend_text)
        self.assertIn('elif req.method == "ROOM"', backend_text)
        schema_text = (PROJECT_ROOT / 'backend' / 'app' / 'schemas.py').read_text()
        for field in (
            'reference_method', 'reference_primary_objective_flux',
            'reference_cytbd_flux', 'room_delta', 'room_epsilon', 'room_linear',
            'room_solver', 'room_time_limit_seconds',
        ):
            self.assertIn(field, schema_text)

    def test_remote_visible_result_preserves_room_metadata(self):
        response = {
            'objective': simulation.MISSION33_GROWTH_OBJECTIVE,
            'objective_reaction': simulation.MISSION33_GROWTH_OBJECTIVE,
            'method': 'ROOM',
            'result': self.AEROBIC_ROOM['growth'],
            'status': 'ok',
            'primary_objective_flux': self.AEROBIC_ROOM['growth'],
            'method_score': 45.0,
            'method_score_name': simulation.MISSION33_ROOM_SCORE_NAME,
            'total_absolute_flux': self.AEROBIC_ROOM['total'],
            'active_reaction_count': self.AEROBIC_ROOM['active'],
            'reference_method': 'pFBA',
            'reference_objective_reaction': simulation.MISSION33_GROWTH_OBJECTIVE,
            'reference_primary_objective_flux': self.AEROBIC_REFERENCE['growth'],
            'reference_uses_same_environment': True,
            'reference_has_no_gene_knockouts': True,
            'reference_cytbd_flux': self.AEROBIC_REFERENCE['cytbd'],
            'room_delta': simulation.ROOM_DEFAULT_DELTA,
            'room_epsilon': simulation.ROOM_DEFAULT_EPSILON,
            'room_linear': False,
            'room_solver': 'scipy-highs-milp',
            'room_time_limit_seconds': 12.0,
            'fluxes': {
                simulation.MISSION33_GROWTH_OBJECTIVE: self.AEROBIC_ROOM['growth'],
                'CYTBD': 0.0,
                'EX_glc__D_e': -self.AEROBIC_ROOM['glucose'],
                'EX_o2_e': 0.0,
            },
        }
        payload = {
            'method': 'ROOM',
            'objective': simulation.MISSION33_GROWTH_OBJECTIVE,
            'gene_knockouts': list(simulation.MISSION33_TARGET_GENES),
            'env_conditions': simulation._build_default_env_conditions_payload(),
        }
        with (
            patch.object(simulation, '_build_request_payload', return_value=payload),
            patch.object(simulation, '_read_selected_production_fluxes', return_value=[]),
            patch.object(simulation, '_http_post_json', return_value=response),
        ):
            result = simulation.run_simul_remote('http://example.test')
        diagnostics = result[2]['method_diagnostics']
        self.assertEqual(diagnostics['method_score'], 45.0)
        self.assertEqual(diagnostics['reference_method'], 'pFBA')
        self.assertAlmostEqual(diagnostics['reference_cytbd_flux'], 43.598985)
        self.assertFalse(diagnostics['room_linear'])
        self.assertEqual(diagnostics['room_solver'], 'scipy-highs-milp')
        self.assertEqual(diagnostics['room_time_limit_seconds'], 12.0)
        self.assertEqual(diagnostics['cytbd_flux'], 0.0)

    def test_window_displays_room_score_reference_and_mission_report(self):
        window = (PROJECT_ROOT / 'code' / 'window.py').read_text()
        self.assertIn("elif method_name == 'ROOM'", window)
        self.assertIn('ROOM significant-change criterion', window)
        self.assertIn('Reference CYTBD flux', window)
        self.assertIn('Mutant CYTBD flux', window)
        self.assertIn('MILP solver', window)
        self.assertIn('Simulation failed safely', window)
        self.assertIn("('33', list(MISSION33_TARGET_GENES))", window)
        self.assertIn('run_mission33_reference_adjustment_check', window)
        self.assertIn("label_id='mission33_reference_adjustment_check'", window)
        tree = ast.parse(window)
        functions = {
            node.name for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertIn('_build_mission33_text', functions)

    def test_dr_chen_controls_mission_33_without_new_tiled_object(self):
        mission32 = (PROJECT_ROOT / 'code' / 'mission32.py').read_text()
        mission33 = (PROJECT_ROOT / 'code' / 'mission33.py').read_text()
        map_text = (PROJECT_ROOT / 'data' / 'map_lb.tmx').read_text()
        self.assertIn('from mission33 import Mission33_info', mission32)
        self.assertIn('self.menu33 = Mission33_info', mission32)
        self.assertIn("elif '33' in self.missions_activated", mission32)
        self.assertIn("elif '32' in self.missions_completed", mission32)
        self.assertIn('class Mission33_info', mission33)
        self.assertIn('CYTBD was already', mission33)
        self.assertIn('name="Mission32"', map_text)
        self.assertNotIn('name="Mission33"', map_text)

    def test_dialogue_lines_are_short(self):
        mission32 = (PROJECT_ROOT / 'code' / 'mission32.py').read_text()
        fragments = (
            'You separated a broken branch from a disabled reaction.',
            'Now measure its adjustment footprint from two references.',
            'Build matched wild-type pFBA references for both contexts.',
            'You separated genetic loss from reference-state use.',
        )
        for fragment in fragments:
            self.assertIn(fragment, mission32)
            self.assertLessEqual(len(fragment), 70)

    def test_mission_and_book_documentation_exists(self):
        mission_doc = (PROJECT_ROOT / 'data' / 'missions' / 'mission33.md').read_text()
        self.assertIn('Reference-State Adjustment Footprint', mission_doc)
        self.assertIn('wild-type pFBA reference', mission_doc)
        self.assertIn('significant-change score', mission_doc)
        self.assertIn('/simulate', mission_doc)
        self.assertNotIn('The answer is anaerobic', mission_doc)
        book = (PROJECT_ROOT / 'data' / 'books' / 'How to Simulate.md').read_text()
        for term in ('pre-knockout', 'same environment', 'delta', 'epsilon', 'integer ROOM'):
            self.assertIn(term, book)

    def test_independent_sbml_room_milp_scores(self):
        try:
            import numpy as np
            from scipy.optimize import Bounds, LinearConstraint, linprog, milp
            from scipy.sparse import csc_matrix
        except Exception as exc:
            self.skipTest(f'SciPy MILP unavailable: {exc}')

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
        reaction_ids = [item.attrib['id'] for item in reaction_elements]
        reaction_index = {item: index for index, item in enumerate(reaction_ids)}
        matrix = np.zeros((len(species), len(reaction_ids)))
        lower = []
        upper = []
        for column, reaction in enumerate(reaction_elements):
            lower.append(parameters[reaction.attrib[f"{{{ns['fbc']}}}lowerFluxBound"]])
            upper.append(parameters[reaction.attrib[f"{{{ns['fbc']}}}upperFluxBound"]])
            reactants = reaction.find('sbml:listOfReactants', ns)
            if reactants is not None:
                for item in reactants:
                    matrix[species_index[item.attrib['species']], column] -= float(item.attrib.get('stoichiometry', '1'))
            products = reaction.find('sbml:listOfProducts', ns)
            if products is not None:
                for item in products:
                    matrix[species_index[item.attrib['species']], column] += float(item.attrib.get('stoichiometry', '1'))
        lower = np.array(lower, dtype=float)
        upper = np.array(upper, dtype=float)
        biomass = reaction_index['R_BIOMASS_Ecoli_core_w_GAM']
        cytbd = reaction_index['R_CYTBD']
        oxygen = reaction_index['R_EX_o2_e']
        count = len(reaction_ids)

        def pfba_reference(lb, ub):
            primary_objective = np.zeros(count)
            primary_objective[biomass] = -1.0
            primary = linprog(
                primary_objective,
                A_eq=matrix,
                b_eq=np.zeros(len(species)),
                bounds=list(zip(lb, ub)),
                method='highs',
            )
            self.assertTrue(primary.success, primary.message)
            target = primary.x[biomass]
            secondary_objective = np.concatenate([np.zeros(count), np.ones(count)])
            equality = np.block([
                [matrix, np.zeros((len(species), count))],
                [np.eye(1, count, biomass), np.zeros((1, count))],
            ])
            equality_rhs = np.append(np.zeros(len(species)), target)
            inequality = []
            for index in range(count):
                row = np.zeros(2 * count)
                row[index] = 1.0
                row[count + index] = -1.0
                inequality.append(row)
                row = np.zeros(2 * count)
                row[index] = -1.0
                row[count + index] = -1.0
                inequality.append(row)
            secondary = linprog(
                secondary_objective,
                A_ub=np.array(inequality),
                b_ub=np.zeros(2 * count),
                A_eq=equality,
                b_eq=equality_rhs,
                bounds=list(zip(lb, ub)) + [(0.0, None)] * count,
                method='highs',
            )
            self.assertTrue(secondary.success, secondary.message)
            return secondary.x[:count]

        def room_score(reference, lb, ub):
            objective = np.concatenate([np.zeros(count), np.ones(count)])
            integrality = np.concatenate([np.zeros(count), np.ones(count)])
            variable_lower = np.concatenate([lb, np.zeros(count)])
            variable_upper = np.concatenate([ub, np.ones(count)])
            equality = np.hstack([matrix, np.zeros((len(species), count))])
            rows = []
            upper_rhs = []
            for index, ref_flux in enumerate(reference):
                high = ref_flux + simulation.ROOM_DEFAULT_DELTA * abs(ref_flux) + simulation.ROOM_DEFAULT_EPSILON
                low = ref_flux - simulation.ROOM_DEFAULT_DELTA * abs(ref_flux) - simulation.ROOM_DEFAULT_EPSILON
                row = np.zeros(2 * count)
                row[index] = 1.0
                row[count + index] = -(ub[index] - high)
                rows.append(row)
                upper_rhs.append(high)
                row = np.zeros(2 * count)
                row[index] = -1.0
                row[count + index] = lb[index] - low
                rows.append(row)
                upper_rhs.append(-low)
            row = np.zeros(2 * count)
            row[biomass] = 1.0
            rows.append(row)
            upper_rhs.append(reference[biomass])
            constraint_matrix = np.vstack([equality, np.array(rows)])
            constraint_lower = np.concatenate([
                np.zeros(len(species)),
                np.full(len(rows), -np.inf),
            ])
            constraint_upper = np.concatenate([
                np.zeros(len(species)),
                np.array(upper_rhs),
            ])
            result = milp(
                objective,
                integrality=integrality,
                bounds=Bounds(variable_lower, variable_upper),
                constraints=LinearConstraint(
                    csc_matrix(constraint_matrix),
                    constraint_lower,
                    constraint_upper,
                ),
            )
            self.assertTrue(result.success, result.message)
            return result.fun, result.x[:count]

        results = {}
        for context in ('aerobic', 'oxygen_closed'):
            lb = lower.copy()
            ub = upper.copy()
            if context == 'oxygen_closed':
                lb[oxygen] = 0.0
            reference = pfba_reference(lb, ub)
            mutant_lb = lb.copy()
            mutant_ub = ub.copy()
            mutant_lb[cytbd] = 0.0
            mutant_ub[cytbd] = 0.0
            score, mutant = room_score(reference, mutant_lb, mutant_ub)
            results[context] = (reference, score, mutant)

        aerobic_reference, aerobic_score, aerobic_mutant = results['aerobic']
        closed_reference, closed_score, closed_mutant = results['oxygen_closed']
        self.assertAlmostEqual(aerobic_reference[cytbd], 43.598985, delta=1e-5)
        self.assertAlmostEqual(aerobic_score, 45.0, delta=1e-6)
        self.assertAlmostEqual(closed_reference[cytbd], 0.0, delta=1e-8)
        self.assertAlmostEqual(closed_score, 0.0, delta=1e-8)
        self.assertAlmostEqual(aerobic_mutant[oxygen], 0.0, delta=1e-8)
        self.assertAlmostEqual(closed_mutant[oxygen], 0.0, delta=1e-8)

    def test_backend_real_room_contract_when_dependencies_exist(self):
        backend_dir = PROJECT_ROOT / 'backend'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        try:
            from app.schemas import SimulateRequest
            from app.simulator import simulate as backend_simulate
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'Backend MEWpy/COBRApy unavailable: {exc}')

        for context, expected_score, expected_ref_cytbd in (
            ('aerobic', 45.0, 43.598985),
            ('oxygen_closed', 0.0, 0.0),
        ):
            env = simulation._build_default_env_conditions_payload()
            if context == 'oxygen_closed':
                env[simulation.MISSION33_OXYGEN_REACTION] = [0.0, env[simulation.MISSION33_OXYGEN_REACTION][1]]
            request = SimulateRequest(
                method='ROOM',
                objective=simulation.MISSION33_GROWTH_OBJECTIVE,
                gene_knockouts=simulation.MISSION33_TARGET_GENES,
                env_conditions=env,
            )
            result = backend_simulate(request)
            self.assertEqual(result.status, 'ok')
            self.assertEqual(result.method_score_name, simulation.MISSION33_ROOM_SCORE_NAME)
            self.assertAlmostEqual(result.method_score, expected_score, delta=1e-5)
            self.assertEqual(result.reference_method, 'pFBA')
            self.assertAlmostEqual(result.reference_cytbd_flux, expected_ref_cytbd, delta=1e-5)
            self.assertTrue(result.reference_uses_same_environment)
            self.assertTrue(result.reference_has_no_gene_knockouts)
            self.assertFalse(result.room_linear)
            self.assertEqual(result.room_solver, 'scipy-highs-milp')
            self.assertEqual(result.room_time_limit_seconds, 12.0)


if __name__ == '__main__':
    unittest.main()
