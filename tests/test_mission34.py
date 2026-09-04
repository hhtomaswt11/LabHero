"""Regression tests for Mission 34 Shared-Subunit Equivalence Audit.

Run from the project root with:
    python3 tests/test_mission34.py
"""
from __future__ import annotations

import gzip
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


class Mission34RegressionTests(unittest.TestCase):
    EXPECTED = {
        'wild_type': (0.873921507, 21.799493, 0.0, 518.422086, 48),
        'pdh_specific_single': (0.796695925, 21.303586, 7.743120, 532.796720, 50),
        'akgdh_specific_single': (0.858307408, 22.482010, 0.0, 531.461417, 48),
        'akgdh_same_complex_double': (0.858307408, 22.482010, 0.0, 531.461417, 48),
        'shared_subunit_single': (0.782351053, 21.910306, 7.783756, 556.281006, 50),
        'split_reaction_double': (0.782351053, 21.910306, 7.783756, 556.281006, 50),
    }

    def _genes(self, condition, *, extra=None, incomplete=False):
        genes = simulation._build_active_genes_data()
        for gene_id in simulation.MISSION34_CONDITION_GENES.get(condition, []):
            genes[gene_id] = False
        if extra:
            genes[extra] = False
        if incomplete:
            genes.pop(next(iter(genes)))
        return genes

    def _reactions(self, *, changed=None, incomplete=False):
        reactions = simulation._build_default_reactions_data()
        if changed:
            index = list(simulation.REACTIONS.index).index(changed)
            key = f'reaction_{index}_lb'
            reactions[key] = not reactions[key]
        if incomplete:
            reactions.pop(next(iter(reactions)))
        return reactions

    def _production(self, condition, *, diagnostics=None, missing=None, error=None):
        growth, _oxygen, _formate, total, active = self.EXPECTED[condition]
        method_diagnostics = {
            'method': simulation.MISSION34_METHOD,
            'objective_reaction': simulation.MISSION34_GROWTH_OBJECTIVE,
            'primary_objective_flux': growth,
            'method_score': total,
            'method_score_name': simulation.MISSION34_EXPECTED_SCORE_NAME,
            'total_absolute_flux': total,
            'active_reaction_count': active,
            'gpr_disabled_reactions': list(simulation.MISSION34_EXPECTED_DISABLED[condition]),
        }
        if diagnostics:
            method_diagnostics.update(diagnostics)
        if missing:
            method_diagnostics.pop(missing, None)
        result = {
            'selected_ids': [],
            'items': [],
            'objective_raw': growth,
            'biomass_raw': growth,
            'method_diagnostics': method_diagnostics,
        }
        if error:
            result['error'] = error
        return result

    def _medium(self, condition, *, missing=None, error=None):
        _growth, oxygen, formate, _total, _active = self.EXPECTED[condition]
        rows = [
            (simulation.MISSION34_GLUCOSE_REACTION, -10.0),
            (simulation.MISSION34_OXYGEN_REACTION, -oxygen),
            (simulation.MISSION34_FORMATE_REACTION, formate),
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
    ):
        growth = self.EXPECTED[condition][0]
        if objective_result is None:
            objective_result = growth
        if production is None:
            production = self._production(condition)
        if medium is None:
            medium = self._medium(condition)
        with patch.object(simulation, 'save_mission34_shared_subunit_check'):
            return simulation._build_mission34_data(
                method or simulation.MISSION34_METHOD,
                objective or simulation.MISSION34_GROWTH_OBJECTIVE,
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
        for condition in (order or simulation.MISSION34_CONDITION_ORDER):
            report = self._record(condition, existing=report)
        return report

    def test_constants_progression_and_protocol(self):
        self.assertEqual(simulation.MISSION34_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION34_METHOD, 'pFBA')
        self.assertEqual(simulation.MISSION34_GROWTH_OBJECTIVE, 'BIOMASS_Ecoli_core_w_GAM')
        self.assertEqual(simulation.MISSION34_REQUIRED_RUN_COUNT, 6)
        self.assertFalse(simulation.is_mission34_unlocked(['32']))
        self.assertTrue(simulation.is_mission34_unlocked(['33']))
        self.assertEqual(simulation.MISSION34_EXPECTED_DISABLED['shared_subunit_single'], ['AKGDH', 'PDH'])

    def test_initial_state_requires_six_conditions(self):
        with patch.object(simulation, 'save_mission34_shared_subunit_check'):
            report = simulation.initialise_mission34_shared_subunit_screen()
        self.assertEqual(report['recorded_run_count'], 0)
        self.assertEqual(report['missing_conditions'], simulation.MISSION34_CONDITION_ORDER)
        self.assertFalse(report['evidence_ready'])

    def test_exact_genotype_classification(self):
        for condition in simulation.MISSION34_CONDITION_ORDER:
            self.assertEqual(
                simulation._mission34_condition_for_knockouts(
                    simulation.MISSION34_CONDITION_GENES[condition]
                ),
                condition,
            )
        self.assertIsNone(simulation._mission34_condition_for_knockouts(['b0115']))
        self.assertIsNone(simulation._mission34_condition_for_knockouts(['b0114', 'b0116']))

    def test_complete_matrix_supports_both_equivalence_pairs(self):
        report = self._complete()
        self.assertEqual(report['recorded_run_count'], 6)
        self.assertEqual(report['missing_conditions'], [])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['same_complex_match_supported'])
        self.assertTrue(report['shared_vs_split_match_supported'])
        self.assertEqual(len(report['reaction_level_match_groups']), 2)
        self.assertTrue(report['answer_ready'])
        self.assertTrue(report['ready_to_deliver'])

    def test_any_order_and_repeat_update_without_duplication(self):
        report = self._complete(list(reversed(simulation.MISSION34_CONDITION_ORDER)))
        self.assertEqual(report['recorded_run_count'], 6)
        report = self._record('wild_type', existing=report)
        self.assertEqual(report['recorded_run_count'], 6)
        self.assertEqual(len(report['runs']), 6)

    def test_expected_reaction_sets_are_recorded(self):
        report = self._complete()
        for condition in simulation.MISSION34_CONDITION_ORDER:
            self.assertEqual(
                report['runs'][condition]['disabled_reactions'],
                simulation.MISSION34_EXPECTED_DISABLED[condition],
            )

    def test_same_complex_double_adds_no_reaction_closure(self):
        report = self._complete()
        single = report['runs']['akgdh_specific_single']
        double = report['runs']['akgdh_same_complex_double']
        self.assertTrue(simulation._mission34_pair_matches(single, double))
        self.assertEqual(single['disabled_reactions'], ['AKGDH'])
        self.assertEqual(double['disabled_reactions'], ['AKGDH'])

    def test_shared_single_matches_split_double(self):
        report = self._complete()
        shared = report['runs']['shared_subunit_single']
        split = report['runs']['split_reaction_double']
        self.assertTrue(simulation._mission34_pair_matches(shared, split))
        self.assertEqual(shared['disabled_reactions'], ['AKGDH', 'PDH'])
        self.assertEqual(shared['growth'], split['growth'])
        self.assertEqual(shared['total_absolute_flux'], split['total_absolute_flux'])

    def test_invalid_attempt_preserves_previous_evidence(self):
        report = self._record('wild_type')
        invalid = self._record('pdh_specific_single', existing=report, method='FBA')
        self.assertEqual(invalid['recorded_run_count'], 1)
        self.assertIsNotNone(invalid['runs']['wild_type'])
        self.assertIsNone(invalid['runs']['pdh_specific_single'])
        self.assertFalse(invalid['latest_attempt']['recorded'])
        self.assertIn('Use pFBA', ' '.join(invalid['current_issues']))

    def test_wrong_objective_environment_extra_gene_and_incomplete_payloads_rejected(self):
        cases = [
            {'objective': 'EX_ac_e'},
            {'reactions': self._reactions(changed=simulation.MISSION34_OXYGEN_REACTION)},
            {'genes': self._genes('wild_type', extra='b0978')},
            {'genes': self._genes('wild_type', incomplete=True)},
            {'reactions': self._reactions(incomplete=True)},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                report = self._record('wild_type', **kwargs)
                self.assertFalse(report['current_run_recorded'])

    def test_visible_gpr_payload_is_required_and_must_match(self):
        missing = self._production('pdh_specific_single', missing='gpr_disabled_reactions')
        report = self._record('pdh_specific_single', production=missing)
        self.assertFalse(report['current_run_recorded'])
        wrong = self._production(
            'pdh_specific_single',
            diagnostics={'gpr_disabled_reactions': ['AKGDH']},
        )
        report = self._record('pdh_specific_single', production=wrong)
        self.assertFalse(report['current_run_recorded'])
        self.assertIn('does not match', ' '.join(report['current_issues']))

    def test_missing_exchange_and_method_diagnostics_rejected(self):
        missing_formate = self._medium('pdh_specific_single', missing=simulation.MISSION34_FORMATE_REACTION)
        report = self._record('pdh_specific_single', medium=missing_formate)
        self.assertFalse(report['current_run_recorded'])
        missing_score = self._production('wild_type', missing='method_score')
        report = self._record('wild_type', production=missing_score)
        self.assertFalse(report['current_run_recorded'])

    def test_infeasible_is_not_converted_to_zero(self):
        report = self._record('wild_type', objective_result='Status: INFEASIBLE')
        self.assertFalse(report['current_run_recorded'])
        self.assertIn('INFEASIBLE', ' '.join(report['current_issues']))

    def test_pair_mismatch_blocks_answer_readiness(self):
        report = self._complete()
        altered = self._production(
            'split_reaction_double',
            diagnostics={'total_absolute_flux': 560.0, 'method_score': 560.0},
        )
        report = self._record('split_reaction_double', existing=report, production=altered)
        self.assertTrue(report['evidence_ready'])
        self.assertFalse(report['shared_vs_split_match_supported'])
        self.assertFalse(report['answer_ready'])

    def test_answers_are_short_and_reaction_level(self):
        report = self._complete()
        for answer in ('equivalent', 'equivalente', 'equivalentes', 'functionally equivalent', 'matching'):
            self.assertTrue(simulation.mission34_answer_matches(answer, report), answer)
        for answer in ('b0116', 'b0114+b0726', 'same genes', 'identical genotypes', 'shared', 'double'):
            self.assertFalse(simulation.mission34_answer_matches(answer, report), answer)

    def test_report_is_complete_but_does_not_reveal_answer(self):
        report = self._complete()
        text = simulation.build_mission34_shared_subunit_report_text(report)
        self.assertIn('Runs recorded: 6/6', text)
        self.assertIn('Evidence complete.', text)
        self.assertIn('What is their reaction-level relationship?', text)
        self.assertNotIn('The answer is equivalent', text)
        self.assertIn('No hidden validation simulation is used.', text)

    def test_state_is_json_serialisable(self):
        report = self._complete()
        encoded = json.dumps(report)
        self.assertIn('shared_vs_split_match_supported', encoded)

    def test_save_load_and_clear(self):
        report = self._complete()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(save_load, 'get_save_path', side_effect=lambda name: str(Path(tmp) / name)):
                save_load.save_mission34_shared_subunit_check(report)
                loaded = save_load.load_mission34_shared_subunit_check()
                self.assertEqual(loaded['recorded_run_count'], 6)
                save_load.clear_mission34_shared_subunit_check()
                self.assertIsNone(save_load.load_mission34_shared_subunit_check())

    def test_gpr_rules_in_active_sbml(self):
        model_path = PROJECT_ROOT / 'data' / 'models' / 'e_coli_core.xml.gz'
        with gzip.open(model_path, 'rb') as stream:
            root = ET.fromstring(stream.read())
        fbc = 'http://www.sbml.org/sbml/level3/version1/fbc/version2'
        core = 'http://www.sbml.org/sbml/level3/version1/core'
        ns = {'s': core, 'f': fbc}

        def genes_for(reaction_id):
            for reaction in root.findall('.//s:reaction', ns):
                rid = reaction.attrib.get('id', '')
                if rid in (reaction_id, f'R_{reaction_id}'):
                    assoc = reaction.find('./f:geneProductAssociation', ns)
                    return sorted(
                        ref.attrib.get(f'{{{fbc}}}geneProduct', '').replace('G_', '')
                        for ref in assoc.findall('.//f:geneProductRef', ns)
                    )
            return []

        self.assertEqual(genes_for('PDH'), ['b0114', 'b0115', 'b0116'])
        self.assertEqual(genes_for('AKGDH'), ['b0116', 'b0726', 'b0727'])

    def test_static_desktop_backend_and_dr_chen_integration(self):
        mission32 = (PROJECT_ROOT / 'code' / 'mission32.py').read_text()
        mission34 = (PROJECT_ROOT / 'code' / 'mission34.py').read_text()
        window = (PROJECT_ROOT / 'code' / 'window.py').read_text()
        simulation_source = (PROJECT_ROOT / 'code' / 'simulation.py').read_text()
        schema = (PROJECT_ROOT / 'backend' / 'app' / 'schemas.py').read_text()
        backend = (PROJECT_ROOT / 'backend' / 'app' / 'simulator.py').read_text()
        self.assertIn('from mission34 import Mission34_info', mission32)
        self.assertIn('self.menu34 = Mission34_info', mission32)
        self.assertIn("if '34' in self.missions_completed", mission32)
        self.assertIn('class Mission34_info', mission34)
        self.assertIn("('34', list(MISSION34_GENE_NAMES))", window)
        self.assertIn('run_mission34_shared_subunit_check', window)
        self.assertIn("label_id='mission34_shared_subunit_check'", window)
        self.assertIn("diagnostics['gpr_disabled_reactions']", simulation_source)
        self.assertIn('gpr_disabled_reactions: list[str] | None', schema)
        self.assertIn('gpr_disabled_reactions=sorted(disabled_reactions)', backend)

    def test_mission_document_exists_and_matches_current_title(self):
        mission_doc = PROJECT_ROOT / 'data' / 'missions' / 'mission34.md'
        self.assertTrue(mission_doc.exists())
        text = mission_doc.read_text(encoding='utf-8')
        self.assertIn('Mission 34 — Shared-Subunit Equivalence Audit', text)


if __name__ == '__main__':
    unittest.main()
