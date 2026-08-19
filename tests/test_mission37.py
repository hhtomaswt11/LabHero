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


class Mission37RegressionTests(unittest.TestCase):
    CORE_NS = 'http://www.sbml.org/sbml/level3/version1/core'
    FBC_NS = 'http://www.sbml.org/sbml/level3/version1/fbc/version2'

    def make_complete_report(self):
        report = simulation._mission37_empty_report()
        common = {
            'method': 'pFBA',
            'objective': 'BIOMASS_SC5_notrace',
            'model_id': 'yeast_iMM904',
            'glucose_uptake': 10.0,
            'oxygen_uptake': 2.0,
            'primary_objective_flux': 0.287866,
            'active_reaction_count': 299,
            'tracked_fluxes': ['EX_etoh_e', 'EX_succ_e'],
        }
        normal = {
            **common,
            'growth': 0.287866,
            'ethanol_secretion': 15.815475,
            'succinate_secretion': 0.0,
            'total_absolute_flux': 338.005992,
            'disabled_reactions': [],
        }
        for genotype_id in simulation.MISSION37_GENOTYPE_ORDER[:-1]:
            run = dict(normal)
            run['genotype_id'] = genotype_id
            run['knocked_out_genes'] = list(simulation.MISSION37_GENOTYPES[genotype_id])
            report['runs'][genotype_id] = run
        triple = {
            **common,
            'genotype_id': 'pdc1_pdc5_pdc6',
            'knocked_out_genes': list(simulation.MISSION37_GENOTYPES['pdc1_pdc5_pdc6']),
            'growth': 0.176148,
            'primary_objective_flux': 0.176148,
            'ethanol_secretion': 0.009179,
            'succinate_secretion': 6.386125,
            'total_absolute_flux': 415.542796,
            'disabled_reactions': ['3MOBDC', 'ACALDCD', 'PYRDC', 'PYRDC2'],
        }
        report['runs']['pdc1_pdc5_pdc6'] = triple
        return simulation._mission37_refresh_derived(report)

    def make_visible_payload(self, growth, ethanol, succinate, disabled):
        production = {
            'selected_ids': ['EX_etoh_e', 'EX_succ_e'],
            'items': [
                {'reaction_id': 'EX_etoh_e', 'production_flux': ethanol},
                {'reaction_id': 'EX_succ_e', 'production_flux': succinate},
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

    def test_unlock_requires_mission36(self):
        self.assertFalse(simulation.is_mission37_unlocked(['35']))
        self.assertTrue(simulation.is_mission37_unlocked(['36']))

    def test_required_genotype_series_is_fixed_and_progressive(self):
        self.assertEqual(len(simulation.MISSION37_GENOTYPE_ORDER), 6)
        self.assertEqual(simulation.MISSION37_GENOTYPES['wild_type'], ())
        self.assertEqual(
            set(simulation.MISSION37_GENOTYPES['pdc1_pdc5_pdc6']),
            {'YLR044C', 'YLR134W', 'YGR087C'},
        )
        self.assertEqual(simulation.MISSION37_PDC_GENES['PDC1'], 'YLR044C')
        self.assertEqual(simulation.MISSION37_PDC_GENES['PDC5'], 'YLR134W')
        self.assertEqual(simulation.MISSION37_PDC_GENES['PDC6'], 'YGR087C')

    def test_complete_visible_evidence_derives_unique_cut_set(self):
        report = self.make_complete_report()
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['cut_set_supported'])
        self.assertEqual(report['unique_cut_set'], 'pdc1_pdc5_pdc6')
        self.assertLess(report['ethanol_retention']['pdc1_pdc5_pdc6'], 0.01)
        self.assertGreater(report['growth_retention']['pdc1_pdc5_pdc6'], 0.50)
        self.assertTrue(report['target_reactions_disabled']['pdc1_pdc5_pdc6'])
        self.assertFalse(report['target_reactions_disabled']['pdc1_pdc5'])

    def test_answer_is_derived_from_report_not_a_separate_expected_field(self):
        report = self.make_complete_report()
        report['unique_cut_set'] = 'pdc1'
        # Refreshing must recover the cut set from visible runs before matching.
        self.assertTrue(simulation.mission37_answer_matches('PDC1 + PDC5 + PDC6', report))
        self.assertFalse(simulation.mission37_answer_matches('PDC1 + PDC5', report))
        self.assertTrue(simulation.mission37_answer_matches('YLR044C YLR134W YGR087C', report))
        self.assertTrue(simulation.mission37_answer_matches('all three', report))

    def test_old_report_version_is_rejected(self):
        prepared = simulation._mission37_prepare_report({'mission_id': '37', 'check_version': 0, 'runs': {'x': 1}})
        self.assertEqual(prepared['runs'], {})
        self.assertFalse(prepared['evidence_ready'])

    def test_report_never_prints_the_answer_as_a_solution_line(self):
        text = simulation.build_mission37_fermentation_cut_set_report_text(self.make_complete_report())
        self.assertTrue(text.startswith('Mission 37 Fermentation Redundancy Cut Set'))
        self.assertIn('Evidence complete.', text)
        self.assertIn('smallest tested knockout set', text)
        self.assertNotIn('Answer:', text)
        self.assertNotIn('Correct cut set:', text)
        self.assertIn('GPR-disabled reactions', text)
        self.assertIn('3MOBDC, ACALDCD, PYRDC, PYRDC2', text)
        self.assertNotIn('No hidden validation simulation', text)

    def test_landing_report_title_can_be_suppressed_contextually(self):
        text = simulation.build_mission37_fermentation_cut_set_report_text(
            self.make_complete_report(), include_title=False
        )
        self.assertTrue(text.startswith('Controlled protocol:'))
        source = (ROOT / 'code' / 'mission37.py').read_text()
        self.assertIn('report_include_title = bool(', source)
        self.assertIn('include_title=report_include_title', source)

    def test_briefing_and_hint_keep_historical_green_theme_background(self):
        source = (ROOT / 'code' / 'mission37.py').read_text()
        briefing_start = source.index('briefing = pygame_menu.Menu')
        briefing_end = source.index("briefing.add.button('Back'", briefing_start)
        briefing_block = source[briefing_start:briefing_end]
        hint_start = source.index('hint3 = pygame_menu.Menu', briefing_end)
        hint_end = source.index("hint1.add.button('Back'", hint_start)
        hint_block = source[hint_start:hint_end]
        self.assertNotIn("background_color='white'", briefing_block)
        self.assertNotIn("background_color='white'", hint_block)

    def test_bound_sweep_on_rejects_run_without_erasing_valid_evidence(self):
        existing = self.make_complete_report()
        before_runs = json.loads(json.dumps(existing['runs']))
        genes = {gene: True for gene in simulation.MISSION37_PDC_GENES.values()}
        genes['YLR044C'] = False
        production, medium = self.make_visible_payload(0.287866, 15.815475, 0.0, [])
        with patch.object(simulation, '_model_environment_is_default', return_value=True), \
             patch.object(simulation, 'save_mission37_fermentation_cut_set') as save_report:
            report = simulation._build_mission37_data(
                'pFBA', 'BIOMASS_SC5_notrace', 0.287866,
                genes, {}, model_id='yeast_iMM904',
                selected_fluxes=['EX_etoh_e', 'EX_succ_e'],
                production_fluxes=production, medium_fluxes=medium,
                existing_report=existing,
                sweep_requested=True,
            )
        self.assertFalse(report['current_run_valid'])
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['recorded_run_count'], 6)
        self.assertEqual(report['runs'], before_runs)
        self.assertTrue(report['latest_attempt']['sweep_requested'])
        self.assertTrue(any('Turn Bound Sweep off' in issue for issue in report['current_issues']))
        text = simulation.build_mission37_fermentation_cut_set_report_text(report)
        self.assertIn('Latest run was not recorded:', text)
        self.assertIn('Turn Bound Sweep off for Mission 37', text)
        self.assertIn('Previously valid Mission 37 evidence remains available.', text)
        save_report.assert_called_once()

    def test_remote_wrapper_forwards_bound_sweep_protocol_state(self):
        with patch.object(
            simulation,
            'run_mission37_fermentation_cut_set_check',
            return_value={'mission_id': '37'},
        ) as local_check:
            result = simulation.run_mission37_fermentation_cut_set_check_remote(
                'http://backend.test',
                ('BIOMASS_SC5_notrace', 0.2, {}, {}),
                sweep_requested=True,
            )
        self.assertEqual(result, {'mission_id': '37'})
        local_check.assert_called_once_with(
            ('BIOMASS_SC5_notrace', 0.2, {}, {}),
            sweep_requested=True,
        )

    def test_invalid_run_preserves_previous_valid_evidence(self):
        existing = self.make_complete_report()
        production, medium = self.make_visible_payload(0.2, 1.0, 0.0, [])
        with patch.object(simulation, '_model_environment_is_default', return_value=True), \
             patch.object(simulation, 'save_mission37_fermentation_cut_set') as save_report:
            report = simulation._build_mission37_data(
                'FBA', 'BIOMASS_SC5_notrace', 0.2,
                {'YOL086C': False}, {},
                model_id='yeast_iMM904',
                selected_fluxes=['EX_etoh_e', 'EX_succ_e'],
                production_fluxes=production,
                medium_fluxes=medium,
                existing_report=existing,
            )
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(report['evidence_ready'])
        self.assertEqual(report['recorded_run_count'], 6)
        self.assertTrue(any('pFBA' in issue for issue in report['current_issues']))
        self.assertTrue(any('genotype series' in issue for issue in report['current_issues']))
        save_report.assert_called_once()

    def test_valid_run_can_be_recorded_before_wild_type_and_completed_later(self):
        report = simulation._mission37_empty_report()
        genes = {gene: True for gene in simulation.MISSION37_PDC_GENES.values()}
        genes['YLR044C'] = False
        production, medium = self.make_visible_payload(0.287866, 15.815475, 0.0, [])
        with patch.object(simulation, '_model_environment_is_default', return_value=True), \
             patch.object(simulation, 'save_mission37_fermentation_cut_set'):
            report = simulation._build_mission37_data(
                'pFBA', 'BIOMASS_SC5_notrace', 0.287866,
                genes, {}, model_id='yeast_iMM904',
                selected_fluxes=['EX_etoh_e', 'EX_succ_e'],
                production_fluxes=production, medium_fluxes=medium,
                existing_report=report,
            )
        self.assertIn('pdc1', report['runs'])
        self.assertFalse(report['evidence_ready'])
        self.assertIn('wild_type', report['missing_conditions'])

    def test_wrong_gpr_disabled_set_is_rejected(self):
        genes = {gene: False for gene in simulation.MISSION37_PDC_GENES.values()}
        production, medium = self.make_visible_payload(0.176148, 0.009179, 6.386125, ['PYRDC', 'PYRDC2'])
        with patch.object(simulation, '_model_environment_is_default', return_value=True), \
             patch.object(simulation, 'save_mission37_fermentation_cut_set'):
            report = simulation._build_mission37_data(
                'pFBA', 'BIOMASS_SC5_notrace', 0.176148,
                genes, {}, model_id='yeast_iMM904',
                selected_fluxes=['EX_etoh_e', 'EX_succ_e'],
                production_fluxes=production, medium_fluxes=medium,
                existing_report=simulation._mission37_empty_report(),
            )
        self.assertFalse(report['current_run_recorded'])
        self.assertTrue(any('GPR-disabled reaction set' in issue for issue in report['current_issues']))

    def test_state_is_json_serialisable(self):
        json.dumps(self.make_complete_report())

    def test_save_load_contract_exists_for_desktop_and_web(self):
        self.assertTrue(hasattr(save_load, 'save_mission37_fermentation_cut_set'))
        self.assertTrue(hasattr(save_load, 'load_mission37_fermentation_cut_set'))
        self.assertTrue(hasattr(save_load, 'clear_mission37_fermentation_cut_set'))

    def test_voss_tiled_object_and_dialogue_asset_are_reused(self):
        tmx = (ROOT / 'data' / 'map_lb.tmx').read_text()
        self.assertIn('name="Voss"', tmx)
        self.assertTrue((ROOT / 'graphics' / 'dialogues' / 'voss.jpg').exists())

    def test_voss_interaction_is_wired_to_mission37(self):
        level = (ROOT / 'code' / 'level.py').read_text()
        player = (ROOT / 'code' / 'player.py').read_text()
        self.assertIn('from mission37 import Mission37', level)
        self.assertIn("if obj.name == 'Voss':", level)
        self.assertIn('talk_37 = self.toggle_talk_37', level)
        self.assertIn("name == 'Voss'", player)
        self.assertIn('self.talk_37()', player)

    def test_window_records_mission37_only_on_yeast_path(self):
        source = (ROOT / 'code' / 'window.py').read_text()
        self.assertIn("not is_ecoli and '37' in self.player.missions_activated", source)
        self.assertIn("mission37_sweep_requested = bool(", source)
        self.assertIn("get('execute_sweep', False)", source)
        self.assertIn('run_mission37_fermentation_cut_set_check_remote(', source)
        self.assertIn('sweep_requested=mission37_sweep_requested', source)
        self.assertIn('run_mission37_fermentation_cut_set_check(', source)
        self.assertIn('mission37_fermentation_cut_set_check', source)
        bound_block = source[
            source.index('bound_sweep_mission_active = ('):
            source.index('if bound_sweep_mission_active:', source.index('bound_sweep_mission_active = ('))
        ]
        self.assertNotIn("'37' in self.player.missions_activated", bound_block)

    def test_answer_field_submits_on_enter_and_button(self):
        source = (ROOT / 'code' / 'mission37.py').read_text()
        self.assertIn('onreturn=self.deliver_results', source)
        self.assertIn("'Deliver Interpretation'", source)
        self.assertIn('self.deliver_results(answer_input.get_value())', source)
        self.assertIn('Bound Sweep: not used; leave it off for this mission', source)

    def test_validator_source_contains_no_solver_call(self):
        source = (ROOT / 'code' / 'simulation.py').read_text()
        block = source[source.index('def _build_mission37_data('):source.index('def run_mission37_fermentation_cut_set_check(')]
        self.assertNotIn('.simulate(', block)
        self.assertNotIn('linprog(', block)
        self.assertNotIn('run_simul(', block)
        self.assertNotIn('/simulate', block)

    def _pdc_gene_set_for_reaction(self, reaction_id):
        with gzip.open(ROOT / 'data' / 'models' / 'iMM904.xml.gz', 'rb') as handle:
            root = ET.parse(handle).getroot()
        ns = {'c': self.CORE_NS, 'f': self.FBC_NS}
        model = root.find('c:model', ns)
        reaction = next(
            r for r in model.find('c:listOfReactions', ns)
            if r.attrib['id'] == 'R_' + reaction_id
        )
        association = reaction.find('f:geneProductAssociation', ns)
        genes = {
            element.attrib[f'{{{self.FBC_NS}}}geneProduct'].removeprefix('G_')
            for element in association.iter()
            if element.tag.endswith('geneProductRef')
        }
        return genes, ET.tostring(association, encoding='unicode')

    def test_bundled_model_gpr_supports_three_way_pdc_redundancy(self):
        expected = {'YLR044C', 'YLR134W', 'YGR087C'}
        for reaction_id in ('PYRDC', 'PYRDC2'):
            genes, xml = self._pdc_gene_set_for_reaction(reaction_id)
            self.assertEqual(genes, expected)
            self.assertIn(':or', xml)

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
        lower = np.zeros(len(reactions))
        upper = np.zeros(len(reactions))
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
        primary = linprog(
            c, A_eq=matrix, b_eq=np.zeros(len(species)),
            bounds=list(zip(lower, upper)), method='highs',
        )
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

    def test_independent_pfba_reproduces_mission37_wt_and_complete_cut_set(self):
        wt = self._independent_pfba()
        mutant = self._independent_pfba(simulation.MISSION37_TRIPLE_DISABLED_REACTIONS)
        self.assertAlmostEqual(wt['BIOMASS_SC5_notrace'], 0.287866, places=5)
        self.assertAlmostEqual(wt['EX_etoh_e'], 15.815475, places=4)
        self.assertAlmostEqual(wt['EX_succ_e'], 0.0, places=5)
        self.assertAlmostEqual(mutant['BIOMASS_SC5_notrace'], 0.176148, places=5)
        self.assertAlmostEqual(mutant['EX_etoh_e'], 0.009179, places=4)
        self.assertAlmostEqual(mutant['EX_succ_e'], 6.386125, places=4)
        self.assertGreater(mutant['BIOMASS_SC5_notrace'] / wt['BIOMASS_SC5_notrace'], 0.50)
        self.assertLess(mutant['EX_etoh_e'] / wt['EX_etoh_e'], 0.01)


if __name__ == '__main__':
    unittest.main()
