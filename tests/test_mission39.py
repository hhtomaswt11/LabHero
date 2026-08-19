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
import model_registry  # noqa: E402
sys.platform = _original_platform


class Mission39RegressionTests(unittest.TestCase):
    CORE_NS = 'http://www.sbml.org/sbml/level3/version1/core'
    FBC_NS = 'http://www.sbml.org/sbml/level3/version1/fbc/version2'

    @staticmethod
    def make_reactions(condition_id='default'):
        table, _ = simulation.build_legacy_tables('yeast_iMM904')
        reactions = {}
        for index in range(len(table.index)):
            reactions[f'reaction_{index}_lb'] = bool(float(table.lb.iloc[index]) != 0.0)
            reactions[f'reaction_{index}_ub'] = bool(float(table.ub.iloc[index]) != 0.0)
        exchange = simulation.MISSION39_CONDITION_EXCHANGES[condition_id]
        if exchange:
            index = list(table.index).index(exchange)
            reactions[f'reaction_{index}_lb'] = True
        return reactions

    @staticmethod
    def make_genes():
        return {gene_id: False for gene_id in simulation.MISSION39_FIXED_GENOTYPE}

    @staticmethod
    def make_visible_payload(growth, ethanol, succinate, pyruvate, supplement_id=None, supplement_raw=0.0):
        production = {
            'selected_ids': ['EX_etoh_e', 'EX_succ_e', 'EX_pyr_e'],
            'items': [
                {'reaction_id': 'EX_etoh_e', 'production_flux': max(ethanol, 0.0), 'raw_flux': ethanol},
                {'reaction_id': 'EX_succ_e', 'production_flux': max(succinate, 0.0), 'raw_flux': succinate},
                {'reaction_id': 'EX_pyr_e', 'production_flux': max(pyruvate, 0.0), 'raw_flux': pyruvate},
            ],
            'biomass_raw': growth,
            'method_diagnostics': {
                'model_id': 'yeast_iMM904',
                'method': 'pFBA',
                'objective_reaction': 'BIOMASS_SC5_notrace',
                'primary_objective_flux': growth,
                'method_score': 100.0,
                'method_score_name': 'total_absolute_flux',
                'total_absolute_flux': 100.0,
                'active_reaction_count': 250,
                'gpr_disabled_reactions': list(simulation.MISSION39_EXPECTED_DISABLED),
            },
        }
        raw = {
            'EX_glc__D_e': -2.2,
            'EX_o2_e': -2.0,
            'EX_etoh_e': ethanol,
            'EX_pyr_e': pyruvate,
            'EX_succ_e': succinate,
            'EX_acald_e': 0.0,
        }
        if supplement_id:
            raw[supplement_id] = supplement_raw
        medium = {'items': []}
        for reaction_id, raw_flux in raw.items():
            medium['items'].append({
                'reaction_id': reaction_id,
                'raw_flux': raw_flux,
                'uptake_flux': max(-raw_flux, 0.0),
                'secretion_flux': max(raw_flux, 0.0),
            })
        return production, medium

    def make_complete_report(self):
        report = simulation._mission39_empty_report()
        rows = {
            'default': (0.0954254138, 0.0, 0.01055405, 3.12666470, None, 0.0),
            'pyruvate_open': (0.0954254138, 0.0, 0.01055405, 3.12666470, 'EX_pyr_e', 0.0),
            'ethanol_open': (0.0955458621, 0.0, 0.01056737, 3.16194718, 'EX_etoh_e', 0.03836071),
            'acetaldehyde_open': (0.2229403449, 9.91049168, 0.02465720, 12.04454342, 'EX_acald_e', 10.0),
        }
        for condition_id, (growth, ethanol, succinate, pyruvate, exchange, uptake) in rows.items():
            report['runs'][condition_id] = {
                'condition_id': condition_id,
                'environment_exchange': exchange,
                'knocked_out_genes': sorted(simulation.MISSION39_FIXED_GENOTYPE),
                'growth': growth,
                'glucose_uptake': 2.2 if condition_id != 'acetaldehyde_open' else 7.5,
                'oxygen_uptake': 2.0,
                'ethanol_secretion': ethanol,
                'succinate_secretion': succinate,
                'pyruvate_secretion': pyruvate,
                'supplement_uptake': uptake,
                'supplement_raw_flux': -uptake if uptake else 0.0,
                'acetaldehyde_uptake': 10.0 if condition_id == 'acetaldehyde_open' else 0.0,
                'primary_objective_flux': growth,
                'total_absolute_flux': 100.0,
                'active_reaction_count': 250,
                'disabled_reactions': list(simulation.MISSION39_EXPECTED_DISABLED),
                'tracked_fluxes': list(simulation.MISSION39_REQUIRED_PRODUCTION_FLUXES),
                'method': 'pFBA',
                'objective': 'BIOMASS_SC5_notrace',
                'model_id': 'yeast_iMM904',
            }
        return simulation._mission39_refresh_derived(report)

    def test_unlock_requires_mission38(self):
        self.assertFalse(simulation.is_mission39_unlocked(['37']))
        self.assertTrue(simulation.is_mission39_unlocked(['38']))

    def test_fixed_genotype_and_environment_screen_are_explicit(self):
        self.assertEqual(set(simulation.MISSION39_FIXED_GENOTYPE), {'YLR044C', 'YLR134W', 'YGR087C', 'YEL047C'})
        self.assertEqual(simulation.MISSION39_CONDITION_ORDER, ('default', 'pyruvate_open', 'ethanol_open', 'acetaldehyde_open'))
        self.assertEqual(simulation.MISSION39_CONDITION_EXCHANGES['acetaldehyde_open'], 'EX_acald_e')
        self.assertEqual(set(simulation.MISSION39_REQUIRED_PRODUCTION_FLUXES), {'EX_etoh_e', 'EX_succ_e', 'EX_pyr_e'})

    def test_yeast_exchange_report_exposes_acetaldehyde(self):
        context = model_registry.build_ui_context('yeast_iMM904')
        self.assertIn('EX_acald_e', context['exchange_report_ids'])

    def test_compact_environment_editor_accepts_acetaldehyde_opening(self):
        context = model_registry.build_ui_context('yeast_iMM904')
        payload, errors = model_registry.build_compact_environment_payload(
            context['exchanges'], lower_open_text='EX_acald_e'
        )
        self.assertEqual(errors, [])
        index = [row['id'] for row in context['exchanges']].index('EX_acald_e')
        self.assertTrue(payload[f'reaction_{index}_lb'])
        constraints = simulation._model_environment_constraints('yeast_iMM904', payload)
        self.assertEqual(float(constraints['EX_acald_e'][0]), -10.0)

    def test_environment_classifier_accepts_only_one_controlled_opening(self):
        for condition_id in simulation.MISSION39_CONDITION_ORDER:
            observed, issues = simulation._mission39_environment_condition(self.make_reactions(condition_id))
            self.assertEqual(observed, condition_id)
            self.assertEqual(issues, [])
        reactions = self.make_reactions('pyruvate_open')
        table, _ = simulation.build_legacy_tables('yeast_iMM904')
        index = list(table.index).index('EX_etoh_e')
        reactions[f'reaction_{index}_lb'] = True
        observed, issues = simulation._mission39_environment_condition(reactions)
        self.assertIsNone(observed)
        self.assertTrue(issues)

    def test_complete_visible_evidence_derives_unique_rescue(self):
        report = self.make_complete_report()
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['rescue_supported'])
        self.assertEqual(report['unique_rescue'], 'acetaldehyde_open')
        self.assertLess(report['growth_fold_vs_default']['ethanol_open'], 1.01)
        self.assertGreater(report['growth_fold_vs_default']['acetaldehyde_open'], 2.0)

    def test_answer_is_rederived_from_visible_runs(self):
        report = self.make_complete_report()
        report['unique_rescue'] = 'ethanol_open'
        self.assertTrue(simulation.mission39_answer_matches('acetaldehyde', report))
        self.assertTrue(simulation.mission39_answer_matches('EX_acald_e', report))
        self.assertFalse(simulation.mission39_answer_matches('ethanol', report))

    def test_old_report_version_is_rejected(self):
        report = simulation._mission39_prepare_report({'mission_id': '39', 'check_version': 0, 'runs': {'x': 1}})
        self.assertEqual(report['runs'], {})
        self.assertFalse(report['evidence_ready'])

    def test_report_never_prints_solution_line(self):
        text = simulation.build_mission39_bypass_rescue_report_text(self.make_complete_report())
        self.assertTrue(text.startswith('Mission 39 Pathway Bypass Rescue'))
        self.assertIn('Evidence complete.', text)
        self.assertIn('supplement uptake', text)
        self.assertNotIn('Answer:', text)
        self.assertNotIn('Correct supplement:', text)
        self.assertNotIn('Unique rescue:', text)

    def test_landing_report_title_can_be_suppressed_contextually(self):
        text = simulation.build_mission39_bypass_rescue_report_text(self.make_complete_report(), include_title=False)
        self.assertTrue(text.startswith('Controlled bypass screen:'))
        source = (ROOT / 'code' / 'mission39.py').read_text()
        self.assertIn('report_include_title = bool(', source)
        self.assertIn('include_title=report_include_title', source)

    def test_briefing_and_hint_keep_historical_green_theme_background(self):
        source = (ROOT / 'code' / 'mission39.py').read_text()
        briefing_start = source.index('briefing = pygame_menu.Menu')
        briefing_end = source.index("briefing.add.button('Back'", briefing_start)
        hint_start = source.index('hint3 = pygame_menu.Menu', briefing_end)
        hint_end = source.index("hint1.add.button('Back'", hint_start)
        self.assertNotIn("background_color='white'", source[briefing_start:briefing_end])
        self.assertNotIn("background_color='white'", source[hint_start:hint_end])

    def test_bound_sweep_on_rejects_run_without_erasing_evidence(self):
        existing = self.make_complete_report()
        before = json.loads(json.dumps(existing['runs']))
        production, medium = self.make_visible_payload(0.095425, 0.0, 0.010554, 3.126665)
        with patch.object(simulation, 'save_mission39_bypass_rescue'):
            report = simulation._build_mission39_data(
                'pFBA', 'BIOMASS_SC5_notrace', 0.095425,
                self.make_genes(), self.make_reactions('default'), model_id='yeast_iMM904',
                selected_fluxes=['EX_etoh_e', 'EX_succ_e', 'EX_pyr_e'],
                production_fluxes=production, medium_fluxes=medium,
                existing_report=existing, sweep_requested=True,
            )
        self.assertFalse(report['current_run_recorded'])
        self.assertEqual(report['runs'], before)
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(any('Turn Bound Sweep off' in issue for issue in report['current_issues']))

    def test_invalid_environment_preserves_previous_valid_evidence(self):
        existing = self.make_complete_report()
        before = json.loads(json.dumps(existing['runs']))
        reactions = self.make_reactions('pyruvate_open')
        table, _ = simulation.build_legacy_tables('yeast_iMM904')
        index = list(table.index).index('EX_etoh_e')
        reactions[f'reaction_{index}_lb'] = True
        production, medium = self.make_visible_payload(0.095425, 0.0, 0.010554, 3.126665)
        with patch.object(simulation, 'save_mission39_bypass_rescue'):
            report = simulation._build_mission39_data(
                'pFBA', 'BIOMASS_SC5_notrace', 0.095425,
                self.make_genes(), reactions, model_id='yeast_iMM904',
                selected_fluxes=['EX_etoh_e', 'EX_succ_e', 'EX_pyr_e'],
                production_fluxes=production, medium_fluxes=medium,
                existing_report=existing,
            )
        self.assertFalse(report['current_run_recorded'])
        self.assertEqual(report['runs'], before)
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(any('default medium or open exactly one' in issue for issue in report['current_issues']))

    def test_rescue_run_can_be_recorded_before_default_reference(self):
        production, medium = self.make_visible_payload(0.222940, 9.910492, 0.024657, 12.044543, 'EX_acald_e', -10.0)
        with patch.object(simulation, 'save_mission39_bypass_rescue'):
            report = simulation._build_mission39_data(
                'pFBA', 'BIOMASS_SC5_notrace', 0.222940,
                self.make_genes(), self.make_reactions('acetaldehyde_open'), model_id='yeast_iMM904',
                selected_fluxes=['EX_etoh_e', 'EX_succ_e', 'EX_pyr_e'],
                production_fluxes=production, medium_fluxes=medium,
                existing_report=simulation._mission39_empty_report(),
            )
        self.assertIn('acetaldehyde_open', report['runs'])
        self.assertFalse(report['evidence_ready'])
        self.assertIn('default', report['missing_conditions'])

    def test_wrong_genotype_and_wrong_gpr_are_rejected(self):
        genes = self.make_genes()
        genes['YEL047C'] = True
        production, medium = self.make_visible_payload(0.176148, 0.009, 6.386, 0.0)
        production['method_diagnostics']['gpr_disabled_reactions'] = ['3MOBDC', 'ACALDCD', 'PYRDC', 'PYRDC2']
        with patch.object(simulation, 'save_mission39_bypass_rescue'):
            report = simulation._build_mission39_data(
                'pFBA', 'BIOMASS_SC5_notrace', 0.176148,
                genes, self.make_reactions('default'), model_id='yeast_iMM904',
                selected_fluxes=['EX_etoh_e', 'EX_succ_e', 'EX_pyr_e'],
                production_fluxes=production, medium_fluxes=medium,
                existing_report=simulation._mission39_empty_report(),
            )
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(any('genotype fixed' in issue for issue in report['current_issues']))
        self.assertTrue(any('GPR-disabled reaction set' in issue for issue in report['current_issues']))

    def test_state_is_json_serialisable(self):
        json.dumps(self.make_complete_report())

    def test_save_load_contract_exists_for_desktop_and_web(self):
        self.assertTrue(hasattr(save_load, 'save_mission39_bypass_rescue'))
        self.assertTrue(hasattr(save_load, 'load_mission39_bypass_rescue'))
        self.assertTrue(hasattr(save_load, 'clear_mission39_bypass_rescue'))

    def test_morbus_tiled_object_and_dialogue_asset_are_reused(self):
        tmx = (ROOT / 'data' / 'map_lb.tmx').read_text()
        self.assertIn('name="Morbus"', tmx)
        self.assertTrue((ROOT / 'graphics' / 'dialogues' / 'morbus.jpg').exists())

    def test_morbus_interaction_is_wired_to_mission39(self):
        level = (ROOT / 'code' / 'level.py').read_text()
        player = (ROOT / 'code' / 'player.py').read_text()
        self.assertIn('from mission39 import Mission39', level)
        self.assertIn("if obj.name == 'Morbus':", level)
        self.assertIn('talk_39 = self.toggle_talk_39', level)
        self.assertIn("name == 'Morbus'", player)
        self.assertIn('self.talk_39()', player)

    def test_window_records_mission39_only_on_yeast_path_and_does_not_execute_sweep(self):
        source = (ROOT / 'code' / 'window.py').read_text()
        self.assertIn("not is_ecoli and '39' in self.player.missions_activated", source)
        self.assertIn('mission39_sweep_requested = bool(', source)
        self.assertIn('run_mission39_bypass_rescue_check_remote(', source)
        self.assertIn('run_mission39_bypass_rescue_check(', source)
        self.assertIn('sweep_requested=mission39_sweep_requested', source)
        self.assertIn('mission39_bypass_rescue_check', source)
        bound_block = source[
            source.index('bound_sweep_mission_active = ('):
            source.index('if bound_sweep_mission_active:', source.index('bound_sweep_mission_active = ('))
        ]
        self.assertNotIn("'39' in self.player.missions_activated", bound_block)

    def test_answer_field_submits_on_enter_and_button(self):
        source = (ROOT / 'code' / 'mission39.py').read_text()
        self.assertIn('onreturn=self.deliver_results', source)
        self.assertIn("'Deliver Interpretation'", source)
        self.assertIn('self.deliver_results(answer_input.get_value())', source)
        self.assertIn('Bound Sweep: not used; leave it off for this mission', source)

    def test_completed_dialogue_prepares_final_mortis_certification(self):
        source = (ROOT / 'code' / 'mission39.py').read_text()
        self.assertIn('Mortis will test whether it survives a changing environment.', source)
        self.assertIn('one successful rescue is not proof of robustness', source)

    def test_validator_source_contains_no_solver_call(self):
        source = (ROOT / 'code' / 'simulation.py').read_text()
        block = source[source.index('def _build_mission39_data('):source.index('def run_mission39_bypass_rescue_check(')]
        self.assertNotIn('.simulate(', block)
        self.assertNotIn('linprog(', block)
        self.assertNotIn('run_simul(', block)
        self.assertNotIn('/simulate', block)

    def test_bundled_model_places_acetaldehyde_downstream_of_pyruvate_decarboxylase(self):
        with gzip.open(ROOT / 'data' / 'models' / 'iMM904.xml.gz', 'rb') as handle:
            root = ET.parse(handle).getroot()
        ns = {'c': self.CORE_NS}
        model = root.find('c:model', ns)
        reaction = next(r for r in model.find('c:listOfReactions', ns) if r.attrib['id'] == 'R_PYRDC')
        reactants = {x.attrib['species'] for x in reaction.find('c:listOfReactants', ns)}
        products = {x.attrib['species'] for x in reaction.find('c:listOfProducts', ns)}
        self.assertIn('M_pyr_c', reactants)
        self.assertIn('M_acald_c', products)
        self.assertTrue(any(r.attrib['id'] == 'R_ACALDt' for r in model.find('c:listOfReactions', ns)))

    def _independent_pfba(self, opened_exchange=None):
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
        for reaction_id in simulation.MISSION39_EXPECTED_DISABLED:
            lower[reaction_index[reaction_id]] = 0.0
            upper[reaction_index[reaction_id]] = 0.0
        if opened_exchange:
            lower[reaction_index[opened_exchange]] = -10.0
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

    def test_independent_pfba_reproduces_unique_acetaldehyde_rescue(self):
        default = self._independent_pfba()
        pyr = self._independent_pfba('EX_pyr_e')
        etoh = self._independent_pfba('EX_etoh_e')
        acald = self._independent_pfba('EX_acald_e')
        self.assertAlmostEqual(default['BIOMASS_SC5_notrace'], 0.0954254, places=5)
        self.assertAlmostEqual(default['EX_pyr_e'], 3.126665, places=4)
        self.assertAlmostEqual(pyr['BIOMASS_SC5_notrace'] / default['BIOMASS_SC5_notrace'], 1.0, places=4)
        self.assertLess(etoh['BIOMASS_SC5_notrace'] / default['BIOMASS_SC5_notrace'], 1.01)
        self.assertGreater(acald['BIOMASS_SC5_notrace'] / default['BIOMASS_SC5_notrace'], 2.0)
        self.assertGreater(acald['EX_etoh_e'], 5.0)
        self.assertLessEqual(acald['EX_acald_e'], -9.9)
        self.assertGreater(pyr['EX_pyr_e'], 0.0)  # opening uptake still leaves net secretion


if __name__ == '__main__':
    unittest.main()
