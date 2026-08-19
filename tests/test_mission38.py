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


class Mission38RegressionTests(unittest.TestCase):
    CORE_NS = 'http://www.sbml.org/sbml/level3/version1/core'
    FBC_NS = 'http://www.sbml.org/sbml/level3/version1/fbc/version2'

    def make_complete_report(self):
        report = simulation._mission38_empty_report()
        common = {
            'method': 'pFBA',
            'objective': 'BIOMASS_SC5_notrace',
            'model_id': 'yeast_iMM904',
            'glucose_uptake': 10.0,
            'oxygen_uptake': 2.0,
            'primary_objective_flux': 0.287866,
            'active_reaction_count': 299,
            'tracked_fluxes': ['EX_etoh_e', 'EX_succ_e', 'EX_pyr_e'],
        }
        values = {
            'wt': (0.287866, 15.815475, 0.0, 0.0, 338.006, []),
            'frd1': (0.287866, 15.815475, 0.0, 0.0, 338.006, ['FRDcm']),
            'mae1': (0.287866, 15.815475, 0.0, 0.0, 338.006, ['ME1m', 'ME2m']),
            'pdc_cut': (0.176148, 0.009179, 6.386125, 0.0, 415.543, ['3MOBDC', 'ACALDCD', 'PYRDC', 'PYRDC2']),
            'pdc_cut_frd1': (0.095425, 0.0, 0.010554, 3.126665, 108.717, ['3MOBDC', 'ACALDCD', 'FRDcm', 'PYRDC', 'PYRDC2']),
            'pdc_cut_mae1': (0.164714, 0.0, 5.540616, 0.0, 364.320, ['3MOBDC', 'ACALDCD', 'ME1m', 'ME2m', 'PYRDC', 'PYRDC2']),
        }
        for condition_id, (growth, ethanol, succinate, pyruvate, total, disabled) in values.items():
            run = dict(common)
            run.update({
                'condition_id': condition_id,
                'knocked_out_genes': list(simulation.MISSION38_GENOTYPES[condition_id]),
                'growth': growth,
                'primary_objective_flux': growth,
                'ethanol_secretion': ethanol,
                'succinate_secretion': succinate,
                'pyruvate_secretion': pyruvate,
                'total_absolute_flux': total,
                'disabled_reactions': list(disabled),
            })
            report['runs'][condition_id] = run
        return simulation._mission38_refresh_derived(report)

    def make_visible_payload(self, growth, ethanol, succinate, pyruvate, disabled):
        production = {
            'selected_ids': ['EX_etoh_e', 'EX_succ_e', 'EX_pyr_e'],
            'items': [
                {'reaction_id': 'EX_etoh_e', 'production_flux': ethanol},
                {'reaction_id': 'EX_succ_e', 'production_flux': succinate},
                {'reaction_id': 'EX_pyr_e', 'production_flux': pyruvate},
            ],
            'biomass_raw': growth,
            'method_diagnostics': {
                'model_id': 'yeast_iMM904',
                'method': 'pFBA',
                'objective_reaction': 'BIOMASS_SC5_notrace',
                'primary_objective_flux': growth,
                'method_score': 100.0,
                'method_score_name': 'Total absolute flux',
                'total_absolute_flux': 100.0,
                'active_reaction_count': 250,
                'gpr_disabled_reactions': list(disabled),
            },
        }
        medium = {
            'items': [
                {'reaction_id': 'EX_glc__D_e', 'raw_flux': -10.0, 'uptake_flux': 10.0, 'secretion_flux': 0.0},
                {'reaction_id': 'EX_o2_e', 'raw_flux': -2.0, 'uptake_flux': 2.0, 'secretion_flux': 0.0},
            ]
        }
        return production, medium

    def test_unlock_requires_mission37(self):
        self.assertFalse(simulation.is_mission38_unlocked(['36']))
        self.assertTrue(simulation.is_mission38_unlocked(['37']))

    def test_dependency_matrix_is_fixed_and_uses_common_gene_ids(self):
        self.assertEqual(len(simulation.MISSION38_CONDITION_ORDER), 6)
        self.assertEqual(simulation.MISSION38_GENES['FRD1'], 'YEL047C')
        self.assertEqual(simulation.MISSION38_GENES['MAE1'], 'YKL029C')
        self.assertEqual(
            set(simulation.MISSION38_GENOTYPES['pdc_cut']),
            {'YLR044C', 'YLR134W', 'YGR087C'},
        )
        self.assertEqual(
            set(simulation.MISSION38_REQUIRED_PRODUCTION_FLUXES),
            {'EX_etoh_e', 'EX_succ_e', 'EX_pyr_e'},
        )

    def test_wt_growth_retention_is_available_before_pdc_reference(self):
        report = simulation._mission38_empty_report()
        report['runs'] = {
            'wt': {'growth': 0.288},
            'frd1': {'growth': 0.288},
            'mae1': {'growth': 0.288},
        }
        simulation._mission38_refresh_derived(report)

        self.assertAlmostEqual(report['wt_growth_retention']['wt'], 1.0)
        self.assertAlmostEqual(report['wt_growth_retention']['frd1'], 1.0)
        self.assertAlmostEqual(report['wt_growth_retention']['mae1'], 1.0)
        self.assertEqual(report['pdc_growth_retention'], {})
        self.assertEqual(report['pdc_succinate_retention'], {})
        self.assertFalse(report['evidence_ready'])

        text = simulation.build_mission38_background_dependency_report_text(report)
        self.assertIn('WT | 0.288 | 100.0%', text)
        self.assertIn('FRD1 | 0.288 | 100.0%', text)
        self.assertIn('MAE1 | 0.288 | 100.0%', text)
        self.assertIn('PDC1 + PDC5 + PDC6 | pending', text)

    def test_complete_visible_evidence_derives_unique_background_vulnerability(self):
        report = self.make_complete_report()
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['dependency_supported'])
        self.assertEqual(report['unique_candidate'], 'FRD1')
        self.assertGreaterEqual(report['wt_growth_retention']['frd1'], 0.95)
        self.assertLessEqual(report['pdc_growth_retention']['FRD1'], 0.60)
        self.assertLessEqual(report['pdc_succinate_retention']['FRD1'], 0.10)
        self.assertGreater(report['pdc_growth_retention']['MAE1'], 0.60)

    def test_answer_is_rederived_from_visible_runs(self):
        report = self.make_complete_report()
        report['unique_candidate'] = 'MAE1'
        self.assertTrue(simulation.mission38_answer_matches('FRD1', report))
        self.assertTrue(simulation.mission38_answer_matches('YEL047C', report))
        self.assertFalse(simulation.mission38_answer_matches('MAE1', report))

    def test_old_report_version_is_rejected(self):
        prepared = simulation._mission38_prepare_report({'mission_id': '38', 'check_version': 0, 'runs': {'x': 1}})
        self.assertEqual(prepared['runs'], {})
        self.assertFalse(prepared['evidence_ready'])

    def test_report_never_prints_solution_line(self):
        text = simulation.build_mission38_background_dependency_report_text(self.make_complete_report())
        self.assertTrue(text.startswith('Mission 38 Background-Dependent Compensation Audit'))
        self.assertIn('Evidence complete.', text)
        self.assertIn('WT background', text)
        self.assertIn('PDC-cut-set background', text)
        self.assertNotIn('Answer:', text)
        self.assertNotIn('Correct candidate:', text)
        self.assertNotIn('Unique candidate:', text)

    def test_landing_report_title_can_be_suppressed_contextually(self):
        text = simulation.build_mission38_background_dependency_report_text(
            self.make_complete_report(), include_title=False
        )
        self.assertTrue(text.startswith('Controlled dependency matrix:'))
        source = (ROOT / 'code' / 'mission38.py').read_text()
        self.assertIn('report_include_title = bool(', source)
        self.assertIn('include_title=report_include_title', source)

    def test_briefing_and_hint_keep_historical_green_theme_background(self):
        source = (ROOT / 'code' / 'mission38.py').read_text()
        briefing_start = source.index('briefing = pygame_menu.Menu')
        briefing_end = source.index("briefing.add.button('Back'", briefing_start)
        hint_start = source.index('hint3 = pygame_menu.Menu', briefing_end)
        hint_end = source.index("hint1.add.button('Back'", hint_start)
        self.assertNotIn("background_color='white'", source[briefing_start:briefing_end])
        self.assertNotIn("background_color='white'", source[hint_start:hint_end])

    def test_bound_sweep_on_rejects_run_without_erasing_evidence(self):
        existing = self.make_complete_report()
        before = json.loads(json.dumps(existing['runs']))
        genes = {gene: True for gene in simulation.MISSION38_GENES.values()}
        genes['YEL047C'] = False
        production, medium = self.make_visible_payload(0.287866, 15.815475, 0.0, 0.0, ['FRDcm'])
        with patch.object(simulation, '_model_environment_is_default', return_value=True), \
             patch.object(simulation, 'save_mission38_background_dependency'):
            report = simulation._build_mission38_data(
                'pFBA', 'BIOMASS_SC5_notrace', 0.287866,
                genes, {}, model_id='yeast_iMM904',
                selected_fluxes=['EX_etoh_e', 'EX_succ_e', 'EX_pyr_e'],
                production_fluxes=production, medium_fluxes=medium,
                existing_report=existing, sweep_requested=True,
            )
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['runs'], before)
        self.assertTrue(any('Turn Bound Sweep off' in issue for issue in report['current_issues']))

    def test_invalid_setup_preserves_previous_valid_evidence(self):
        existing = self.make_complete_report()
        before = json.loads(json.dumps(existing['runs']))
        genes = {gene: True for gene in simulation.MISSION38_GENES.values()}
        genes['YEL047C'] = False
        production, medium = self.make_visible_payload(0.287866, 15.815475, 0.0, 0.0, ['FRDcm'])
        with patch.object(simulation, '_model_environment_is_default', return_value=True), \
             patch.object(simulation, 'save_mission38_background_dependency'):
            report = simulation._build_mission38_data(
                'FBA', 'BIOMASS_SC5_notrace', 0.287866,
                genes, {}, model_id='yeast_iMM904',
                selected_fluxes=['EX_etoh_e', 'EX_succ_e'],
                production_fluxes=production, medium_fluxes=medium,
                existing_report=existing,
            )
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['runs'], before)
        self.assertTrue(any('pFBA' in issue for issue in report['current_issues']))
        self.assertTrue(any('Track exactly' in issue for issue in report['current_issues']))

    def test_valid_run_can_be_recorded_before_reference_runs(self):
        report = simulation._mission38_empty_report()
        genes = {gene: True for gene in simulation.MISSION38_GENES.values()}
        for gene in simulation.MISSION38_GENOTYPES['pdc_cut_frd1']:
            genes[gene] = False
        production, medium = self.make_visible_payload(
            0.095425, 0.0, 0.010554, 3.126665,
            ['3MOBDC', 'ACALDCD', 'FRDcm', 'PYRDC', 'PYRDC2'],
        )
        with patch.object(simulation, '_model_environment_is_default', return_value=True), \
             patch.object(simulation, 'save_mission38_background_dependency'):
            report = simulation._build_mission38_data(
                'pFBA', 'BIOMASS_SC5_notrace', 0.095425,
                genes, {}, model_id='yeast_iMM904',
                selected_fluxes=['EX_etoh_e', 'EX_succ_e', 'EX_pyr_e'],
                production_fluxes=production, medium_fluxes=medium,
                existing_report=report,
            )
        self.assertIn('pdc_cut_frd1', report['runs'])
        self.assertFalse(report['evidence_ready'])
        self.assertIn('wt', report['missing_conditions'])
        self.assertIn('pdc_cut', report['missing_conditions'])

    def test_wrong_gpr_disabled_set_is_rejected(self):
        genes = {gene: True for gene in simulation.MISSION38_GENES.values()}
        for gene in simulation.MISSION38_GENOTYPES['pdc_cut_frd1']:
            genes[gene] = False
        production, medium = self.make_visible_payload(0.095425, 0.0, 0.010554, 3.126665, ['PYRDC', 'PYRDC2', 'FRDcm'])
        with patch.object(simulation, '_model_environment_is_default', return_value=True), \
             patch.object(simulation, 'save_mission38_background_dependency'):
            report = simulation._build_mission38_data(
                'pFBA', 'BIOMASS_SC5_notrace', 0.095425,
                genes, {}, model_id='yeast_iMM904',
                selected_fluxes=['EX_etoh_e', 'EX_succ_e', 'EX_pyr_e'],
                production_fluxes=production, medium_fluxes=medium,
                existing_report=simulation._mission38_empty_report(),
            )
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(any('GPR-disabled reaction set' in issue for issue in report['current_issues']))

    def test_state_is_json_serialisable(self):
        json.dumps(self.make_complete_report())

    def test_save_load_contract_exists_for_desktop_and_web(self):
        self.assertTrue(hasattr(save_load, 'save_mission38_background_dependency'))
        self.assertTrue(hasattr(save_load, 'load_mission38_background_dependency'))
        self.assertTrue(hasattr(save_load, 'clear_mission38_background_dependency'))

    def test_umbra_tiled_object_and_dialogue_asset_are_reused(self):
        tmx = (ROOT / 'data' / 'map_lb.tmx').read_text()
        self.assertIn('name="Umbra"', tmx)
        self.assertTrue((ROOT / 'graphics' / 'dialogues' / 'umbra.jpg').exists())

    def test_umbra_interaction_is_wired_to_mission38(self):
        level = (ROOT / 'code' / 'level.py').read_text()
        player = (ROOT / 'code' / 'player.py').read_text()
        self.assertIn('from mission38 import Mission38', level)
        self.assertIn("if obj.name == 'Umbra':", level)
        self.assertIn('talk_38 = self.toggle_talk_38', level)
        self.assertIn("name == 'Umbra'", player)
        self.assertIn('self.talk_38()', player)

    def test_window_records_mission38_only_on_yeast_path_and_does_not_execute_sweep(self):
        source = (ROOT / 'code' / 'window.py').read_text()
        self.assertIn("not is_ecoli and '38' in self.player.missions_activated", source)
        self.assertIn('mission38_sweep_requested = bool(', source)
        self.assertIn('run_mission38_background_dependency_check_remote(', source)
        self.assertIn('run_mission38_background_dependency_check(', source)
        self.assertIn('sweep_requested=mission38_sweep_requested', source)
        self.assertIn('mission38_background_dependency_check', source)
        bound_block = source[
            source.index('bound_sweep_mission_active = ('):
            source.index('if bound_sweep_mission_active:', source.index('bound_sweep_mission_active = ('))
        ]
        self.assertNotIn("'38' in self.player.missions_activated", bound_block)

    def test_answer_field_submits_on_enter_and_button(self):
        source = (ROOT / 'code' / 'mission38.py').read_text()
        self.assertIn('onreturn=self.deliver_results', source)
        self.assertIn("'Deliver Interpretation'", source)
        self.assertIn('self.deliver_results(answer_input.get_value())', source)
        self.assertIn('Bound Sweep: not used; leave it off for this mission', source)

    def test_validator_source_contains_no_solver_call(self):
        source = (ROOT / 'code' / 'simulation.py').read_text()
        block = source[source.index('def _build_mission38_data('):source.index('def run_mission38_background_dependency_check(')]
        self.assertNotIn('.simulate(', block)
        self.assertNotIn('linprog(', block)
        self.assertNotIn('run_simul(', block)
        self.assertNotIn('/simulate', block)

    def _gene_set_for_reaction(self, reaction_id):
        with gzip.open(ROOT / 'data' / 'models' / 'iMM904.xml.gz', 'rb') as handle:
            root = ET.parse(handle).getroot()
        ns = {'c': self.CORE_NS, 'f': self.FBC_NS}
        model = root.find('c:model', ns)
        reaction = next(
            r for r in model.find('c:listOfReactions', ns)
            if r.attrib['id'] == 'R_' + reaction_id
        )
        association = reaction.find('f:geneProductAssociation', ns)
        return {
            element.attrib[f'{{{self.FBC_NS}}}geneProduct'].removeprefix('G_')
            for element in association.iter()
            if element.tag.endswith('geneProductRef')
        }

    def test_bundled_model_gpr_supports_frd1_and_mae1_candidates(self):
        self.assertEqual(self._gene_set_for_reaction('FRDcm'), {'YEL047C'})
        self.assertEqual(self._gene_set_for_reaction('ME1m'), {'YKL029C'})
        self.assertEqual(self._gene_set_for_reaction('ME2m'), {'YKL029C'})

    def _independent_pfba(self, disabled_reactions=()):
        with gzip.open(ROOT / 'data' / 'models' / 'iMM904.xml.gz', 'rb') as handle:
            root = ET.parse(handle).getroot()
        ns = {'c': self.CORE_NS, 'f': self.FBC_NS}
        model = root.find('c:model', ns)
        params = {
            p.attrib['id']: float(p.attrib['value'])
            for p in model.find('c:listOfParameters', ns)
        }
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
        for reaction_id in disabled_reactions:
            lower[reaction_index[reaction_id]] = 0.0
            upper[reaction_index[reaction_id]] = 0.0
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

    def test_independent_pfba_reproduces_background_specific_frd1_effect(self):
        pdc_disabled = ['3MOBDC', 'ACALDCD', 'PYRDC', 'PYRDC2']
        wt = self._independent_pfba()
        frd1 = self._independent_pfba(['FRDcm'])
        mae1 = self._independent_pfba(['ME1m', 'ME2m'])
        pdc = self._independent_pfba(pdc_disabled)
        pdc_frd1 = self._independent_pfba(pdc_disabled + ['FRDcm'])
        pdc_mae1 = self._independent_pfba(pdc_disabled + ['ME1m', 'ME2m'])

        self.assertAlmostEqual(wt['BIOMASS_SC5_notrace'], 0.287866, places=5)
        self.assertAlmostEqual(frd1['BIOMASS_SC5_notrace'] / wt['BIOMASS_SC5_notrace'], 1.0, places=4)
        self.assertAlmostEqual(mae1['BIOMASS_SC5_notrace'] / wt['BIOMASS_SC5_notrace'], 1.0, places=4)
        self.assertAlmostEqual(pdc['BIOMASS_SC5_notrace'], 0.176148, places=5)
        self.assertAlmostEqual(pdc['EX_succ_e'], 6.386125, places=4)
        self.assertAlmostEqual(pdc_frd1['BIOMASS_SC5_notrace'], 0.095425, places=5)
        self.assertAlmostEqual(pdc_frd1['EX_succ_e'], 0.010554, places=4)
        self.assertAlmostEqual(pdc_frd1['EX_pyr_e'], 3.126665, places=4)
        self.assertAlmostEqual(pdc_mae1['BIOMASS_SC5_notrace'], 0.164714, places=5)
        self.assertAlmostEqual(pdc_mae1['EX_succ_e'], 5.540616, places=4)
        self.assertAlmostEqual(pdc_mae1['EX_pyr_e'], 0.0, places=5)
        self.assertLess(pdc_frd1['BIOMASS_SC5_notrace'] / pdc['BIOMASS_SC5_notrace'], 0.60)
        self.assertGreater(pdc_mae1['BIOMASS_SC5_notrace'] / pdc['BIOMASS_SC5_notrace'], 0.90)


if __name__ == '__main__':
    unittest.main()
