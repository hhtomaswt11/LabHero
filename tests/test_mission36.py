from __future__ import annotations
import json, sys, types, unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT/'code'
sys.path.insert(0, str(CODE))
try:
    import pygame
except ModuleNotFoundError:
    pygame=types.ModuleType('pygame'); pygame.Vector2=lambda *a:tuple(a); sys.modules['pygame']=pygame
try:
    import pygame_menu
except ModuleNotFoundError:
    class T:
        def copy(self): return T()
    pm=types.ModuleType('pygame_menu'); pm.themes=types.SimpleNamespace(THEME_GREEN=T()); pm.font=types.SimpleNamespace(FONT_MUNRO='munro'); pm.widgets=types.SimpleNamespace(MENUBAR_STYLE_SIMPLE='simple'); sys.modules['pygame_menu']=pm
_orig=sys.platform
try:
    import mewpy, cobra
except ModuleNotFoundError:
    sys.platform='emscripten'
import simulation
sys.platform=_orig

class Mission36Tests(unittest.TestCase):
    def make_report(self):
        report=simulation._mission36_empty_report()
        report['baseline']={'model_id':'yeast_iMM904','method':'pFBA','objective':'BIOMASS_SC5_notrace','growth':0.287866,'glucose_uptake':10.0,'oxygen_uptake':2.0,'ethanol_secretion':15.815475,'co2_secretion':18.021084,'total_absolute_flux':338.005992,'primary_objective_flux':0.287866,'active_reaction_count':299,'tracked_fluxes':['EX_etoh_e','EX_co2_e']}
        rows=[]
        data=[(-.5,.043264,.5,1.413992,0,1.445005,52.265322),(-1,.073433,1,2,.435941,2.488391,82.270866),(-2,.097803,2,2,2.138132,4.207989,111.672783),(-10,.287866,10,2,15.815475,18.021084,338.005992)]
        for b,g,glu,o2,etoh,co2,total in data:
            rows.append({'model_id':'yeast_iMM904','bound_value':b,'status':'ok','growth_value':g,'tested_reaction_uptake':glu,'oxygen_uptake':o2,'tracked_flux_values':{'EX_etoh_e':etoh,'EX_co2_e':co2},'method_diagnostics':{'total_absolute_flux':total}})
        report['glucose_curve']={'model_id':'yeast_iMM904','method':'pFBA','objective':'BIOMASS_SC5_notrace','knocked_out_genes':[],'environment_changed':False,'variable':'EX_glc__D_e:lower','preset':'yeast_glucose_fermentation_threshold','reaction_id':'EX_glc__D_e','bound':'lower','values':[-.5,-1,-2,-10],'tracked_fluxes':['EX_etoh_e','EX_co2_e'],'rows':rows}
        return simulation._mission36_refresh_derived(report)
    def test_curve_derives_transition_from_visible_rows(self):
        report=self.make_report(); self.assertTrue(report['evidence_ready']); self.assertEqual(report['first_transition_bound'],-1.0); self.assertEqual(list(report['oxygen_binding_by_bound'].values()),[False,True,True,True])
    def test_answer_is_derived_not_hardcoded_field(self):
        report=self.make_report(); report['first_transition_bound']=-2
        self.assertTrue(simulation.mission36_answer_matches('-1', report)); self.assertFalse(simulation.mission36_answer_matches('-0.5', report))
    def test_old_report_version_rejected(self):
        old={'mission_id':'36','check_version':1,'baseline':{'x':1}}; prepared=simulation._mission36_prepare_report(old); self.assertIsNone(prepared['baseline'])
    def test_sweep_config_is_yeast_specific(self):
        with patch.object(simulation,'_read_simulation_model_id',return_value='yeast_iMM904'):
            cfg=simulation._normalise_sweep_config({'sweep_variable':[[('D-Glucose','EX_glc__D_e:lower')]],'sweep_values':[[('Yeast','yeast_glucose_fermentation_threshold')]]},model_id='yeast_iMM904')
        self.assertEqual(cfg['values'],[-.5,-1.,-2.,-10.]); self.assertEqual(cfg['reaction_id'],'EX_glc__D_e')
    def test_report_does_not_print_answer_label(self):
        text=simulation.build_mission36_fermentation_report_text(self.make_report()); self.assertIn('Evidence complete.',text); self.assertNotIn('Answer: -1',text); self.assertIn('first tested glucose lower bound',text)
    def test_new_results_report_keeps_historical_mission_title_pattern(self):
        text = simulation.build_mission36_fermentation_report_text(self.make_report())
        self.assertTrue(text.startswith('Mission 36 Oxygen-Capped Fermentation Onset\n\nControlled setup:'))
        self.assertNotIn('- Model:', text)
        self.assertIn('- Method: pFBA', text)
        self.assertIn('- Objective: BIOMASS_SC5_notrace', text)

    def test_mission_menu_report_title_is_contextual(self):
        text = simulation.build_mission36_fermentation_report_text(self.make_report(), include_title=False)
        self.assertFalse(text.startswith('Mission 36 Oxygen-Capped Fermentation Onset'))
        self.assertTrue(text.startswith('Controlled setup:'))
        source = (ROOT/'code'/'mission36.py').read_text()
        self.assertIn('report_include_title = bool(', source)
        self.assertIn('include_title=report_include_title', source)
        self.assertIn("'36' in self.missions_activated", source)

    def test_briefing_does_not_repeat_obvious_model_line(self):
        source = (ROOT/'code'/'mission36.py').read_text()
        self.assertNotIn('- Model: Yeast iMM904', source)

    def test_briefing_and_hint_keep_historical_green_theme_background(self):
        source = (ROOT/'code'/'mission36.py').read_text()
        briefing_start = source.index('briefing = pygame_menu.Menu')
        briefing_end = source.index("briefing.add.button('Back'", briefing_start)
        briefing_block = source[briefing_start:briefing_end]
        hint_start = source.index('hint3 = pygame_menu.Menu', briefing_end)
        hint_end = source.index("hint1.add.button('Back'", hint_start)
        hint_block = source[hint_start:hint_end]
        self.assertNotIn("background_color='white'", briefing_block)
        self.assertNotIn("background_color='white'", hint_block)

    def test_incomplete_current_version_baseline_is_not_treated_as_valid(self):
        report = simulation._mission36_empty_report()
        report['baseline'] = {'growth': 0.287866}
        refreshed = simulation._mission36_refresh_derived(report)
        self.assertFalse(refreshed['baseline_ready'])
        text = simulation.build_mission36_fermentation_report_text(refreshed)
        self.assertIn('Reference pending.', text)


    def _valid_sweep_menu(self):
        return {
            'execute_sweep': True,
            'sweep_variable': 'EX_glc__D_e:lower',
            'sweep_values': 'yeast_glucose_fermentation_threshold',
        }

    def test_invalid_adh1_sweep_is_recorded_as_rejected_without_erasing_evidence(self):
        existing = self.make_report()
        genes = {'YOL086C': False}
        with patch.object(simulation, 'load_mission36_fermentation_onset', return_value=existing), \
             patch.object(simulation, 'save_mission36_fermentation_onset') as save_report, \
             patch.object(simulation, '_read_simulation_model_id', return_value='yeast_iMM904'), \
             patch.object(simulation, '_read_simulation_file', return_value=('pFBA', 'BIOMASS_SC5_notrace', genes, {})), \
             patch.object(simulation, '_model_environment_is_default', return_value=True), \
             patch.object(simulation, '_read_selected_production_fluxes', return_value=['EX_etoh_e', 'EX_co2_e']):
            report = simulation.run_mission36_rejected_sweep_attempt(
                self._valid_sweep_menu(), 'pFBA', 'BIOMASS_SC5_notrace', genes,
                baseline_preexisting=True,
            )
        self.assertTrue(report['evidence_ready'])
        self.assertFalse(report['current_attempt_recorded'])
        self.assertFalse(report['latest_attempt']['recorded'])
        self.assertFalse(report['latest_attempt']['solver_executed'])
        self.assertTrue(any('wild type' in issue for issue in report['current_issues']))
        self.assertIsNotNone(report['baseline'])
        self.assertIsNotNone(report['glucose_curve'])
        text = simulation.build_mission36_fermentation_report_text(report)
        self.assertIn('Latest attempt was not recorded.', text)
        self.assertIn('Requested glucose curve was not executed.', text)
        self.assertIn('Previously valid Mission 36 evidence remains available.', text)
        self.assertIn('Evidence complete.', text)
        save_report.assert_called_once()

    def test_changed_environment_sweep_is_rejected_before_curve_execution(self):
        genes = {}
        with patch.object(simulation, '_read_simulation_model_id', return_value='yeast_iMM904'), \
             patch.object(simulation, '_read_simulation_file', return_value=('pFBA', 'BIOMASS_SC5_notrace', genes, {})), \
             patch.object(simulation, '_model_environment_is_default', return_value=False), \
             patch.object(simulation, '_read_selected_production_fluxes', return_value=['EX_etoh_e', 'EX_co2_e']):
            allowed, issues = simulation._mission36_sweep_precheck(
                self._valid_sweep_menu(), 'pFBA', 'BIOMASS_SC5_notrace', genes,
                baseline_preexisting=True,
            )
        self.assertFalse(allowed)
        self.assertTrue(any('environment completely model-default' in issue for issue in issues))

    def test_noop_default_environment_remains_valid_for_sweep(self):
        genes = {}
        with patch.object(simulation, '_read_simulation_model_id', return_value='yeast_iMM904'), \
             patch.object(simulation, '_read_simulation_file', return_value=('pFBA', 'BIOMASS_SC5_notrace', genes, {})), \
             patch.object(simulation, '_model_environment_is_default', return_value=True), \
             patch.object(simulation, '_read_selected_production_fluxes', return_value=['EX_etoh_e', 'EX_co2_e']):
            allowed, issues = simulation._mission36_sweep_precheck(
                self._valid_sweep_menu(), 'pFBA', 'BIOMASS_SC5_notrace', genes,
                baseline_preexisting=True,
            )
        self.assertTrue(allowed)
        self.assertEqual(issues, [])

    def test_invalid_text_input_blocks_sweep_and_becomes_visible_issue(self):
        genes = {}
        with patch.object(simulation, '_read_simulation_model_id', return_value='yeast_iMM904'), \
             patch.object(simulation, '_read_simulation_file', return_value=('pFBA', 'BIOMASS_SC5_notrace', genes, {})), \
             patch.object(simulation, '_model_environment_is_default', return_value=True), \
             patch.object(simulation, '_read_selected_production_fluxes', return_value=['EX_etoh_e', 'EX_co2_e']):
            allowed, issues = simulation._mission36_sweep_precheck(
                self._valid_sweep_menu(), 'pFBA', 'BIOMASS_SC5_notrace', genes,
                baseline_preexisting=True, input_errors=['Unknown gene id/name: BAD_GENE'],
            )
        self.assertFalse(allowed)
        self.assertTrue(any('BAD_GENE' in issue for issue in issues))

    def test_window_routes_rejected_requested_sweep_to_mission_report(self):
        source = (ROOT/'code'/'window.py').read_text()
        self.assertIn('mission36_sweep_explicitly_requested', source)
        self.assertIn('run_mission36_rejected_sweep_attempt(', source)
        self.assertIn('input_errors=mission36_input_errors', source)

    def test_answer_text_input_submits_on_enter_and_button_remains_available(self):
        source = (ROOT/'code'/'mission36.py').read_text()
        self.assertIn('onreturn=self.deliver_results', source)
        self.assertIn("'Deliver Interpretation', lambda: self.deliver_results(answer_input.get_value())", source)

    def test_state_is_json_serialisable(self):
        json.dumps(self.make_report())
    def test_unlock_requires_m35(self):
        self.assertFalse(simulation.is_mission36_unlocked(['34'])); self.assertTrue(simulation.is_mission36_unlocked(['35']))
    def test_wiring_uses_vale(self):
        level=(ROOT/'code'/'level.py').read_text(); player=(ROOT/'code'/'player.py').read_text(); self.assertIn("if obj.name == 'Vale':",level); self.assertIn("name == 'Vale'",player); self.assertIn('talk_36',level)
    def test_mission26_helpers_survive_model_aware_sweep_refactor(self):
        # Mission 36 generalises the historical Bound Sweep engine.  Keep the
        # Mission 26 helper block intact so older mission modules remain importable.
        required = [
            '_growth_values_from_rows',
            '_count_decreasing_steps',
            '_selected_fluxes_include',
            'is_mission26_unlocked',
            '_mission26_clean_number',
            '_mission26_number_or_none',
            '_mission26_value_key',
            '_mission26_base_environment_status',
        ]
        for name in required:
            self.assertTrue(hasattr(simulation, name), name)

    def test_map_is_not_required_to_change(self):
        self.assertTrue((ROOT/'graphics'/'dialogues'/'vale.jpg').exists())

if __name__=='__main__': unittest.main()
