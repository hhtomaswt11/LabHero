from __future__ import annotations

import gzip
import json
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, eye, hstack, lil_matrix, vstack

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

try:
    import pygame  # noqa: F401
except ModuleNotFoundError:
    pygame = types.ModuleType('pygame')
    pygame.Vector2 = lambda *args: tuple(args)
    sys.modules['pygame'] = pygame

try:
    import pygame_menu  # noqa: F401
except ModuleNotFoundError:
    class _Theme:
        def copy(self):
            return _Theme()
    pm = types.ModuleType('pygame_menu')
    pm.themes = types.SimpleNamespace(THEME_GREEN=_Theme())
    pm.font = types.SimpleNamespace(FONT_MUNRO='munro')
    pm.widgets = types.SimpleNamespace(MENUBAR_STYLE_SIMPLE='simple')
    sys.modules['pygame_menu'] = pm

_original_platform = sys.platform
try:
    import mewpy  # noqa: F401
    import cobra  # noqa: F401
except ModuleNotFoundError:
    sys.platform = 'emscripten'

import simulation  # noqa: E402
import save_load  # noqa: E402
sys.platform = _original_platform


class Mission40RegressionTests(unittest.TestCase):
    CORE_NS = 'http://www.sbml.org/sbml/level3/version1/core'
    FBC_NS = 'http://www.sbml.org/sbml/level3/version1/fbc/version2'

    NO_RESCUE = {
        -0.5: (0.043235686, 0.0, 0.0, 0.0, 0.5, 1.415029),
        -1.0: (0.072576514, 0.0, 0.494320, 0.0, 1.0, 2.0),
        -2.0: (0.091724688, 0.0, 2.654896, 0.0, 2.0, 2.0),
        -10.0: (0.095425414, 0.0, 3.126665, 0.010554, 2.225298, 2.0),
    }
    RESCUE = {
        -0.5: (0.057990699, 0.0, 0.0, 0.0, 0.5, 2.0, 2.146529),
        -1.0: (0.077320932, 2.505968, 0.0, 0.0, 1.0, 2.0, 2.541041),
        -2.0: (0.113209955, 9.948648, 0.0, 0.0, 2.0, 2.0, 10.0),
        -10.0: (0.222940345, 9.910492, 12.044543, 0.024657, 7.517075, 2.0, 10.0),
    }

    @staticmethod
    def make_reactions(rescue=False, no_op_o2_upper=False):
        table, _ = simulation.build_legacy_tables('yeast_iMM904')
        reactions = {}
        for index in range(len(table.index)):
            reactions[f'reaction_{index}_lb'] = bool(float(table.lb.iloc[index]) != 0.0)
            reactions[f'reaction_{index}_ub'] = bool(float(table.ub.iloc[index]) != 0.0)
        if rescue:
            idx = list(table.index).index('EX_acald_e')
            reactions[f'reaction_{idx}_lb'] = True
        if no_op_o2_upper:
            idx = list(table.index).index('EX_o2_e')
            reactions[f'reaction_{idx}_ub'] = True
        return reactions

    @staticmethod
    def make_genes():
        return {gene_id: False for gene_id in simulation.MISSION40_FIXED_GENOTYPE}

    def make_curve(self, rescue=False, *, bad_gpr=False, bad_status=False, no_op_o2_upper=False):
        data = self.RESCUE if rescue else self.NO_RESCUE
        rows = []
        for i, bound in enumerate(simulation.MISSION40_SWEEP_VALUES):
            values = data[float(bound)]
            if rescue:
                growth, ethanol, pyruvate, succinate, glucose, oxygen, acald_uptake = values
            else:
                growth, ethanol, pyruvate, succinate, glucose, oxygen = values
                acald_uptake = 0.0
            disabled = list(simulation.MISSION40_EXPECTED_DISABLED)
            if bad_gpr and i == 0:
                disabled = disabled[:-1]
            rows.append({
                'model_id': 'yeast_iMM904',
                'bound_value': float(bound),
                'status': 'infeasible' if bad_status and i == 0 else 'ok',
                'objective_result': growth,
                'growth_value': growth,
                'tested_reaction_raw_flux': -glucose,
                'tested_reaction_uptake': glucose,
                'oxygen_raw_flux': -oxygen,
                'oxygen_uptake': oxygen,
                'tracked_flux_values': {
                    'EX_etoh_e': ethanol,
                    'EX_succ_e': succinate,
                    'EX_pyr_e': pyruvate,
                },
                'exchange_raw_fluxes': {
                    'EX_acald_e': -acald_uptake,
                    'EX_glc__D_e': -glucose,
                    'EX_o2_e': -oxygen,
                },
                'exchange_uptake_fluxes': {
                    'EX_acald_e': acald_uptake,
                    'EX_glc__D_e': glucose,
                    'EX_o2_e': oxygen,
                },
                'exchange_secretion_fluxes': {},
                'method_diagnostics': {
                    'model_id': 'yeast_iMM904',
                    'method': 'pFBA',
                    'objective_reaction': 'BIOMASS_SC5_notrace',
                    'primary_objective_flux': growth,
                    'total_absolute_flux': 100.0 + i,
                    'active_reaction_count': 250,
                    'gpr_disabled_reactions': disabled,
                },
            })
        return {
            'sweep_id': 'bound_sweep',
            'check_version': 3,
            'model_id': 'yeast_iMM904',
            'method': 'pFBA',
            'objective': 'BIOMASS_SC5_notrace',
            'knocked_out_genes': list(simulation.MISSION40_FIXED_GENOTYPE),
            'environment_changed': bool(rescue),
            'base_genes': self.make_genes(),
            'base_reactions': self.make_reactions(rescue=rescue, no_op_o2_upper=no_op_o2_upper),
            'variable': 'EX_glc__D_e:lower',
            'preset': 'yeast_glucose_fermentation_threshold',
            'expected_preset': 'yeast_glucose_fermentation_threshold',
            'preset_matches_variable': True,
            'reaction_id': 'EX_glc__D_e',
            'reaction_name': 'D-Glucose exchange',
            'bound': 'lower',
            'bound_label': 'lower bound',
            'values': list(simulation.MISSION40_SWEEP_VALUES),
            'tracked_fluxes': list(simulation.MISSION40_REQUIRED_PRODUCTION_FLUXES),
            'selected_production_fluxes': list(simulation.MISSION40_REQUIRED_PRODUCTION_FLUXES),
            'rows': rows,
        }

    def make_complete_report(self):
        report = simulation._mission40_empty_report()
        report['curves']['no_rescue'] = self.make_curve(False)
        report['curves']['acetaldehyde_rescue'] = self.make_curve(True)
        return simulation._mission40_refresh_derived(report)

    def test_unlock_requires_mission39(self):
        self.assertFalse(simulation.is_mission40_unlocked(['38']))
        self.assertTrue(simulation.is_mission40_unlocked(['39']))

    def test_protocol_is_final_matched_two_curve_screen(self):
        self.assertEqual(simulation.MISSION40_FIXED_GENOTYPE, simulation.MISSION39_FIXED_GENOTYPE)
        self.assertEqual(simulation.MISSION40_SWEEP_VALUES, [-0.5, -1.0, -2.0, -10.0])
        self.assertEqual(simulation.MISSION40_CURVE_ORDER, ('no_rescue', 'acetaldehyde_rescue'))
        self.assertEqual(set(simulation.MISSION40_REQUIRED_PRODUCTION_FLUXES), {'EX_etoh_e', 'EX_succ_e', 'EX_pyr_e'})

    def test_complete_visible_evidence_derives_context_dependent_qualifying_bounds(self):
        report = self.make_complete_report()
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['conditional_rescue_supported'])
        self.assertFalse(report['robust_across_all_tested_bounds'])
        self.assertEqual(report['qualifying_bounds'], [-2.0, -10.0])
        self.assertTrue(report['ready_to_deliver'])

    def test_pairwise_metrics_are_derived_from_visible_rows(self):
        report = self.make_complete_report()
        row = report['paired_rows']['-2.0']
        self.assertAlmostEqual(row['matched_growth_fold'], 0.113209955 / 0.091724688, places=5)
        self.assertAlmostEqual(row['acetaldehyde_uptake'], 10.0, places=6)
        self.assertAlmostEqual(row['rescue_ethanol'], 9.948648, places=6)
        self.assertTrue(row['qualifies'])
        self.assertFalse(report['paired_rows']['-1.0']['qualifies'])

    def test_answer_is_rederived_from_report_and_order_insensitive(self):
        report = self.make_complete_report()
        self.assertTrue(simulation.mission40_answer_matches('-2 and -10', report))
        self.assertTrue(simulation.mission40_answer_matches('LB -10, -2', report))
        self.assertFalse(simulation.mission40_answer_matches('-10', report))
        report['qualifying_bounds'] = [-0.5]
        self.assertTrue(simulation.mission40_answer_matches('-2 -10', report))  # refreshed from curves, not stale field

    def test_incomplete_evidence_cannot_be_delivered(self):
        report = simulation._mission40_empty_report()
        report['curves']['no_rescue'] = self.make_curve(False)
        simulation._mission40_refresh_derived(report)
        self.assertFalse(report['evidence_ready'])
        self.assertFalse(simulation.mission40_answer_matches('-2 -10', report))

    def test_missing_numeric_pair_evidence_is_not_treated_as_zero(self):
        report = simulation._mission40_empty_report()
        no_curve = self.make_curve(False)
        rescue_curve = self.make_curve(True)
        rescue_curve['rows'][2]['exchange_uptake_fluxes'].pop('EX_acald_e')
        report['curves']['no_rescue'] = no_curve
        report['curves']['acetaldehyde_rescue'] = rescue_curve
        simulation._mission40_refresh_derived(report)
        self.assertFalse(report['evidence_ready'])
        self.assertNotIn('-2.0', report['paired_rows'])

    def test_old_report_version_is_rejected(self):
        old = {'mission_id': '40', 'check_version': 0, 'curves': {'junk': {}}}
        prepared = simulation._mission40_prepare_report(old)
        self.assertEqual(prepared['check_version'], simulation.MISSION40_CHECK_VERSION)
        self.assertEqual(prepared['curves'], {})

    def test_report_does_not_print_final_answer_or_qualifying_marker(self):
        text = simulation.build_mission40_final_certification_report_text(self.make_complete_report())
        self.assertIn('Evidence complete.', text)
        self.assertNotIn('qualifying bounds: -2', text.lower())
        self.assertNotIn('answer:', text.lower())
        self.assertNotIn('| yes', text.lower())

    def test_landing_report_title_can_be_suppressed_contextually(self):
        report = simulation._mission40_empty_report()
        self.assertNotIn('Mission 40 Final', simulation.build_mission40_final_certification_report_text(report, include_title=False))
        self.assertIn('Mission 40 Final', simulation.build_mission40_final_certification_report_text(report, include_title=True))

    def test_environment_classifier_accepts_default_and_acetaldehyde_only(self):
        self.assertEqual(simulation._mission40_environment_curve_type(self.make_reactions(False))[0], 'no_rescue')
        self.assertEqual(simulation._mission40_environment_curve_type(self.make_reactions(True))[0], 'acetaldehyde_rescue')
        table, _ = simulation.build_legacy_tables('yeast_iMM904')
        reactions = self.make_reactions(False)
        idx = list(table.index).index('EX_etoh_e')
        reactions[f'reaction_{idx}_lb'] = True
        self.assertIsNone(simulation._mission40_environment_curve_type(reactions)[0])

    def test_noop_default_upper_restatement_remains_valid(self):
        curve, curve_type, issues = simulation._mission40_validate_curve(self.make_curve(True, no_op_o2_upper=True))
        self.assertIsNotNone(curve, issues)
        self.assertEqual(curve_type, 'acetaldehyde_rescue')

    def test_curves_can_be_recorded_in_any_order_and_repeated_curve_replaces(self):
        with patch.object(simulation, 'load_mission40_final_certification', return_value=simulation._mission40_empty_report()), \
             patch.object(simulation, 'save_mission40_final_certification'):
            first = simulation.run_mission40_curve_check(self.make_curve(True))
        self.assertEqual(first['recorded_curve_count'], 1)
        self.assertEqual(first['missing_curves'], ['no_rescue'])
        with patch.object(simulation, 'load_mission40_final_certification', return_value=first), \
             patch.object(simulation, 'save_mission40_final_certification'):
            second = simulation.run_mission40_curve_check(self.make_curve(False))
        self.assertEqual(second['recorded_curve_count'], 2)
        with patch.object(simulation, 'load_mission40_final_certification', return_value=second), \
             patch.object(simulation, 'save_mission40_final_certification'):
            repeated = simulation.run_mission40_curve_check(self.make_curve(False))
        self.assertEqual(repeated['recorded_curve_count'], 2)

    def test_invalid_curve_preserves_previous_valid_evidence(self):
        report = self.make_complete_report()
        with patch.object(simulation, 'load_mission40_final_certification', return_value=report), \
             patch.object(simulation, 'save_mission40_final_certification'):
            candidate = simulation.run_mission40_curve_check(self.make_curve(True, bad_status=True))
        self.assertFalse(candidate['current_attempt_recorded'])
        self.assertEqual(candidate['recorded_curve_count'], 2)
        self.assertTrue(candidate['evidence_ready'])

    def test_wrong_gpr_rejects_curve(self):
        curve, _curve_type, issues = simulation._mission40_validate_curve(self.make_curve(False, bad_gpr=True))
        self.assertIsNone(curve)
        self.assertTrue(any('GPR-disabled' in issue for issue in issues))

    def test_preflight_rejects_wrong_genotype_without_solver_execution(self):
        menu = {'execute_sweep': True, 'sweep_variable': 'EX_glc__D_e:lower', 'sweep_values': 'yeast_glucose_fermentation_threshold'}
        wrong_genes = {'YLR044C': False}
        reactions = self.make_reactions(False)
        with patch.object(simulation, '_read_simulation_model_id', return_value='yeast_iMM904'), \
             patch.object(simulation, '_read_simulation_file', return_value=('pFBA', 'BIOMASS_SC5_notrace', wrong_genes, reactions)), \
             patch.object(simulation, '_read_selected_production_fluxes', return_value=list(simulation.MISSION40_REQUIRED_PRODUCTION_FLUXES)), \
             patch.object(simulation, 'load_mission40_final_certification', return_value=self.make_complete_report()), \
             patch.object(simulation, 'save_mission40_final_certification'):
            rejected = simulation.run_mission40_rejected_sweep_attempt(menu, 'pFBA', 'BIOMASS_SC5_notrace', wrong_genes)
        self.assertFalse(rejected['latest_attempt']['solver_executed'])
        self.assertEqual(rejected['recorded_curve_count'], 2)
        self.assertTrue(rejected['evidence_ready'])

    def test_state_is_json_serialisable(self):
        json.dumps(self.make_complete_report())

    def test_save_load_contract_exists_for_desktop_and_web(self):
        source = (ROOT / 'code' / 'save_load.py').read_text()
        self.assertIn('save_mission40_final_certification', source)
        self.assertIn("_web_store_set('mission40_final_certification'", source)
        self.assertIn("_web_store_get('mission40_final_certification'", source)
        self.assertIn('mission40_final_certification.txt', source)

    def test_mortis_tiled_object_and_dialogue_asset_are_reused(self):
        tmx = (ROOT / 'data' / 'map_lb.tmx').read_text()
        self.assertIn('name="Mortis"', tmx)
        self.assertTrue((ROOT / 'graphics' / 'dialogues' / 'mortis.jpg').exists())

    def test_mortis_interaction_is_wired_to_mission40(self):
        level = (ROOT / 'code' / 'level.py').read_text()
        player = (ROOT / 'code' / 'player.py').read_text()
        self.assertIn('from mission40 import Mission40', level)
        self.assertIn("if obj.name == 'Mortis':", level)
        self.assertIn('self.talk_40 = Mission40', level)
        self.assertIn("name == 'Mortis'", player)
        self.assertIn('self.talk_40()', player)

    def test_window_executes_only_prechecked_mission40_sweeps_and_reports_them(self):
        source = (ROOT / 'code' / 'window.py').read_text()
        self.assertIn('mission40_should_run_bound_sweep', source)
        self.assertIn('run_mission40_rejected_sweep_attempt', source)
        self.assertIn('or mission40_sweep_requested', source)
        self.assertIn('run_mission40_curve_check(bound_sweep_data)', source)
        self.assertIn('build_mission40_final_certification_report_text', source)

    def test_answer_field_submits_on_enter_and_button(self):
        source = (ROOT / 'code' / 'mission40.py').read_text()
        self.assertIn('onreturn=self.deliver_results', source)
        self.assertIn("'Deliver Final Interpretation'", source)
        self.assertIn('self.deliver_results(answer_input.get_value())', source)

    def test_final_dialogue_closes_the_game_arc_and_no_mission41_exists(self):
        source = (ROOT / 'code' / 'mission40.py').read_text()
        self.assertIn('LabHero metabolic-model training is complete.', source)
        self.assertIn('environment, GPR logic, background and pathway bypass', source)
        self.assertFalse((ROOT / 'code' / 'mission41.py').exists())
        self.assertFalse((ROOT / 'data' / 'missions' / 'mission41.md').exists())

    def test_validator_source_contains_no_hidden_solver_call(self):
        source = (ROOT / 'code' / 'simulation.py').read_text()
        block = source[source.index('def _mission40_validate_curve('):source.index('def _mission40_sweep_precheck(')]
        self.assertNotIn('.simulate(', block)
        self.assertNotIn('linprog(', block)
        self.assertNotIn('run_simul(', block)
        self.assertNotIn('/simulate', block)

    def test_briefing_requires_bound_sweep_and_matched_environments(self):
        source = (ROOT / 'code' / 'mission40.py').read_text()
        self.assertIn('Bound Sweep: ON for both curves', source)
        self.assertIn('No-rescue curve', source)
        self.assertIn('Rescue curve', source)
        self.assertIn('EX_acald_e', source)

    def _independent_pfba(self, glucose_lb, rescue=False):
        with gzip.open(ROOT / 'data' / 'models' / 'iMM904.xml.gz', 'rb') as handle:
            root = ET.parse(handle).getroot()
        ns = {'c': self.CORE_NS, 'f': self.FBC_NS}
        model = root.find('c:model', ns)
        params = {p.attrib['id']: float(p.attrib['value']) for p in model.find('c:listOfParameters', ns)}
        species = [s.attrib['id'] for s in model.find('c:listOfSpecies', ns)]
        species_index = {sid: i for i, sid in enumerate(species)}
        reactions = list(model.find('c:listOfReactions', ns))
        reaction_ids = [r.attrib['id'].removeprefix('R_') for r in reactions]
        reaction_index = {rid: i for i, rid in enumerate(reaction_ids)}
        matrix = lil_matrix((len(species), len(reactions)), dtype=float)
        lower = np.zeros(len(reactions)); upper = np.zeros(len(reactions))
        for j, reaction in enumerate(reactions):
            lower[j] = params[reaction.attrib[f'{{{self.FBC_NS}}}lowerFluxBound']]
            upper[j] = params[reaction.attrib[f'{{{self.FBC_NS}}}upperFluxBound']]
            reactants = reaction.find('c:listOfReactants', ns)
            if reactants is not None:
                for ref in reactants:
                    matrix[species_index[ref.attrib['species']], j] -= float(ref.attrib.get('stoichiometry', '1'))
            products = reaction.find('c:listOfProducts', ns)
            if products is not None:
                for ref in products:
                    matrix[species_index[ref.attrib['species']], j] += float(ref.attrib.get('stoichiometry', '1'))
        for reaction_id in simulation.MISSION40_EXPECTED_DISABLED:
            lower[reaction_index[reaction_id]] = 0.0
            upper[reaction_index[reaction_id]] = 0.0
        lower[reaction_index['EX_glc__D_e']] = float(glucose_lb)
        if rescue:
            lower[reaction_index['EX_acald_e']] = -10.0
        matrix = csr_matrix(matrix)
        objective_index = reaction_index['BIOMASS_SC5_notrace']
        c = np.zeros(len(reactions)); c[objective_index] = -1.0
        primary = linprog(c, A_eq=matrix, b_eq=np.zeros(len(species)), bounds=list(zip(lower, upper)), method='highs')
        self.assertTrue(primary.success, primary.message)
        optimum = primary.x[objective_index]
        n = len(reactions)
        aeq = hstack([matrix, csr_matrix((len(species), n))], format='csr')
        row = lil_matrix((1, 2*n)); row[0, objective_index] = 1.0
        aeq = vstack([aeq, row.tocsr()], format='csr')
        beq = np.r_[np.zeros(len(species)), optimum]
        ident = eye(n, format='csr')
        aub = vstack([hstack([ident, -ident]), hstack([-ident, -ident])], format='csr')
        secondary = linprog(
            np.r_[np.zeros(n), np.ones(n)],
            A_ub=aub, b_ub=np.zeros(2*n), A_eq=aeq, b_eq=beq,
            bounds=list(zip(lower, upper)) + [(0, None)] * n,
            method='highs',
        )
        self.assertTrue(secondary.success, secondary.message)
        flux = secondary.x[:n]
        return {rid: float(flux[index]) for rid, index in reaction_index.items()}

    def test_independent_pfba_reproduces_conditional_final_rescue_pattern(self):
        qualifying = []
        for bound in simulation.MISSION40_SWEEP_VALUES:
            no = self._independent_pfba(bound, False)
            rescue = self._independent_pfba(bound, True)
            fold = rescue['BIOMASS_SC5_notrace'] / no['BIOMASS_SC5_notrace']
            acald_uptake = max(-rescue['EX_acald_e'], 0.0)
            ethanol = max(rescue['EX_etoh_e'], 0.0)
            if (
                fold >= simulation.MISSION40_MIN_MATCHED_GROWTH_FOLD
                and acald_uptake >= simulation.MISSION40_MIN_ACETALDEHYDE_UPTAKE
                and ethanol >= simulation.MISSION40_MIN_RESCUE_ETHANOL
            ):
                qualifying.append(float(bound))
        self.assertEqual(qualifying, [-2.0, -10.0])


if __name__ == '__main__':
    unittest.main()
