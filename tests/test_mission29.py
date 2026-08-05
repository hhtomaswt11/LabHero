"""Regression tests for Mission 29 isoenzyme redundancy screen.

Run from the project root with:
    python3 tests/test_mission29.py
"""
from __future__ import annotations

import gzip
import inspect
import json
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

# Let this dedicated test run in minimal CI containers. On the real project
# environment these fallbacks are not used.
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

import simulation  # noqa: E402
sys.platform = _original_platform


class Mission29RegressionTests(unittest.TestCase):
    GROWTH = {
        'wild_type_reference': 0.873921507,
        'b0118': 0.873921507,
        'b1276': 0.873921507,
        'aconitase': 0.0,
        'b1723': 0.873921507,
        'b3916': 0.873921507,
        'phosphofructokinase': 0.704036948,
        'b1676': 0.873921507,
        'b1854': 0.873921507,
        'pyruvate_kinase': 0.864926018,
    }

    def _genes(self, run_key):
        genes = simulation._build_active_genes_data()
        if run_key in simulation.MISSION29_SINGLE_GENES:
            genes[run_key] = False
        elif run_key in simulation.MISSION29_PAIR_ORDER:
            for gene_id in simulation.MISSION29_PAIRS[run_key]:
                genes[gene_id] = False
        return genes

    def _reactions(self, *, extra_change=None, incomplete=False):
        reactions = simulation._build_default_reactions_data()
        if extra_change:
            reaction_id, bound = extra_change
            index = list(simulation.REACTIONS.index).index(reaction_id)
            key = f'reaction_{index}_{bound}'
            reactions[key] = not bool(reactions[key])
        if incomplete:
            reactions.pop(next(iter(reactions)))
        return reactions

    def _disabled(self, run_key):
        if run_key in simulation.MISSION29_PAIR_ORDER:
            return list(simulation.MISSION29_PAIR_REACTIONS[run_key])
        return []

    def _production(self, growth, *, diagnostics=None, biomass=None, error=None):
        total = 56.866 if growth <= 0.001 else 500.0 + 20.0 * growth
        result = {
            'selected_ids': [],
            'items': [],
            'biomass_raw': growth if biomass is None else biomass,
            'method_diagnostics': {
                'method': simulation.MISSION29_METHOD,
                'objective_reaction': simulation.MISSION29_GROWTH_OBJECTIVE,
                'primary_objective_flux': growth,
                'method_score': total,
                'method_score_name': simulation.MISSION29_EXPECTED_SCORE_NAME,
                'total_absolute_flux': total,
                'active_reaction_count': 27 if growth <= 0.001 else 48,
            },
        }
        if diagnostics:
            result['method_diagnostics'].update(diagnostics)
        if error:
            result['error'] = error
        return result

    def _medium(self, growth, *, missing=None, glucose=None, oxygen=None, error=None):
        if glucose is None:
            glucose = -0.932 if growth <= 0.001 else -10.0
        if oxygen is None:
            oxygen = -1.864 if growth <= 0.001 else -21.8
        items = []
        for reaction_id, raw in (
            (simulation.MISSION27_GLUCOSE_REACTION, glucose),
            (simulation.MISSION27_OXYGEN_REACTION, oxygen),
        ):
            if reaction_id == missing:
                continue
            items.append({
                'reaction_id': reaction_id,
                'raw_flux': raw,
                'uptake_flux': max(-raw, 0.0),
                'secretion_flux': max(raw, 0.0),
            })
        result = {'items': items}
        if error:
            result['error'] = error
        return result

    def _record(self, run_key, *, existing=None, method=None, objective=None,
                genes=None, reactions=None, production=None, medium=None,
                objective_result=None, objective_error=None, disabled=None):
        growth = self.GROWTH[run_key]
        with (
            patch.object(simulation, 'save_mission29_redundancy_check'),
            patch.object(
                simulation,
                '_mission29_disabled_reactions',
                return_value=self._disabled(run_key) if disabled is None else disabled,
            ),
        ):
            return simulation._build_mission29_data(
                method or simulation.MISSION29_METHOD,
                objective or simulation.MISSION29_GROWTH_OBJECTIVE,
                growth if objective_result is None else objective_result,
                genes if genes is not None else self._genes(run_key),
                reactions if reactions is not None else self._reactions(),
                production_fluxes=production if production is not None else self._production(growth),
                medium_fluxes=medium if medium is not None else self._medium(growth),
                existing_report={} if existing is None else existing,
                objective_error=objective_error,
            )

    def _complete(self, order=None):
        order = order or [
            'wild_type_reference',
            *simulation.MISSION29_SINGLE_GENES,
            *simulation.MISSION29_PAIR_ORDER,
        ]
        report = {}
        for run_key in order:
            report = self._record(run_key, existing=report)
        return report

    def test_constants_and_progression(self):
        self.assertEqual(simulation.MISSION29_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION29_METHOD, 'pFBA')
        self.assertEqual(simulation.MISSION29_REQUIRED_RUN_COUNT, 10)
        self.assertEqual(simulation.MISSION29_EXPECTED_SYNTHETIC_PAIR, 'aconitase')
        self.assertFalse(simulation.is_mission29_unlocked([]))
        self.assertFalse(simulation.is_mission29_unlocked(['27']))
        self.assertTrue(simulation.is_mission29_unlocked(['28']))

    def test_initial_state_requires_ten_runs(self):
        with patch.object(simulation, 'save_mission29_redundancy_check'):
            report = simulation.initialise_mission29_redundancy_screen()
        self.assertEqual(report['recorded_run_count'], 0)
        self.assertEqual(report['required_run_count'], 10)
        self.assertEqual(len(report['missing_conditions']), 10)

    def test_complete_screen_supports_one_unique_synthetic_pair(self):
        report = self._complete()
        self.assertEqual(report['recorded_run_count'], 10)
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['synthetic_lethal_candidates'], ['aconitase'])
        self.assertEqual(report['unique_synthetic_pair'], 'aconitase')
        self.assertTrue(report['unique_synthetic_lethality_supported'])
        self.assertTrue(report['ready_to_deliver'])

    def test_runs_can_arrive_in_any_order(self):
        order = [
            'pyruvate_kinase', 'b0118', 'b3916', 'wild_type_reference',
            'b1854', 'aconitase', 'b1723', 'b1276',
            'phosphofructokinase', 'b1676',
        ]
        report = self._complete(order)
        self.assertTrue(report['unique_synthetic_lethality_supported'])
        self.assertEqual(report['missing_conditions'], [])

    def test_nine_runs_are_incomplete(self):
        order = ['wild_type_reference', *simulation.MISSION29_SINGLE_GENES, *simulation.MISSION29_PAIR_ORDER[:-1]]
        report = self._complete(order)
        self.assertEqual(report['recorded_run_count'], 9)
        self.assertFalse(report['evidence_ready'])
        self.assertEqual(report['missing_conditions'], ['pair:pyruvate_kinase'])

    def test_repeated_run_replaces_without_duplication(self):
        report = self._complete()
        repeated = self._record('b0118', existing=report)
        self.assertEqual(repeated['recorded_run_count'], 10)
        self.assertEqual(repeated['current_gene'], 'b0118')
        self.assertTrue(repeated['current_run_recorded'])

    def test_wrong_method_and_objective_are_rejected(self):
        self.assertFalse(self._record('wild_type_reference', method='FBA')['current_run_valid'])
        self.assertFalse(self._record('wild_type_reference', objective='EX_ac_e')['current_run_valid'])

    def test_only_defined_genotypes_are_accepted(self):
        genes = simulation._build_active_genes_data()
        genes['b3956'] = False
        self.assertFalse(self._record('wild_type_reference', genes=genes)['current_run_valid'])
        genes = self._genes('b0118')
        genes['b1723'] = False
        self.assertFalse(self._record('b0118', genes=genes)['current_run_valid'])

    def test_cross_pair_double_knockout_is_rejected(self):
        genes = simulation._build_active_genes_data()
        genes['b0118'] = False
        genes['b1723'] = False
        report = self._record('aconitase', genes=genes, disabled=[])
        self.assertFalse(report['current_run_valid'])

    def test_environment_must_be_default(self):
        report = self._record('b0118', reactions=self._reactions(extra_change=('EX_akg_e', 'lb')))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('default', ' '.join(report['current_issues']).lower())

    def test_environment_payload_is_order_independent(self):
        reactions = dict(reversed(list(self._reactions().items())))
        self.assertTrue(self._record('wild_type_reference', reactions=reactions)['current_run_valid'])

    def test_incomplete_environment_is_rejected(self):
        report = self._record('wild_type_reference', reactions=self._reactions(incomplete=True))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('incomplete', ' '.join(report['current_issues']).lower())

    def test_single_knockout_must_leave_matched_reaction_enabled(self):
        report = self._record('b0118', disabled=['ACONTa'])
        self.assertFalse(report['current_run_valid'])
        self.assertIn('single isoenzyme', ' '.join(report['current_issues']).lower())

    def test_double_knockout_must_disable_complete_matched_gpr(self):
        report = self._record('aconitase', disabled=['ACONTa'])
        self.assertFalse(report['current_run_valid'])
        self.assertIn('acontb', ' '.join(report['current_issues']).lower())

    def test_glucose_and_oxygen_must_be_numeric(self):
        missing_glucose = self._record('b0118', medium=self._medium(self.GROWTH['b0118'], missing=simulation.MISSION27_GLUCOSE_REACTION))
        missing_oxygen = self._record('b0118', medium=self._medium(self.GROWTH['b0118'], missing=simulation.MISSION27_OXYGEN_REACTION))
        self.assertFalse(missing_glucose['current_run_valid'])
        self.assertFalse(missing_oxygen['current_run_valid'])

    def test_glucose_secretion_is_rejected(self):
        report = self._record('b0118', medium=self._medium(self.GROWTH['b0118'], glucose=1.0))
        self.assertFalse(report['current_run_valid'])

    def test_oxygen_must_remain_positive(self):
        report = self._record('b0118', medium=self._medium(self.GROWTH['b0118'], oxygen=0.0))
        self.assertFalse(report['current_run_valid'])

    def test_default_glucose_capacity_cannot_be_exceeded(self):
        report = self._record('b0118', medium=self._medium(self.GROWTH['b0118'], glucose=-11.0))
        self.assertFalse(report['current_run_valid'])

    def test_growth_zero_is_valid_when_numeric(self):
        report = self._record('aconitase')
        self.assertTrue(report['current_run_valid'])
        self.assertEqual(report['pair_trials']['aconitase']['growth'], 0.0)

    def test_infeasible_is_not_converted_to_zero(self):
        report = self._record('aconitase', objective_result='INFEASIBLE')
        self.assertFalse(report['current_run_valid'])
        self.assertIn('infeasible', ' '.join(report['current_issues']).lower())

    def test_missing_growth_is_rejected(self):
        report = self._record('aconitase', objective_result=None, objective_error='Missing visible result.')
        self.assertFalse(report['current_run_valid'])

    def test_biomass_must_match_visible_growth(self):
        growth = self.GROWTH['b0118']
        report = self._record('b0118', production=self._production(growth, biomass=growth - 0.1))
        self.assertFalse(report['current_run_valid'])

    def test_primary_diagnostic_must_match_biomass(self):
        growth = self.GROWTH['b0118']
        report = self._record('b0118', production=self._production(growth, diagnostics={'primary_objective_flux': growth - 0.1}))
        self.assertFalse(report['current_run_valid'])

    def test_pfba_diagnostics_are_required(self):
        growth = self.GROWTH['b0118']
        for updates in (
            {'method': 'FBA'},
            {'objective_reaction': 'EX_ac_e'},
            {'method_score_name': None},
            {'method_score': None},
            {'total_absolute_flux': None},
            {'active_reaction_count': None},
        ):
            with self.subTest(updates=updates):
                report = self._record('b0118', production=self._production(growth, diagnostics=updates))
                self.assertFalse(report['current_run_valid'])

    def test_pfba_score_must_match_total_absolute_flux(self):
        growth = self.GROWTH['b0118']
        report = self._record('b0118', production=self._production(growth, diagnostics={'method_score': 1.0}))
        self.assertFalse(report['current_run_valid'])

    def test_single_retention_values_are_one(self):
        report = self._complete()
        for gene_id in simulation.MISSION29_SINGLE_GENES:
            self.assertAlmostEqual(report['single_growth_retention'][gene_id], 1.0, delta=1e-6)

    def test_pair_retention_values_are_correct(self):
        report = self._complete()
        self.assertAlmostEqual(report['pair_growth_retention']['aconitase'], 0.0, delta=1e-6)
        self.assertAlmostEqual(report['pair_growth_retention']['phosphofructokinase'], 0.80561, delta=1e-4)
        self.assertAlmostEqual(report['pair_growth_retention']['pyruvate_kinase'], 0.98971, delta=1e-4)

    def test_controls_must_remain_viable_for_final_relationship(self):
        report = self._complete()
        report['pair_trials']['phosphofructokinase']['growth'] = 0.0
        # Rebuild the last run to force recalculation from this altered state.
        rebuilt = self._record('b1676', existing=report)
        self.assertFalse(rebuilt['unique_synthetic_lethality_supported'])

    def test_invalid_attempt_preserves_complete_evidence(self):
        report = self._complete()
        invalid = self._record('b0118', existing=report, method='FBA')
        self.assertEqual(invalid['recorded_run_count'], 10)
        self.assertTrue(invalid['evidence_ready'])
        self.assertFalse(invalid['current_run_recorded'])
        self.assertTrue(invalid['unique_synthetic_lethality_supported'])

    def test_answer_aliases(self):
        report = self._complete()
        accepted = (
            'b0118 + b1276',
            'acnB and acnA',
            'aconitase isoenzyme pair',
            'ACONTa and ACONTb',
        )
        for answer in accepted:
            with self.subTest(answer=answer):
                self.assertTrue(simulation.mission29_answer_matches(answer, report))

    def test_wrong_or_incomplete_answers_are_rejected(self):
        report = self._complete()
        for answer in ('b0118', 'b1723 + b3916', 'pfkA pfkB', 'PYK', ''):
            with self.subTest(answer=answer):
                self.assertFalse(simulation.mission29_answer_matches(answer, report))

    def test_answer_requires_current_complete_report(self):
        report = self._complete()
        report['check_version'] = 1
        self.assertFalse(simulation.mission29_answer_matches('b0118 b1276', report))

    def test_report_does_not_state_the_answer(self):
        report = self._complete()
        text = simulation.build_mission29_redundancy_report_text(report)
        self.assertIn('Evidence complete', text)
        self.assertIn('Question:', text)
        self.assertNotIn('The answer is', text)
        self.assertNotIn('Submit b0118', text)

    def test_initial_report_has_no_redundant_title_block(self):
        text = simulation.build_mission29_redundancy_report_text(None)
        self.assertTrue(text.startswith('No redundancy evidence'))
        self.assertNotIn('Mission 29 Isoenzyme Redundancy Screen\nMission 29', text)

    def test_report_is_json_serialisable(self):
        json.dumps(self._complete())

    def test_visible_check_does_not_run_hidden_simulation(self):
        source = inspect.getsource(simulation.run_mission29_redundancy_check)
        self.assertNotIn('run_simul(', source)
        self.assertNotIn('simulate(', source)
        self.assertNotIn('_http_post_json', source)

    def test_remote_wrapper_reuses_same_visible_result(self):
        source = inspect.getsource(simulation.run_mission29_redundancy_check_remote)
        self.assertIn('run_mission29_redundancy_check(simulation_results)', source)
        self.assertNotIn('/simulate', source)

    def test_save_helpers_exist(self):
        import save_load
        self.assertTrue(callable(save_load.save_mission29_redundancy_check))
        self.assertTrue(callable(save_load.load_mission29_redundancy_check))
        self.assertTrue(callable(save_load.clear_mission29_redundancy_check))

    def test_dr_li_wiring_and_map_object(self):
        level = (PROJECT_ROOT / 'code' / 'level.py').read_text()
        player = (PROJECT_ROOT / 'code' / 'player.py').read_text()
        mission = (PROJECT_ROOT / 'code' / 'mission29.py').read_text()
        tiled = (PROJECT_ROOT / 'data' / 'map_lb.tmx').read_text()
        self.assertIn('from mission29 import Mission29', level)
        self.assertIn("obj.name == 'Mission29'", level)
        self.assertIn('talk_29 = self.toggle_talk_29', level)
        self.assertIn("name == 'Mission29'", player)
        self.assertIn("graphics/dialogues/li.jpg", mission)
        self.assertIn('Dr. Li', mission)
        self.assertIn('name="Mission29"', tiled)

    def test_gene_highlighting_and_window_capture(self):
        source = (PROJECT_ROOT / 'code' / 'window.py').read_text()
        self.assertIn("('29', list(MISSION29_SINGLE_GENES))", source)
        self.assertIn('run_mission29_redundancy_check', source)
        self.assertIn("label_id='mission29_redundancy_check'", source)

    def test_window_defines_mission29_report_adapter(self):
        # ``from simulation import *`` deliberately excludes underscore-prefixed
        # names. Window therefore needs its own adapter, as already done for
        # Missions 27 and 28, rather than calling simulation._build_* directly.
        source = (PROJECT_ROOT / 'code' / 'window.py').read_text()
        self.assertIn('def _build_mission29_text(report_data):', source)
        self.assertIn(
            'return build_mission29_redundancy_report_text(report_data)',
            source,
        )

    def test_documentation_exists(self):
        text = (PROJECT_ROOT / 'data' / 'missions' / 'mission29.md').read_text()
        self.assertIn('Isoenzyme Redundancy Screen', text)
        self.assertIn('Dr. Li', text)
        self.assertIn('b0118', text)
        self.assertIn('b1276', text)

    def test_gpr_gene_products_and_reactions_exist_in_sbml(self):
        model_path = PROJECT_ROOT / 'data' / 'models' / 'e_coli_core.xml.gz'
        ns = {
            'sbml': 'http://www.sbml.org/sbml/level3/version1/core',
            'fbc': 'http://www.sbml.org/sbml/level3/version1/fbc/version2',
        }
        with gzip.open(model_path, 'rb') as handle:
            root = ET.parse(handle).getroot()
        model = root.find('sbml:model', ns)
        reaction_ids = {item.attrib['id'] for item in model.find('sbml:listOfReactions', ns)}
        gene_ids = {
            item.attrib[f"{{{ns['fbc']}}}label"]
            for item in model.findall('.//fbc:geneProduct', ns)
        }
        for gene_id in simulation.MISSION29_SINGLE_GENES:
            self.assertIn(gene_id, gene_ids)
        for reaction_list in simulation.MISSION29_PAIR_REACTIONS.values():
            for reaction_id in reaction_list:
                self.assertIn('R_' + reaction_id, reaction_ids)

    def test_independent_fba_growth_values(self):
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

        objective = np.zeros(len(reactions))
        biomass = reaction_index['R_BIOMASS_Ecoli_core_w_GAM']
        objective[biomass] = -1.0
        conditions = {
            'wild_type_reference': [],
            **{gene_id: [] for gene_id in simulation.MISSION29_SINGLE_GENES},
            **{
                pair_id: ['R_' + reaction for reaction in simulation.MISSION29_PAIR_REACTIONS[pair_id]]
                for pair_id in simulation.MISSION29_PAIR_ORDER
            },
        }
        for key, disabled_reactions in conditions.items():
            current = list(bounds)
            for reaction_id in disabled_reactions:
                current[reaction_index[reaction_id]] = (0.0, 0.0)
            result = linprog(
                objective,
                A_eq=matrix,
                b_eq=np.zeros(len(species)),
                bounds=current,
                method='highs',
            )
            self.assertTrue(result.success)
            growth = result.x[biomass]
            self.assertAlmostEqual(growth, self.GROWTH[key], delta=1e-6)

            # Independent pFBA secondary optimisation: fix the primary optimum
            # and minimise the sum of absolute reaction fluxes.
            reaction_count = len(reactions)
            secondary_objective = np.concatenate([
                np.zeros(reaction_count),
                np.ones(reaction_count),
            ])
            secondary_matrix = np.hstack([
                matrix,
                np.zeros((len(species), reaction_count)),
            ])
            biomass_row = np.zeros(2 * reaction_count)
            biomass_row[biomass] = 1.0
            secondary_matrix = np.vstack([secondary_matrix, biomass_row])
            secondary_rhs = np.append(np.zeros(len(species)), growth)
            abs_constraints = []
            abs_rhs = []
            for index in range(reaction_count):
                positive = np.zeros(2 * reaction_count)
                positive[index] = 1.0
                positive[reaction_count + index] = -1.0
                abs_constraints.append(positive)
                abs_rhs.append(0.0)

                negative = np.zeros(2 * reaction_count)
                negative[index] = -1.0
                negative[reaction_count + index] = -1.0
                abs_constraints.append(negative)
                abs_rhs.append(0.0)

            secondary = linprog(
                secondary_objective,
                A_ub=np.array(abs_constraints),
                b_ub=np.array(abs_rhs),
                A_eq=secondary_matrix,
                b_eq=secondary_rhs,
                bounds=current + [(0.0, None)] * reaction_count,
                method='highs',
            )
            self.assertTrue(secondary.success)
            fluxes = secondary.x[:reaction_count]
            expected_total = {
                'wild_type_reference': 518.422085518,
                'b0118': 518.422085518,
                'b1276': 518.422085518,
                'aconitase': 56.865555556,
                'b1723': 518.422085518,
                'b3916': 518.422085518,
                'phosphofructokinase': 680.110498599,
                'b1676': 518.422085518,
                'b1854': 518.422085518,
                'pyruvate_kinase': 526.311439072,
            }[key]
            expected_active = {
                'aconitase': 27,
                'phosphofructokinase': 44,
            }.get(key, 48)
            self.assertAlmostEqual(sum(abs(value) for value in fluxes), expected_total, delta=1e-6)
            self.assertEqual(sum(abs(value) > 1e-9 for value in fluxes), expected_active)

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
        conditions = [('wild_type_reference', [])]
        conditions.extend((gene_id, [gene_id]) for gene_id in simulation.MISSION29_SINGLE_GENES)
        conditions.extend((pair_id, list(simulation.MISSION29_PAIRS[pair_id])) for pair_id in simulation.MISSION29_PAIR_ORDER)
        for key, knockouts in conditions:
            request = SimulateRequest(
                method=simulation.MISSION29_METHOD,
                objective=simulation.MISSION29_GROWTH_OBJECTIVE,
                gene_knockouts=knockouts,
                environmental_conditions=default_env,
            )
            result = backend_simulate(request)
            self.assertEqual(result.status, 'ok')
            self.assertAlmostEqual(result.primary_objective_flux, self.GROWTH[key], delta=1e-6)
            self.assertEqual(result.method_score_name, simulation.MISSION29_EXPECTED_SCORE_NAME)


if __name__ == '__main__':
    unittest.main()
