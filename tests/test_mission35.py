"""Regression tests for Mission 35 E. coli Final Systems Certification.

Run from the project root with:
    python3 tests/test_mission35.py
"""
from __future__ import annotations

import json
import sys
import types
import unittest
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

import progression  # noqa: E402
import save_load  # noqa: E402
import simulation  # noqa: E402
sys.platform = _original_platform


class Mission35RegressionTests(unittest.TestCase):
    DESIGN = {
        'wild_type': (0.873921507, 21.799493, 0.0, 0.0, 0.0, 518.422086, 48),
        'pdh_specific': (0.796695925, 21.303586, 7.743120, 0.0, 0.0, 532.796720, 50),
        'akgdh_specific': (0.858307408, 22.482010, 0.0, 0.0, 0.0, 531.461417, 48),
        'shared_subunit': (0.782351053, 21.910306, 7.783756, 0.0, 0.0, 556.281006, 50),
    }
    CURVES = {
        'pdh_specific': {
            -30.0: (0.796695925, 21.303586, 7.743120, 0.0, 0.0, 532.796720, 50),
            -10.0: (0.554383178, 10.0, 12.723248, 9.702700, 0.0, 384.931171, 54),
            -5.0: (0.391648451, 5.0, 15.937901, 12.231124, 1.816407, 344.364389, 51),
            -2.0: (0.283657150, 2.0, 17.057965, 9.994601, 5.694236, 335.967153, 51),
        },
        'shared_subunit': {
            -30.0: (0.782351053, 21.910306, 7.783756, 0.0, 0.0, 556.281006, 50),
            -10.0: (0.552180592, 10.0, 13.057348, 9.667315, 0.0, 385.583878, 54),
            -5.0: (0.391648451, 5.0, 15.937901, 12.231124, 1.816407, 344.364389, 51),
            -2.0: (0.283657150, 2.0, 17.057965, 9.994601, 5.694236, 335.967153, 51),
        },
    }

    def _genes(self, condition, *, extra=None, incomplete=False):
        genes = simulation._build_active_genes_data()
        for gene_id in simulation.MISSION35_DESIGN_GENES.get(condition, []):
            genes[gene_id] = False
        if extra:
            genes[extra] = False
        if incomplete:
            genes.pop(next(iter(genes)))
        return genes

    def _reactions(self, *, changed=None, incomplete=False):
        reactions = simulation._build_default_reactions_data()
        if changed:
            idx = list(simulation.REACTIONS.index).index(changed)
            reactions[f'reaction_{idx}_lb'] = not reactions[f'reaction_{idx}_lb']
        if incomplete:
            reactions.pop(next(iter(reactions)))
        return reactions

    def _design_production(self, condition, *, panel=None, disabled=None, missing_diag=None):
        growth, _o2, formate, acetate, ethanol, total, active = self.DESIGN[condition]
        selected = list(panel if panel is not None else simulation.MISSION35_REQUIRED_PRODUCTION_FLUXES)
        values = {
            simulation.MISSION35_FORMATE_REACTION: formate,
            simulation.MISSION35_ACETATE_REACTION: acetate,
            simulation.MISSION35_ETHANOL_REACTION: ethanol,
        }
        diagnostics = {
            'method': simulation.MISSION35_METHOD,
            'objective_reaction': simulation.MISSION35_GROWTH_OBJECTIVE,
            'primary_objective_flux': growth,
            'method_score': total,
            'method_score_name': 'total_absolute_flux',
            'total_absolute_flux': total,
            'active_reaction_count': active,
            'gpr_disabled_reactions': list(
                simulation.MISSION35_EXPECTED_DISABLED[condition]
                if disabled is None else disabled
            ),
        }
        if missing_diag:
            diagnostics.pop(missing_diag, None)
        return {
            'selected_ids': selected,
            'items': [
                {'reaction_id': rid, 'production_flux': values[rid]}
                for rid in selected if rid in values
            ],
            'objective_raw': growth,
            'biomass_raw': growth,
            'method_diagnostics': diagnostics,
        }

    def _medium(self, growth, oxygen, formate, acetate=0.0, ethanol=0.0, *, missing=None):
        raw = {
            simulation.MISSION35_GLUCOSE_REACTION: -10.0,
            simulation.MISSION35_OXYGEN_REACTION: -oxygen,
            simulation.MISSION35_FORMATE_REACTION: formate,
            simulation.MISSION35_ACETATE_REACTION: acetate,
            simulation.MISSION35_ETHANOL_REACTION: ethanol,
            simulation.MISSION35_GROWTH_OBJECTIVE: growth,
        }
        return {
            'items': [
                {
                    'reaction_id': rid,
                    'raw_flux': value,
                    'uptake_flux': max(-float(value), 0.0),
                    'secretion_flux': max(float(value), 0.0),
                }
                for rid, value in raw.items() if rid != missing
            ]
        }

    def _record_design(self, condition, existing=None, **kwargs):
        growth, o2, formate, acetate, ethanol, _total, _active = self.DESIGN[condition]
        with patch.object(simulation, 'save_mission35_final_certification'):
            return simulation._build_mission35_visible_run(
                kwargs.pop('method', simulation.MISSION35_METHOD),
                kwargs.pop('objective', simulation.MISSION35_GROWTH_OBJECTIVE),
                kwargs.pop('objective_result', growth),
                kwargs.pop('genes', self._genes(condition)),
                kwargs.pop('reactions', self._reactions()),
                kwargs.pop('production_fluxes', self._design_production(condition)),
                kwargs.pop('medium_fluxes', self._medium(growth, o2, formate, acetate, ethanol)),
                existing_report={} if existing is None else existing,
                objective_error=kwargs.pop('objective_error', None),
            )

    def _formate_production(self):
        return {
            'selected_ids': [],
            'items': [],
            'objective_raw': 40.0,
            'biomass_raw': 0.0,
            'method_diagnostics': {
                'method': simulation.MISSION35_METHOD,
                'objective_reaction': simulation.MISSION35_FORMATE_OBJECTIVE,
                'primary_objective_flux': 40.0,
                'method_score': 950.0,
                'method_score_name': 'total_absolute_flux',
                'total_absolute_flux': 950.0,
                'active_reaction_count': 34,
                'gpr_disabled_reactions': ['PDH'],
            },
        }

    def _record_formate_objective(self, existing, **kwargs):
        with patch.object(simulation, 'save_mission35_final_certification'):
            return simulation._build_mission35_visible_run(
                kwargs.pop('method', simulation.MISSION35_METHOD),
                kwargs.pop('objective', simulation.MISSION35_FORMATE_OBJECTIVE),
                kwargs.pop('objective_result', 40.0),
                kwargs.pop('genes', self._genes('pdh_specific')),
                kwargs.pop('reactions', self._reactions()),
                kwargs.pop('production_fluxes', self._formate_production()),
                kwargs.pop('medium_fluxes', self._medium(0.0, 40.0, 40.0)),
                existing_report=existing,
                objective_error=kwargs.pop('objective_error', None),
            )

    def _sweep(self, condition, **overrides):
        rows = []
        disabled = list(simulation.MISSION35_EXPECTED_DISABLED[condition])
        for bound in simulation.MISSION35_SWEEP_VALUES:
            growth, oxygen, formate, acetate, ethanol, total, active = self.CURVES[condition][bound]
            rows.append({
                'bound_value': bound,
                'status': 'ok',
                'growth_value': growth,
                'oxygen_uptake': oxygen,
                'exchange_uptake_fluxes': {
                    simulation.MISSION35_GLUCOSE_REACTION: 10.0,
                    simulation.MISSION35_OXYGEN_REACTION: oxygen,
                },
                'exchange_secretion_fluxes': {
                    simulation.MISSION35_FORMATE_REACTION: formate,
                    simulation.MISSION35_ACETATE_REACTION: acetate,
                    simulation.MISSION35_ETHANOL_REACTION: ethanol,
                },
                'method_diagnostics': {
                    'method': simulation.MISSION35_METHOD,
                    'objective_reaction': simulation.MISSION35_GROWTH_OBJECTIVE,
                    'primary_objective_flux': growth,
                    'method_score': total,
                    'method_score_name': 'total_absolute_flux',
                    'total_absolute_flux': total,
                    'active_reaction_count': active,
                    'gpr_disabled_reactions': disabled,
                },
            })
        data = {
            'method': simulation.MISSION35_METHOD,
            'objective': simulation.MISSION35_GROWTH_OBJECTIVE,
            'knocked_out_genes': list(simulation.MISSION35_DESIGN_GENES[condition]),
            'base_genes': self._genes(condition),
            'base_reactions': self._reactions(),
            'reaction_id': simulation.MISSION35_SWEEP_REACTION,
            'bound': simulation.MISSION35_SWEEP_BOUND,
            'preset': simulation.MISSION35_SWEEP_PRESET,
            'values': list(simulation.MISSION35_SWEEP_VALUES),
            'rows': rows,
        }
        data.update(overrides)
        return data

    def _record_curve(self, condition, existing, sweep=None):
        with patch.object(simulation, 'save_mission35_final_certification'):
            return simulation._build_mission35_curve_data(
                self._sweep(condition) if sweep is None else sweep,
                existing_report=existing,
            )

    def _complete(self):
        report = {}
        for condition in simulation.MISSION35_DESIGN_ORDER:
            report = self._record_design(condition, report)
        report = self._record_curve('shared_subunit', report)
        report = self._record_curve('pdh_specific', report)
        report = self._record_formate_objective(report)
        return report

    def test_protocol_constants_and_unlock(self):
        self.assertEqual(simulation.MISSION35_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION35_METHOD, 'pFBA')
        self.assertFalse(simulation.is_mission35_unlocked(['33']))
        self.assertTrue(simulation.is_mission35_unlocked(['34']))
        self.assertEqual(simulation.MISSION35_SWEEP_VALUES, [-30.0, -10.0, -5.0, -2.0])

    def test_progression_rewards_are_derived_from_mission_35(self):
        self.assertFalse(progression.is_skin_unlocked('golden', ['34']))
        self.assertFalse(progression.is_area_unlocked('golden_lab', ['34']))
        self.assertFalse(progression.is_model_unlocked('yeast_iMM904', ['34']))
        self.assertTrue(progression.is_skin_unlocked('golden', ['35']))
        rewards = progression.mission35_reward_state(['35'])
        self.assertTrue(all(rewards.values()))
        json.dumps(rewards)

    def test_initial_report_has_three_incomplete_sections(self):
        with patch.object(simulation, 'save_mission35_final_certification'):
            report = simulation.initialise_mission35_final_certification()
        self.assertEqual(report['design_recorded_count'], 0)
        self.assertEqual(report['curve_recorded_count'], 0)
        self.assertFalse(report['objective_audit_ready'])
        self.assertFalse(report['ready_to_deliver'])

    def test_design_screen_records_all_four_in_any_order(self):
        report = {}
        for condition in reversed(simulation.MISSION35_DESIGN_ORDER):
            report = self._record_design(condition, report)
        self.assertEqual(report['design_recorded_count'], 4)
        self.assertTrue(report['design_screen_ready'])
        self.assertEqual(report['unique_approved_target'], 'PDH')
        self.assertEqual(report['eligible_design_conditions'], ['pdh_specific'])

    def test_design_criteria_are_derived_not_gene_hardcoded(self):
        report = {}
        for condition in simulation.MISSION35_DESIGN_ORDER:
            report = self._record_design(condition, report)
        self.assertGreaterEqual(report['design_screen']['pdh_specific']['formate_secretion'], 7.5)
        self.assertGreaterEqual(report['design_screen']['pdh_specific']['growth_retention'], 0.90)
        self.assertLess(report['design_screen']['shared_subunit']['growth_retention'], 0.90)
        self.assertEqual(report['unique_approved_target'], report['design_screen']['pdh_specific']['disabled_reactions'][0])

    def test_design_requires_exact_production_panel(self):
        bad = self._design_production('pdh_specific', panel=['EX_for_e'])
        report = self._record_design('pdh_specific', production_fluxes=bad)
        self.assertFalse(report['current_attempt_recorded'])
        self.assertIn('Select exactly EX_for_e, EX_ac_e and EX_etoh_e', ' '.join(report['current_issues']))

    def test_design_rejects_wrong_method_objective_environment_and_genotype(self):
        self.assertFalse(self._record_design('wild_type', method='FBA')['current_attempt_recorded'])
        self.assertFalse(self._record_design('wild_type', objective='EX_succ_e')['current_attempt_recorded'])
        self.assertFalse(self._record_design('wild_type', reactions=self._reactions(changed='EX_o2_e'))['current_attempt_recorded'])
        self.assertFalse(self._record_design('wild_type', genes=self._genes('wild_type', extra='b0115'))['current_attempt_recorded'])

    def test_design_rejects_incomplete_gene_payload_and_wrong_gpr(self):
        self.assertFalse(self._record_design('pdh_specific', genes=self._genes('pdh_specific', incomplete=True))['current_attempt_recorded'])
        prod = self._design_production('pdh_specific', disabled=['AKGDH'])
        self.assertFalse(self._record_design('pdh_specific', production_fluxes=prod)['current_attempt_recorded'])

    def test_repeat_updates_without_duplication(self):
        report = self._record_design('wild_type')
        report = self._record_design('wild_type', report)
        self.assertEqual(report['design_recorded_count'], 1)

    def test_formate_objective_records_zero_biomass_as_numeric_not_missing(self):
        report = self._record_design('pdh_specific')
        report = self._record_formate_objective(report)
        audit = report['objective_audit']['formate_optimum']
        self.assertEqual(audit['formate_objective_flux'], 40.0)
        self.assertEqual(audit['biomass_flux'], 0.0)
        self.assertFalse(report['product_optimum_growth_compatible'])

    def test_formate_objective_requires_b0114_and_pdh_only(self):
        report = self._record_design('pdh_specific')
        bad = self._record_formate_objective(report, genes=self._genes('shared_subunit'))
        self.assertFalse(bad['current_attempt_recorded'])

    def test_formate_missing_biomass_is_not_zero(self):
        report = self._record_design('pdh_specific')
        prod = self._formate_production()
        prod['biomass_raw'] = None
        bad = self._record_formate_objective(report, production_fluxes=prod)
        self.assertFalse(bad['current_attempt_recorded'])
        self.assertIn('missing biomass is not zero', ' '.join(bad['current_issues']))

    def test_curve_records_exact_four_rows(self):
        report = self._record_curve('pdh_specific', {})
        self.assertTrue(report['current_attempt_recorded'])
        self.assertEqual(report['curve_recorded_count'], 1)
        self.assertEqual(len(report['oxygen_curves']['pdh_specific']['rows']), 4)

    def test_curve_requires_dedicated_preset_and_exact_values(self):
        bad = self._sweep('pdh_specific', preset='pfk_redundancy_threshold')
        self.assertFalse(self._record_curve('pdh_specific', {}, bad)['current_attempt_recorded'])
        bad = self._sweep('pdh_specific', values=[-30.0, -10.0, -5.0])
        self.assertFalse(self._record_curve('pdh_specific', {}, bad)['current_attempt_recorded'])

    def test_curve_rejects_changed_base_environment(self):
        bad = self._sweep('pdh_specific', base_reactions=self._reactions(changed='EX_o2_e'))
        self.assertFalse(self._record_curve('pdh_specific', {}, bad)['current_attempt_recorded'])

    def test_curve_rejects_infeasible_row_and_missing_gpr(self):
        bad = self._sweep('pdh_specific')
        bad['rows'][2]['status'] = 'infeasible'
        self.assertFalse(self._record_curve('pdh_specific', {}, bad)['current_attempt_recorded'])
        bad = self._sweep('pdh_specific')
        bad['rows'][1]['method_diagnostics'].pop('gpr_disabled_reactions')
        self.assertFalse(self._record_curve('pdh_specific', {}, bad)['current_attempt_recorded'])

    def test_two_curves_derive_first_sustained_convergence_as_minus_five(self):
        report = self._record_curve('pdh_specific', {})
        report = self._record_curve('shared_subunit', report)
        self.assertTrue(report['oxygen_curves_ready'])
        self.assertEqual(report['matching_bounds'], [-5.0, -2.0])
        self.assertEqual(report['first_convergence_bound'], -5.0)
        self.assertTrue(report['phenotype_convergence_supported'])

    def test_curve_mechanism_must_remain_distinct(self):
        report = self._record_curve('pdh_specific', {})
        second = self._sweep('shared_subunit')
        for row in second['rows']:
            row['method_diagnostics']['gpr_disabled_reactions'] = ['PDH']
        bad = self._record_curve('shared_subunit', report, second)
        self.assertFalse(bad['current_attempt_recorded'])

    def test_sweep_trigger_only_for_final_preset_and_curve_genotypes(self):
        menu = {'sweep_variable': [('Oxygen', 'EX_o2_e:lower')], 'sweep_values': [('Final', 'final_oxygen_convergence')]}
        self.assertTrue(simulation.mission35_should_run_bound_sweep(menu, 'pFBA', simulation.MISSION35_GROWTH_OBJECTIVE, self._genes('pdh_specific')))
        self.assertTrue(simulation.mission35_should_run_bound_sweep(menu, 'pFBA', simulation.MISSION35_GROWTH_OBJECTIVE, self._genes('shared_subunit')))
        self.assertFalse(simulation.mission35_should_run_bound_sweep(menu, 'pFBA', simulation.MISSION35_GROWTH_OBJECTIVE, self._genes('wild_type')))
        self.assertFalse(simulation.mission35_should_run_bound_sweep(menu, 'FBA', simulation.MISSION35_GROWTH_OBJECTIVE, self._genes('pdh_specific')))

    def test_complete_dossier_is_ready(self):
        report = self._complete()
        self.assertTrue(report['design_screen_ready'])
        self.assertTrue(report['oxygen_curves_ready'])
        self.assertTrue(report['objective_audit_ready'])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['ready_to_deliver'])
        self.assertEqual(report['unique_approved_target'], 'PDH')
        self.assertEqual(report['first_convergence_bound'], -5.0)
        self.assertFalse(report['product_optimum_growth_compatible'])

    def test_invalid_attempt_preserves_completed_evidence(self):
        report = self._complete()
        bad = self._record_design('wild_type', report, method='FBA')
        self.assertFalse(bad['current_attempt_recorded'])
        self.assertEqual(bad['design_recorded_count'], 4)
        self.assertEqual(bad['curve_recorded_count'], 2)
        self.assertTrue(bad['evidence_ready'])
        self.assertIsNotNone(bad['objective_audit']['formate_optimum'])

    def test_answers_are_short_and_evidence_derived(self):
        report = self._complete()
        self.assertTrue(simulation.mission35_answers_match('PDH', '-5', 'no', report))
        self.assertTrue(simulation.mission35_answers_match('pyruvate dehydrogenase', '-5,0', 'não', report))
        self.assertFalse(simulation.mission35_answers_match('b0114', '-5', 'no', report))
        self.assertFalse(simulation.mission35_answers_match('PDH', '-10', 'no', report))
        self.assertFalse(simulation.mission35_answers_match('PDH', '-5', 'yes', report))

    def test_answers_are_blocked_before_complete_evidence(self):
        report = self._record_design('pdh_specific')
        self.assertFalse(simulation.mission35_answers_match('PDH', '-5', 'no', report))

    def test_final_report_does_not_print_explicit_answer_instructions(self):
        text = simulation.build_mission35_final_certification_report_text(self._complete())
        self.assertIn('Final dossier evidence complete.', text)
        self.assertNotIn('The answer is PDH', text)
        self.assertNotIn('Submit -5', text)
        self.assertNotIn('Answer: no', text)

    def test_report_is_json_serialisable(self):
        json.dumps(self._complete())

    def test_save_load_round_trip_in_web_memstore(self):
        report = self._complete()
        old = save_load._IS_WEB
        try:
            save_load._IS_WEB = True
            save_load.clear_mission35_final_certification()
            save_load.save_mission35_final_certification(report)
            loaded = save_load.load_mission35_final_certification()
            self.assertEqual(loaded['first_convergence_bound'], -5.0)
            save_load.clear_mission35_final_certification()
            self.assertIsNone(save_load.load_mission35_final_certification())
        finally:
            save_load._IS_WEB = old

    def test_static_integration_final_npc_richter_and_golden_skin(self):
        level = (PROJECT_ROOT / 'code' / 'level.py').read_text()
        player = (PROJECT_ROOT / 'code' / 'player.py').read_text()
        mission35 = (PROJECT_ROOT / 'code' / 'mission35.py').read_text()
        skins = (PROJECT_ROOT / 'code' / 'skins.py').read_text()
        self.assertIn("obj.name == 'Final'", level)
        self.assertIn('talk_35 = self.toggle_talk_35', level)
        self.assertIn("name == 'Final'", player)
        self.assertIn("graphics/dialogues/richter.jpg", mission35)
        self.assertIn("id='golden'", skins)
        self.assertIn("graphics/character_golden", skins)

    def test_window_contains_final_sweep_preset_and_mission35_report(self):
        window = (PROJECT_ROOT / 'code' / 'window.py').read_text()
        self.assertIn("'final_oxygen_convergence'", window)
        self.assertIn('mission35_should_run_bound_sweep', window)
        self.assertIn('run_mission35_oxygen_curve_check', window)
        self.assertIn("label_id='mission35_final_certification'", window)


if __name__ == '__main__':
    unittest.main()
