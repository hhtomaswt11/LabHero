"""Regression tests for Mission 27 metabolic bypass rescue.

Run from the project root with:
    python3 tests/test_mission27.py
"""
from __future__ import annotations

import gzip
import inspect
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import simulation  # noqa: E402


class Mission27RegressionTests(unittest.TestCase):
    GROWTH = {
        'wild_type_reference': 0.873921507,
        'knockout_reference': 0.0,
        'EX_akg_e': 1.395438367,
        'EX_pyr_e': 0.0,
        'EX_succ_e': 0.0,
        'EX_fum_e': 0.0,
        'EX_mal__L_e': 0.0,
    }

    def _genes(self, knockout=False, extra=None):
        genes = simulation._build_active_genes_data()
        if knockout:
            genes[simulation.MISSION27_TARGET_GENE] = False
        for gene_id in extra or []:
            genes[gene_id] = False
        return genes

    def _reactions(self, candidate=None, *, extra_change=None, incomplete=False):
        reactions = simulation._build_default_reactions_data()
        if candidate:
            index = list(simulation.REACTIONS.index).index(candidate)
            reactions[f'reaction_{index}_lb'] = True
        if extra_change:
            reaction_id, bound = extra_change
            index = list(simulation.REACTIONS.index).index(reaction_id)
            key = f'reaction_{index}_{bound}'
            reactions[key] = not bool(reactions[key])
        if incomplete:
            reactions.pop(next(iter(reactions)))
        return reactions

    def _production(self, growth, *, diagnostics=None, biomass=None, error=None):
        total = 250.0 + float(growth) * 100.0
        result = {
            'selected_ids': [],
            'items': [],
            'biomass_raw': growth if biomass is None else biomass,
            'method_diagnostics': {
                'method': simulation.MISSION27_METHOD,
                'objective_reaction': simulation.MISSION27_GROWTH_OBJECTIVE,
                'primary_objective_flux': growth,
                'method_score': total,
                'method_score_name': simulation.MISSION27_EXPECTED_SCORE_NAME,
                'total_absolute_flux': total,
                'active_reaction_count': 40 if growth > 0 else 0,
            },
        }
        if diagnostics:
            result['method_diagnostics'].update(diagnostics)
        if error:
            result['error'] = error
        return result

    def _medium(self, run_key, *, candidate=None, missing=None, candidate_raw=None,
                glucose=None, oxygen=None, error=None):
        growth = self.GROWTH[run_key]
        if glucose is None:
            glucose = -10.0 if growth > 0 else 0.0
        if oxygen is None:
            if run_key == 'wild_type_reference':
                oxygen = -21.799493
            elif run_key == simulation.MISSION27_EXPECTED_RESCUE:
                oxygen = -39.003156
            else:
                oxygen = 0.0
        if candidate and candidate_raw is None:
            candidate_raw = -10.0 if candidate == simulation.MISSION27_EXPECTED_RESCUE else 0.0

        rows = [
            (simulation.MISSION27_GLUCOSE_REACTION, glucose),
            (simulation.MISSION27_OXYGEN_REACTION, oxygen),
        ]
        if candidate:
            rows.append((candidate, candidate_raw))
        items = []
        for reaction_id, raw in rows:
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
                objective_result=None, objective_error=None):
        candidate = run_key if run_key in simulation.MISSION27_CANDIDATE_SUPPLEMENTS else None
        knockout = run_key != 'wild_type_reference'
        growth = self.GROWTH[run_key]
        with patch.object(simulation, 'save_mission27_rescue_check'):
            return simulation._build_mission27_data(
                method or simulation.MISSION27_METHOD,
                objective or simulation.MISSION27_GROWTH_OBJECTIVE,
                growth if objective_result is None else objective_result,
                genes if genes is not None else self._genes(knockout),
                reactions if reactions is not None else self._reactions(candidate),
                production_fluxes=production if production is not None else self._production(growth),
                medium_fluxes=medium if medium is not None else self._medium(run_key, candidate=candidate),
                existing_report={} if existing is None else existing,
                objective_error=objective_error,
            )

    def _complete(self, order=None):
        order = order or [
            'wild_type_reference',
            'knockout_reference',
            *simulation.MISSION27_CANDIDATE_SUPPLEMENTS,
        ]
        report = {}
        for run_key in order:
            report = self._record(run_key, existing=report)
        return report

    def test_constants_and_progression(self):
        self.assertEqual(simulation.MISSION27_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION27_METHOD, 'pFBA')
        self.assertEqual(simulation.MISSION27_TARGET_GENE, 'b0720')
        self.assertEqual(simulation.MISSION27_TARGET_GENE_NAME, 'gltA')
        self.assertEqual(simulation.MISSION27_TARGET_REACTION, 'CS')
        self.assertEqual(simulation.MISSION27_EXPECTED_RESCUE, 'EX_akg_e')
        self.assertFalse(simulation.is_mission27_unlocked([]))
        self.assertFalse(simulation.is_mission27_unlocked(['25']))
        self.assertTrue(simulation.is_mission27_unlocked(['26']))

    def test_initial_state_contains_seven_missing_runs(self):
        with patch.object(simulation, 'save_mission27_rescue_check'):
            report = simulation.initialise_mission27_rescue_screen()
        self.assertEqual(report['recorded_run_count'], 0)
        self.assertEqual(report['required_run_count'], 7)
        self.assertEqual(len(report['missing_conditions']), 7)
        self.assertFalse(report['evidence_ready'])

    def test_seven_valid_runs_support_one_unique_rescue(self):
        report = self._complete()
        self.assertEqual(report['recorded_run_count'], 7)
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['unique_rescue_supported'])
        self.assertEqual(report['rescue_candidates'], ['EX_akg_e'])
        self.assertTrue(report['ready_to_deliver'])

    def test_runs_can_arrive_in_any_order(self):
        report = self._complete([
            'EX_mal__L_e', 'EX_akg_e', 'knockout_reference', 'EX_pyr_e',
            'wild_type_reference', 'EX_fum_e', 'EX_succ_e',
        ])
        self.assertTrue(report['unique_rescue_supported'])
        self.assertEqual(report['missing_conditions'], [])

    def test_six_runs_are_incomplete(self):
        report = {}
        for run_key in ['wild_type_reference', 'knockout_reference', *simulation.MISSION27_CANDIDATE_SUPPLEMENTS[:-1]]:
            report = self._record(run_key, existing=report)
        self.assertEqual(report['recorded_run_count'], 6)
        self.assertEqual(report['missing_conditions'], ['EX_mal__L_e'])
        self.assertFalse(report['evidence_ready'])

    def test_repeated_trial_replaces_without_duplication(self):
        report = self._complete()
        repeated = self._record('EX_akg_e', existing=report)
        self.assertEqual(repeated['recorded_run_count'], 7)
        self.assertEqual(repeated['current_candidate'], 'EX_akg_e')
        self.assertTrue(repeated['current_run_recorded'])

    def test_wrong_method_or_objective_is_rejected(self):
        self.assertFalse(self._record('wild_type_reference', method='FBA')['current_run_valid'])
        self.assertFalse(self._record('wild_type_reference', objective='EX_ac_e')['current_run_valid'])

    def test_wild_type_reference_requires_no_knockout(self):
        report = self._record('wild_type_reference', genes=self._genes(True))
        self.assertFalse(report['current_run_valid'])

    def test_knockout_reference_requires_exact_target_gene(self):
        wrong = self._record('knockout_reference', genes=self._genes(False, ['b3956']))
        self.assertFalse(wrong['current_run_valid'])
        two = self._record('knockout_reference', genes=self._genes(True, ['b3956']))
        self.assertFalse(two['current_run_valid'])

    def test_candidate_trial_requires_exact_target_gene(self):
        no_ko = self._record('EX_akg_e', genes=self._genes(False))
        self.assertFalse(no_ko['current_run_valid'])
        wrong = self._record('EX_akg_e', genes=self._genes(False, ['b3956']))
        self.assertFalse(wrong['current_run_valid'])

    def test_wild_type_with_supplement_is_not_a_valid_condition(self):
        report = self._record(
            'EX_akg_e',
            genes=self._genes(False),
        )
        self.assertFalse(report['current_run_valid'])

    def test_candidate_environment_requires_exactly_one_open_candidate(self):
        extra = self._reactions('EX_akg_e', extra_change=('EX_pyr_e', 'lb'))
        report = self._record('EX_akg_e', reactions=extra)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('exactly one', ' '.join(report['current_issues']))

    def test_non_candidate_environment_change_is_rejected(self):
        reactions = self._reactions(extra_change=('EX_nh4_e', 'lb'))
        report = self._record('knockout_reference', reactions=reactions)
        self.assertFalse(report['current_run_valid'])

    def test_environment_payload_can_be_reordered(self):
        reordered = dict(reversed(list(self._reactions('EX_akg_e').items())))
        report = self._record('EX_akg_e', reactions=reordered)
        self.assertTrue(report['current_run_valid'])

    def test_incomplete_environment_payload_is_rejected(self):
        report = self._record('wild_type_reference', reactions=self._reactions(incomplete=True))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('incomplete', ' '.join(report['current_issues']))

    def test_numeric_zero_growth_is_accepted_for_knockout_reference(self):
        report = self._record('knockout_reference', objective_result=0.0)
        self.assertTrue(report['current_run_valid'])
        self.assertEqual(report['knockout_reference']['growth'], 0.0)

    def test_infeasible_is_not_converted_to_zero(self):
        report = self._record('knockout_reference', objective_result='Status: INFEASIBLE')
        self.assertFalse(report['current_run_valid'])
        self.assertIn('infeasible result is not', ' '.join(report['current_issues']))

    def test_missing_exchange_evidence_is_rejected(self):
        medium = self._medium('EX_akg_e', candidate='EX_akg_e', missing='EX_akg_e')
        report = self._record('EX_akg_e', medium=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('candidate exchange evidence', ' '.join(report['current_issues']))

    def test_exchange_report_error_is_rejected(self):
        medium = self._medium('wild_type_reference', error='missing')
        report = self._record('wild_type_reference', medium=medium)
        self.assertFalse(report['current_run_valid'])

    def test_candidate_must_not_be_secreted(self):
        medium = self._medium('EX_akg_e', candidate='EX_akg_e', candidate_raw=2.0)
        report = self._record('EX_akg_e', medium=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('consumed rather than secreted', ' '.join(report['current_issues']))

    def test_candidate_uptake_cannot_exceed_capacity(self):
        medium = self._medium('EX_akg_e', candidate='EX_akg_e', candidate_raw=-11.0)
        report = self._record('EX_akg_e', medium=medium)
        self.assertFalse(report['current_run_valid'])

    def test_rescue_candidate_requires_measurable_uptake(self):
        medium = self._medium('EX_akg_e', candidate='EX_akg_e', candidate_raw=0.0)
        report = self._record('EX_akg_e', medium=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('measurably consumed', ' '.join(report['current_issues']))

    def test_wild_type_reference_requires_default_glucose_and_oxygen(self):
        low_glucose = self._medium('wild_type_reference', glucose=-5.0)
        self.assertFalse(self._record('wild_type_reference', medium=low_glucose)['current_run_valid'])
        no_oxygen = self._medium('wild_type_reference', oxygen=0.0)
        self.assertFalse(self._record('wild_type_reference', medium=no_oxygen)['current_run_valid'])

    def test_knockout_reference_must_show_no_growth(self):
        report = self._record('knockout_reference', objective_result=0.2,
                              production=self._production(0.2, biomass=0.2))
        self.assertFalse(report['current_run_valid'])

    def test_non_rescue_candidate_must_not_restore_growth(self):
        production = self._production(0.1, biomass=0.1)
        medium = self._medium('EX_pyr_e', candidate='EX_pyr_e')
        report = self._record('EX_pyr_e', objective_result=0.1, production=production, medium=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('unexpectedly restores', ' '.join(report['current_issues']))

    def test_zero_growth_non_rescue_allows_zero_candidate_uptake(self):
        report = self._record('EX_pyr_e')
        self.assertTrue(report['current_run_valid'])
        self.assertEqual(report['candidate_trials']['EX_pyr_e']['candidate_uptake'], 0.0)

    def test_target_reaction_must_remain_disabled(self):
        with patch.object(simulation, '_mission27_disabled_reactions', return_value=[]):
            report = self._record('EX_akg_e')
        self.assertFalse(report['current_run_valid'])
        self.assertIn('keep CS disabled', ' '.join(report['current_issues']))

    def test_production_diagnostics_are_required(self):
        report = self._record('wild_type_reference', production={'selected_ids': [], 'items': []})
        self.assertFalse(report['current_run_valid'])

    def test_method_and_objective_diagnostics_are_checked(self):
        production = self._production(self.GROWTH['wild_type_reference'], diagnostics={'method': 'FBA'})
        self.assertFalse(self._record('wild_type_reference', production=production)['current_run_valid'])
        production = self._production(self.GROWTH['wild_type_reference'], diagnostics={'objective_reaction': 'EX_ac_e'})
        self.assertFalse(self._record('wild_type_reference', production=production)['current_run_valid'])

    def test_primary_flux_and_biomass_must_match_visible_result(self):
        growth = self.GROWTH['wild_type_reference']
        production = self._production(growth, diagnostics={'primary_objective_flux': 0.5})
        self.assertFalse(self._record('wild_type_reference', production=production)['current_run_valid'])
        production = self._production(growth, biomass=0.5)
        self.assertFalse(self._record('wild_type_reference', production=production)['current_run_valid'])

    def test_pfba_secondary_score_is_checked(self):
        growth = self.GROWTH['wild_type_reference']
        production = self._production(growth, diagnostics={'method_score_name': 'primary_objective_flux'})
        self.assertFalse(self._record('wild_type_reference', production=production)['current_run_valid'])
        production = self._production(growth, diagnostics={'method_score': 999.0})
        self.assertFalse(self._record('wild_type_reference', production=production)['current_run_valid'])

    def test_invalid_attempt_preserves_complete_evidence(self):
        complete = self._complete()
        invalid = self._record('EX_akg_e', existing=complete, method='FBA')
        self.assertFalse(invalid['current_run_recorded'])
        self.assertEqual(invalid['recorded_run_count'], 7)
        self.assertTrue(invalid['evidence_ready'])
        self.assertTrue(invalid['unique_rescue_supported'])
        text = simulation.build_mission27_rescue_report_text(invalid)
        self.assertIn('Latest run was not recorded', text)
        self.assertIn('Previously valid Mission 27 rescue evidence remains available', text)

    def test_answer_aliases_are_accepted(self):
        report = self._complete()
        for answer in ('EX_akg_e', 'akg', '2-oxoglutarate', '2 oxoglutarate', '2OG', 'alpha-ketoglutarate', 'α-ketoglutarate'):
            with self.subTest(answer=answer):
                self.assertTrue(simulation.mission27_answer_matches(answer, report))

    def test_wrong_answers_are_rejected(self):
        report = self._complete()
        for answer in ('pyruvate', 'succinate', 'fumarate', 'malate', 'gltA', 'CS', ''):
            with self.subTest(answer=answer):
                self.assertFalse(simulation.mission27_answer_matches(answer, report))

    def test_report_exposes_evidence_without_explicit_answer_sentence(self):
        text = simulation.build_mission27_rescue_report_text(self._complete())
        self.assertIn('Evidence complete', text)
        self.assertIn('Which candidate exchange', text)
        self.assertNotIn('The answer is EX_akg_e', text)
        self.assertNotIn('Submit 2-Oxoglutarate', text)

    def test_report_state_is_json_serializable(self):
        json.dumps(self._complete())

    def test_validator_does_not_run_hidden_simulations(self):
        source = inspect.getsource(simulation._build_mission27_data)
        self.assertNotIn('simulate(', source)
        self.assertNotIn('_http_post_json', source)
        wrapper = inspect.getsource(simulation.run_mission27_rescue_check_remote)
        self.assertNotIn('_http_post_json', wrapper)

    def test_window_uses_visible_normal_simulation_not_bound_sweep(self):
        source = (CODE_DIR / 'window.py').read_text()
        self.assertIn('run_mission27_rescue_check(self.results)', source)
        self.assertIn('run_mission27_rescue_check_remote(BACKEND_URL, self.results)', source)
        active_block = source[source.index('bound_sweep_mission_active ='):source.index('menu_compare_runs =')]
        self.assertNotIn("('27' in self.player.missions_activated", active_block)
        self.assertNotIn('run_mission27_bound_sweep_check(bound_sweep_data)', source)

    def test_gene_menu_highlights_mission27_target(self):
        source = (CODE_DIR / 'window.py').read_text()
        self.assertIn("('27', [MISSION27_TARGET_GENE])", source)

    def test_ribeiro_ui_has_gating_activation_and_answer_guards(self):
        source = (CODE_DIR / 'mission27.py').read_text()
        self.assertIn('class Mission27:', source)
        self.assertIn('Dr. Ribeiro', source)
        self.assertIn('graphics/dialogues/ribeiro.jpg', source)
        self.assertIn('initialise_mission27_rescue_screen', source)
        self.assertIn('mission27_answer_matches', source)
        self.assertIn("if '27' not in self.missions_activated", source)
        self.assertNotIn('Dr. Luna', source)
        self.assertNotIn('Glucose Limitation Sweep', source)

    def test_level_player_and_map_wire_mission27_interaction(self):
        level = (CODE_DIR / 'level.py').read_text()
        player = (CODE_DIR / 'player.py').read_text()
        tmx = (PROJECT_ROOT / 'data' / 'map_lb.tmx').read_text()
        self.assertIn('from mission27 import Mission27', level)
        self.assertIn('talk_27 = self.toggle_talk_27', level)
        self.assertIn("if obj.name == 'Mission27'", level)
        self.assertIn('self.talk_27 = talk_27', player)
        self.assertIn("name == 'Mission27'", player)
        self.assertIn('name="Mission27"', tmx)

    def test_save_layer_has_dedicated_rescue_artifact(self):
        source = (CODE_DIR / 'save_load.py').read_text()
        self.assertIn('def save_mission27_rescue_check', source)
        self.assertIn('mission27_rescue_check.txt', source)
        self.assertIn('def clear_mission27_rescue_check', source)

    def test_documentation_matches_redesign(self):
        documentation = (PROJECT_ROOT / 'data' / 'missions' / 'mission27.md').read_text()
        self.assertIn('Dr. Ribeiro', documentation)
        self.assertIn('Metabolic Bypass Rescue', documentation)
        self.assertIn('b0720', documentation)
        self.assertIn('gltA', documentation)
        self.assertIn('EX_akg_e', documentation)
        self.assertNotIn('Dr. Luna', documentation)
        self.assertNotIn('-1000', documentation)

    def test_cs_gpr_is_single_b0720_gene(self):
        model_path = PROJECT_ROOT / 'data' / 'models' / 'e_coli_core.xml.gz'
        ns = {
            'sbml': 'http://www.sbml.org/sbml/level3/version1/core',
            'fbc': 'http://www.sbml.org/sbml/level3/version1/fbc/version2',
        }
        with gzip.open(model_path, 'rb') as handle:
            root = ET.parse(handle).getroot()
        reaction = next(
            item for item in root.findall('.//sbml:reaction', ns)
            if item.attrib.get('id') == 'R_CS'
        )
        refs = reaction.findall('.//fbc:geneProductRef', ns)
        self.assertEqual([item.attrib[f"{{{ns['fbc']}}}geneProduct"] for item in refs], ['G_b0720'])

    def test_independent_fba_growth_values_for_all_conditions(self):
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
        cs = reaction_index['R_CS']
        objective = np.zeros(len(reactions))
        objective[biomass] = -1.0
        conditions = [('wild_type_reference', None, False), ('knockout_reference', None, True)]
        conditions.extend((candidate, candidate, True) for candidate in simulation.MISSION27_CANDIDATE_SUPPLEMENTS)
        for key, candidate, knockout in conditions:
            with self.subTest(condition=key):
                current_bounds = list(bounds)
                if knockout:
                    current_bounds[cs] = (0.0, 0.0)
                if candidate:
                    idx = reaction_index['R_' + candidate]
                    current_bounds[idx] = (-10.0, current_bounds[idx][1])
                result = linprog(
                    objective,
                    A_eq=matrix,
                    b_eq=np.zeros(len(species)),
                    bounds=current_bounds,
                    method='highs',
                )
                self.assertTrue(result.success)
                self.assertAlmostEqual(result.x[biomass], self.GROWTH[key], delta=1e-6)

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
        for key in ('wild_type_reference', 'knockout_reference', *simulation.MISSION27_CANDIDATE_SUPPLEMENTS):
            candidate = key if key in simulation.MISSION27_CANDIDATE_SUPPLEMENTS else None
            env = {reaction: list(bounds) for reaction, bounds in default_env.items()}
            if candidate:
                env[candidate][0] = -10.0
            knockouts = [] if key == 'wild_type_reference' else [simulation.MISSION27_TARGET_GENE]
            response = backend_simulate(SimulateRequest(
                method=simulation.MISSION27_METHOD,
                objective=simulation.MISSION27_GROWTH_OBJECTIVE,
                gene_knockouts=knockouts,
                env_conditions=env,
            ))
            self.assertEqual(response.status, 'ok', response.message)
            self.assertAlmostEqual(float(response.primary_objective_flux), self.GROWTH[key], delta=1e-3)
            self.assertEqual(response.method_score_name, 'total_absolute_flux')
            self.assertAlmostEqual(float(response.fluxes[simulation.MISSION27_GROWTH_OBJECTIVE]), self.GROWTH[key], delta=1e-3)


if __name__ == '__main__':
    unittest.main()
