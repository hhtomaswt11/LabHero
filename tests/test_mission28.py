"""Regression tests for Mission 28 bypass dependency mapping.

Run from the project root with:
    python3 tests/test_mission28.py
"""
from __future__ import annotations

import gzip
import inspect
import json
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


class Mission28RegressionTests(unittest.TestCase):
    GROWTH = {
        'rescue_reference': 1.395438367,
        'b2587': 0.0,
        'b1761': 1.348117979,
        'b0728': 1.345443913,
        'b3236': 1.321580869,
        'b3403': 1.354106260,
    }

    def _genes(self, secondary=None, extras=None, include_primary=True):
        genes = simulation._build_active_genes_data()
        if include_primary:
            genes[simulation.MISSION28_PRIMARY_GENE] = False
        if secondary:
            genes[secondary] = False
        for gene_id in extras or []:
            genes[gene_id] = False
        return genes

    def _reactions(self, *, supplement=True, extra_change=None, incomplete=False):
        reactions = simulation._build_default_reactions_data()
        if supplement:
            index = list(simulation.REACTIONS.index).index(simulation.MISSION28_RESCUE_SUPPLEMENT)
            reactions[f'reaction_{index}_lb'] = True
        if extra_change:
            reaction_id, bound = extra_change
            index = list(simulation.REACTIONS.index).index(reaction_id)
            key = f'reaction_{index}_{bound}'
            reactions[key] = not bool(reactions[key])
        if incomplete:
            reactions.pop(next(iter(reactions)))
        return reactions

    def _disabled(self, secondary=None):
        disabled = [simulation.MISSION28_PRIMARY_REACTION]
        if secondary:
            disabled.append(simulation.MISSION28_SECONDARY_REACTIONS[secondary])
        return sorted(disabled)

    def _production(self, growth, *, diagnostics=None, biomass=None, error=None):
        total = 400.0 + float(growth) * 300.0
        result = {
            'selected_ids': [],
            'items': [],
            'biomass_raw': growth if biomass is None else biomass,
            'method_diagnostics': {
                'method': simulation.MISSION28_METHOD,
                'objective_reaction': simulation.MISSION28_GROWTH_OBJECTIVE,
                'primary_objective_flux': growth,
                'method_score': total,
                'method_score_name': simulation.MISSION28_EXPECTED_SCORE_NAME,
                'total_absolute_flux': total,
                'active_reaction_count': 48 if growth > 0 else 27,
            },
        }
        if diagnostics:
            result['method_diagnostics'].update(diagnostics)
        if error:
            result['error'] = error
        return result

    def _medium(self, run_key, *, missing=None, supplement_raw=None,
                glucose=None, oxygen=None, error=None):
        dependency = run_key == simulation.MISSION28_EXPECTED_DEPENDENCY
        if glucose is None:
            glucose = -0.932 if dependency else -10.0
        if oxygen is None:
            oxygen = -1.864 if dependency else -39.0
        if supplement_raw is None:
            supplement_raw = 0.0 if dependency else -10.0
        rows = [
            (simulation.MISSION27_GLUCOSE_REACTION, glucose),
            (simulation.MISSION27_OXYGEN_REACTION, oxygen),
            (simulation.MISSION28_RESCUE_SUPPLEMENT, supplement_raw),
        ]
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
                objective_result=None, objective_error=None, mission27_report=None):
        secondary = None if run_key == 'rescue_reference' else run_key
        growth = self.GROWTH[run_key]
        with (
            patch.object(simulation, 'save_mission28_dependency_check'),
            patch.object(simulation, '_mission28_disabled_reactions', return_value=self._disabled(secondary)),
        ):
            return simulation._build_mission28_data(
                method or simulation.MISSION28_METHOD,
                objective or simulation.MISSION28_GROWTH_OBJECTIVE,
                growth if objective_result is None else objective_result,
                genes if genes is not None else self._genes(secondary),
                reactions if reactions is not None else self._reactions(),
                production_fluxes=production if production is not None else self._production(growth),
                medium_fluxes=medium if medium is not None else self._medium(run_key),
                existing_report={} if existing is None else existing,
                mission27_report=mission27_report,
                objective_error=objective_error,
            )

    def _complete(self, order=None):
        order = order or ['rescue_reference', *simulation.MISSION28_SECONDARY_GENES]
        report = {}
        for run_key in order:
            report = self._record(run_key, existing=report)
        return report

    def _mission27_report(self):
        return {
            'mission_id': '27',
            'check_version': simulation.MISSION27_CHECK_VERSION,
            'evidence_ready': True,
            'unique_rescue_supported': True,
            'candidate_trials': {
                simulation.MISSION28_RESCUE_SUPPLEMENT: {
                    'method': simulation.MISSION28_METHOD,
                    'objective': simulation.MISSION28_GROWTH_OBJECTIVE,
                    'growth': self.GROWTH['rescue_reference'],
                    'candidate_uptake': 10.0,
                    'candidate_raw_flux': -10.0,
                    'glucose_raw_flux': -10.0,
                    'glucose_uptake': 10.0,
                    'oxygen_raw_flux': -39.0,
                    'oxygen_uptake': 39.0,
                    'knocked_out_genes': [simulation.MISSION28_PRIMARY_GENE],
                    'disabled_reactions': [simulation.MISSION28_PRIMARY_REACTION],
                    'target_reaction_disabled': True,
                    'environment_changes': [f'{simulation.MISSION28_RESCUE_SUPPLEMENT} lower'],
                    'method_diagnostics': {
                        'method': simulation.MISSION28_METHOD,
                        'objective_reaction': simulation.MISSION28_GROWTH_OBJECTIVE,
                        'primary_objective_flux': self.GROWTH['rescue_reference'],
                        'method_score': 875.0,
                        'method_score_name': simulation.MISSION28_EXPECTED_SCORE_NAME,
                        'total_absolute_flux': 875.0,
                        'active_reaction_count': 48,
                    },
                }
            },
        }

    def test_constants_and_progression(self):
        self.assertEqual(simulation.MISSION28_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION28_METHOD, 'pFBA')
        self.assertEqual(simulation.MISSION28_PRIMARY_GENE, 'b0720')
        self.assertEqual(simulation.MISSION28_RESCUE_SUPPLEMENT, 'EX_akg_e')
        self.assertEqual(simulation.MISSION28_EXPECTED_DEPENDENCY, 'b2587')
        self.assertFalse(simulation.is_mission28_unlocked([]))
        self.assertFalse(simulation.is_mission28_unlocked(['26']))
        self.assertTrue(simulation.is_mission28_unlocked(['27']))

    def test_initial_state_can_import_mission27_reference(self):
        with patch.object(simulation, 'save_mission28_dependency_check'):
            report = simulation.initialise_mission28_dependency_screen(self._mission27_report())
        self.assertEqual(report['recorded_run_count'], 1)
        self.assertTrue(report['reference_imported_from_mission27'])
        self.assertNotIn('rescue_reference', report['missing_conditions'])
        self.assertEqual(len(report['missing_conditions']), 5)

    def test_initial_state_without_valid_import_needs_six_runs(self):
        with patch.object(simulation, 'save_mission28_dependency_check'):
            report = simulation.initialise_mission28_dependency_screen({})
        self.assertEqual(report['recorded_run_count'], 0)
        self.assertEqual(report['required_run_count'], 6)
        self.assertIn('rescue_reference', report['missing_conditions'])

    def test_reference_import_rejects_incomplete_mission27_evidence(self):
        report = self._mission27_report()
        report['evidence_ready'] = False
        self.assertIsNone(simulation._mission28_reference_from_mission27(report))

    def test_six_valid_runs_support_one_unique_dependency(self):
        report = self._complete()
        self.assertEqual(report['recorded_run_count'], 6)
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['unique_transport_dependency_supported'])
        self.assertEqual(report['dependency_candidates'], ['b2587'])
        self.assertEqual(report['unique_dependency_candidate'], 'b2587')
        self.assertTrue(report['ready_to_deliver'])

    def test_trials_can_arrive_in_any_order(self):
        report = self._complete(['b3236', 'b2587', 'rescue_reference', 'b3403', 'b1761', 'b0728'])
        self.assertTrue(report['unique_transport_dependency_supported'])
        self.assertEqual(report['missing_conditions'], [])

    def test_imported_reference_allows_only_five_new_runs(self):
        with patch.object(simulation, 'save_mission28_dependency_check'):
            report = simulation.initialise_mission28_dependency_screen(self._mission27_report())
        for candidate in simulation.MISSION28_SECONDARY_GENES:
            report = self._record(candidate, existing=report)
        self.assertEqual(report['recorded_run_count'], 6)
        self.assertTrue(report['evidence_ready'])

    def test_five_runs_are_incomplete_without_last_candidate(self):
        report = {}
        for run_key in ['rescue_reference', *simulation.MISSION28_SECONDARY_GENES[:-1]]:
            report = self._record(run_key, existing=report)
        self.assertEqual(report['recorded_run_count'], 5)
        self.assertEqual(report['missing_conditions'], ['b3403'])
        self.assertFalse(report['evidence_ready'])

    def test_repeated_trial_replaces_without_duplication(self):
        report = self._complete()
        repeated = self._record('b1761', existing=report)
        self.assertEqual(repeated['recorded_run_count'], 6)
        self.assertEqual(repeated['current_candidate'], 'b1761')
        self.assertTrue(repeated['current_run_recorded'])

    def test_wrong_method_or_objective_is_rejected(self):
        self.assertFalse(self._record('rescue_reference', method='FBA')['current_run_valid'])
        self.assertFalse(self._record('rescue_reference', objective='EX_ac_e')['current_run_valid'])

    def test_reference_requires_exact_primary_knockout(self):
        no_ko = self._record('rescue_reference', genes=self._genes(include_primary=False))
        self.assertFalse(no_ko['current_run_valid'])
        extra = self._record('rescue_reference', genes=self._genes(extras=['b3956']))
        self.assertFalse(extra['current_run_valid'])

    def test_trial_requires_primary_plus_one_listed_secondary_gene(self):
        only_primary = self._record('b2587', genes=self._genes())
        self.assertFalse(only_primary['current_run_valid'])
        wrong = self._record('b2587', genes=self._genes('b3956'))
        self.assertFalse(wrong['current_run_valid'])
        three = self._record('b2587', genes=self._genes('b2587', extras=['b1761']))
        self.assertFalse(three['current_run_valid'])

    def test_rescue_supplement_must_be_open(self):
        report = self._record('rescue_reference', reactions=self._reactions(supplement=False))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('2-oxoglutarate rescue supplement', ' '.join(report['current_issues']).lower())

    def test_additional_environment_change_is_rejected(self):
        reactions = self._reactions(extra_change=('EX_pyr_e', 'lb'))
        report = self._record('b2587', reactions=reactions)
        self.assertFalse(report['current_run_valid'])

    def test_environment_payload_can_be_reordered(self):
        reordered = dict(reversed(list(self._reactions().items())))
        report = self._record('rescue_reference', reactions=reordered)
        self.assertTrue(report['current_run_valid'])

    def test_incomplete_environment_payload_is_rejected(self):
        report = self._record('rescue_reference', reactions=self._reactions(incomplete=True))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('incomplete', ' '.join(report['current_issues']))

    def test_primary_reaction_must_remain_disabled(self):
        with (
            patch.object(simulation, 'save_mission28_dependency_check'),
            patch.object(simulation, '_mission28_disabled_reactions', return_value=[]),
        ):
            report = simulation._build_mission28_data(
                simulation.MISSION28_METHOD,
                simulation.MISSION28_GROWTH_OBJECTIVE,
                self.GROWTH['rescue_reference'],
                self._genes(), self._reactions(),
                production_fluxes=self._production(self.GROWTH['rescue_reference']),
                medium_fluxes=self._medium('rescue_reference'),
                existing_report={},
            )
        self.assertFalse(report['current_run_valid'])

    def test_secondary_reaction_must_be_disabled_by_gpr(self):
        with (
            patch.object(simulation, 'save_mission28_dependency_check'),
            patch.object(simulation, '_mission28_disabled_reactions', return_value=['CS']),
        ):
            report = simulation._build_mission28_data(
                simulation.MISSION28_METHOD,
                simulation.MISSION28_GROWTH_OBJECTIVE,
                self.GROWTH['b1761'],
                self._genes('b1761'), self._reactions(),
                production_fluxes=self._production(self.GROWTH['b1761']),
                medium_fluxes=self._medium('b1761'),
                existing_report={},
            )
        self.assertFalse(report['current_run_valid'])
        self.assertIn('expected candidate reaction', ' '.join(report['current_issues']))

    def test_numeric_zero_is_accepted_for_dependency_trial(self):
        report = self._record('b2587', objective_result=0.0)
        self.assertTrue(report['current_run_valid'])
        self.assertEqual(report['secondary_trials']['b2587']['growth'], 0.0)

    def test_infeasible_is_not_converted_to_zero(self):
        report = self._record('b2587', objective_result='Status: INFEASIBLE')
        self.assertFalse(report['current_run_valid'])
        self.assertIn('infeasible result is not', ' '.join(report['current_issues']))

    def test_missing_exchange_evidence_is_rejected(self):
        report = self._record('b1761', medium=self._medium('b1761', missing='EX_akg_e'))
        self.assertFalse(report['current_run_valid'])
        self.assertIn('2-oxoglutarate exchange evidence', ' '.join(report['current_issues']))

    def test_non_numeric_exchange_evidence_is_rejected(self):
        medium = self._medium('b1761')
        medium['items'][2]['uptake_flux'] = None
        report = self._record('b1761', medium=medium)
        self.assertFalse(report['current_run_valid'])
        self.assertIn('exchange evidence', ' '.join(report['current_issues']))

    def test_supplement_secretion_is_rejected(self):
        report = self._record('b1761', medium=self._medium('b1761', supplement_raw=1.0))
        self.assertFalse(report['current_run_valid'])

    def test_supplement_capacity_above_ten_is_rejected(self):
        report = self._record('b1761', medium=self._medium('b1761', supplement_raw=-11.0))
        self.assertFalse(report['current_run_valid'])

    def test_reference_requires_positive_growth_and_uptake(self):
        low_growth = self._record('rescue_reference', objective_result=0.0)
        self.assertFalse(low_growth['current_run_valid'])
        no_uptake = self._record('rescue_reference', medium=self._medium('rescue_reference', supplement_raw=0.0))
        self.assertFalse(no_uptake['current_run_valid'])

    def test_dependency_candidate_requires_growth_and_uptake_collapse(self):
        growth = self._record('b2587', objective_result=0.2, production=self._production(0.2))
        self.assertFalse(growth['current_run_valid'])
        uptake = self._record('b2587', medium=self._medium('b2587', supplement_raw=-1.0))
        self.assertFalse(uptake['current_run_valid'])

    def test_control_candidates_retain_over_ninety_percent_growth(self):
        report = self._complete()
        for candidate in ('b1761', 'b0728', 'b3236', 'b3403'):
            with self.subTest(candidate=candidate):
                self.assertGreater(report['growth_retention_by_candidate'][candidate], 0.90)
                self.assertEqual(report['supplement_uptake_by_candidate'][candidate], 10.0)

    def test_control_candidate_with_low_retention_is_rejected(self):
        base = self._record('rescue_reference')
        report = self._record('b1761', existing=base, objective_result=0.5, production=self._production(0.5))
        self.assertFalse(report['current_run_valid'])

    def test_missing_biomass_or_primary_diagnostic_is_rejected(self):
        growth = self.GROWTH['b1761']
        production = self._production(growth, biomass=None)
        production.pop('biomass_raw')
        self.assertFalse(self._record('b1761', production=production)['current_run_valid'])
        production = self._production(growth, diagnostics={'primary_objective_flux': None})
        self.assertFalse(self._record('b1761', production=production)['current_run_valid'])

    def test_diagnostic_method_objective_and_score_are_validated(self):
        growth = self.GROWTH['b1761']
        for diagnostics in (
            {'method': 'FBA'},
            {'objective_reaction': 'EX_ac_e'},
            {'method_score_name': 'primary_objective_flux'},
            {'method_score': 999.0},
            {'active_reaction_count': None},
        ):
            with self.subTest(diagnostics=diagnostics):
                production = self._production(growth, diagnostics=diagnostics)
                self.assertFalse(self._record('b1761', production=production)['current_run_valid'])

    def test_invalid_attempt_preserves_complete_evidence(self):
        complete = self._complete()
        invalid = self._record('b1761', existing=complete, method='FBA')
        self.assertFalse(invalid['current_run_recorded'])
        self.assertEqual(invalid['recorded_run_count'], 6)
        self.assertTrue(invalid['evidence_ready'])
        self.assertTrue(invalid['unique_transport_dependency_supported'])
        text = simulation.build_mission28_dependency_report_text(invalid)
        self.assertIn('Latest run was not recorded', text)
        self.assertIn('Previously valid Mission 28 dependency evidence remains available', text)

    def test_answer_aliases_are_accepted(self):
        report = self._complete()
        for answer in ('b2587', 'kgtP', 'AKGt2r', '2-oxoglutarate transporter', 'alpha-ketoglutarate transporter'):
            with self.subTest(answer=answer):
                self.assertTrue(simulation.mission28_answer_matches(answer, report))

    def test_wrong_answers_are_rejected(self):
        report = self._complete()
        for answer in ('b1761', 'b0728', 'b3236', 'b3403', 'gltA', 'CS', 'EX_akg_e', ''):
            with self.subTest(answer=answer):
                self.assertFalse(simulation.mission28_answer_matches(answer, report))

    def test_report_exposes_evidence_without_explicit_answer_sentence(self):
        text = simulation.build_mission28_dependency_report_text(self._complete())
        self.assertIn('Evidence complete', text)
        self.assertIn('Which secondary gene knockout', text)
        self.assertNotIn('The answer is b2587', text)
        self.assertNotIn('Submit kgtP', text)

    def test_empty_report_intro_is_detailed_without_repeating_the_mission_title(self):
        text = simulation.build_mission28_dependency_report_text(None)
        self.assertNotIn('Mission 28 Bypass Dependency Mapping', text)
        self.assertIn('No dependency evidence has been recorded yet', text)
        self.assertIn('Experimental objective:', text)
        self.assertIn('Dependency screen:', text)
        self.assertIn('What to determine:', text)
        self.assertIn('five controlled secondary-knockout trials', text)
        self.assertNotIn('The answer is b2587', text)

    def test_report_state_is_json_serializable(self):
        json.dumps(self._complete())

    def test_validator_does_not_run_hidden_simulations(self):
        source = inspect.getsource(simulation._build_mission28_data)
        self.assertNotIn('simulate(', source)
        self.assertNotIn('_http_post_json', source)
        wrapper = inspect.getsource(simulation.run_mission28_dependency_check_remote)
        self.assertNotIn('_http_post_json', wrapper)

    def test_window_uses_visible_normal_simulation_not_bound_sweep(self):
        source = (CODE_DIR / 'window.py').read_text()
        self.assertIn('run_mission28_dependency_check(self.results)', source)
        self.assertIn('run_mission28_dependency_check_remote(BACKEND_URL, self.results)', source)
        active_block = source[source.index('bound_sweep_mission_active ='):source.index('menu_compare_runs =')]
        self.assertNotIn("('28' in self.player.missions_activated", active_block)
        self.assertNotIn('run_mission28_bound_sweep_check(bound_sweep_data)', source)

    def test_gene_menu_highlights_primary_and_secondary_candidates(self):
        source = (CODE_DIR / 'window.py').read_text()
        self.assertIn("('28', [MISSION28_PRIMARY_GENE, *MISSION28_SECONDARY_GENES])", source)

    def test_ribeiro_ui_controls_missions_27_and_28(self):
        source = (CODE_DIR / 'mission27.py').read_text()
        self.assertIn('self.menu28 = Mission28_info', source)
        self.assertIn("elif '27' in self.missions_completed", source)
        self.assertIn('menu_to_open=self.menu28', source)
        self.assertIn('Dr. Li will continue', source)

    def test_mission28_ui_has_activation_and_answer_guards(self):
        source = (CODE_DIR / 'mission28.py').read_text()
        self.assertIn('Dr. Ribeiro', source)
        self.assertIn('Bypass Dependency Mapping', source)
        self.assertIn('initialise_mission28_dependency_screen', source)
        self.assertIn('mission28_answer_matches', source)
        self.assertIn("if '28' not in self.missions_activated", source)
        self.assertNotIn('Dr. Luna', source)
        self.assertNotIn('Alternative Carbon Source Sweep', source)

    def test_save_layer_has_dedicated_dependency_artifact(self):
        source = (CODE_DIR / 'save_load.py').read_text()
        self.assertIn('def save_mission28_dependency_check', source)
        self.assertIn('mission28_dependency_check.txt', source)
        self.assertIn('def clear_mission28_dependency_check', source)

    def test_documentation_matches_redesign(self):
        documentation = (PROJECT_ROOT / 'data' / 'missions' / 'mission28.md').read_text()
        self.assertIn('Dr. Ribeiro', documentation)
        self.assertIn('Bypass Dependency Mapping', documentation)
        self.assertIn('b2587', documentation)
        self.assertIn('AKGt2r', documentation)
        self.assertNotIn('Dr. Luna', documentation)
        self.assertNotIn('-20, -10, -5', documentation)

    def test_candidate_gprs_match_expected_reactions(self):
        model_path = PROJECT_ROOT / 'data' / 'models' / 'e_coli_core.xml.gz'
        ns = {
            'sbml': 'http://www.sbml.org/sbml/level3/version1/core',
            'fbc': 'http://www.sbml.org/sbml/level3/version1/fbc/version2',
        }
        with gzip.open(model_path, 'rb') as handle:
            root = ET.parse(handle).getroot()
        for gene_id, reaction_id in simulation.MISSION28_SECONDARY_REACTIONS.items():
            with self.subTest(gene=gene_id, reaction=reaction_id):
                reaction = next(
                    item for item in root.findall('.//sbml:reaction', ns)
                    if item.attrib.get('id') == 'R_' + reaction_id
                )
                refs = [
                    item.attrib[f"{{{ns['fbc']}}}geneProduct"]
                    for item in reaction.findall('.//fbc:geneProductRef', ns)
                ]
                self.assertIn('G_' + gene_id, refs)

    def test_independent_fba_growth_and_uptake_values(self):
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
        supplement = reaction_index['R_EX_akg_e']
        objective = np.zeros(len(reactions))
        objective[biomass] = -1.0
        base = list(bounds)
        base[reaction_index['R_CS']] = (0.0, 0.0)
        base[supplement] = (-10.0, base[supplement][1])
        conditions = [('rescue_reference', None)] + [
            (gene_id, simulation.MISSION28_SECONDARY_REACTIONS[gene_id])
            for gene_id in simulation.MISSION28_SECONDARY_GENES
        ]
        for key, reaction_id in conditions:
            with self.subTest(condition=key):
                current = list(base)
                if reaction_id:
                    current[reaction_index['R_' + reaction_id]] = (0.0, 0.0)
                result = linprog(
                    objective,
                    A_eq=matrix,
                    b_eq=np.zeros(len(species)),
                    bounds=current,
                    method='highs',
                )
                self.assertTrue(result.success)
                self.assertAlmostEqual(result.x[biomass], self.GROWTH[key], delta=1e-6)
                expected_uptake = 0.0 if key == 'b2587' else 10.0
                self.assertAlmostEqual(max(-result.x[supplement], 0.0), expected_uptake, delta=1e-6)

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
        for key in ('rescue_reference', *simulation.MISSION28_SECONDARY_GENES):
            secondary = None if key == 'rescue_reference' else key
            env = {reaction: list(bounds) for reaction, bounds in default_env.items()}
            env[simulation.MISSION28_RESCUE_SUPPLEMENT][0] = -10.0
            knockouts = [simulation.MISSION28_PRIMARY_GENE]
            if secondary:
                knockouts.append(secondary)
            response = backend_simulate(SimulateRequest(
                method=simulation.MISSION28_METHOD,
                objective=simulation.MISSION28_GROWTH_OBJECTIVE,
                gene_knockouts=knockouts,
                env_conditions=env,
            ))
            self.assertEqual(response.status, 'ok')
            self.assertAlmostEqual(response.primary_objective_flux, self.GROWTH[key], delta=1e-6)
            expected_uptake = 0.0 if key == 'b2587' else 10.0
            self.assertAlmostEqual(max(-response.fluxes[simulation.MISSION28_RESCUE_SUPPLEMENT], 0.0), expected_uptake, delta=1e-6)


if __name__ == '__main__':
    unittest.main()
