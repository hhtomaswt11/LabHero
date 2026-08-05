"""Regression tests for Mission 25 context-dependent gene essentiality.

Run from the project root with:
    python3 tests/test_mission25.py
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


class Mission25RegressionTests(unittest.TestCase):
    EXPECTED = {
        'aerobic_wild_type': {
            'growth': 0.873921507,
            'glucose': -10.0,
            'oxygen': -21.799493,
            'total': 518.422086,
            'active': 48,
        },
        'aerobic_knockout': {
            'growth': 0.870744806,
            'glucose': -10.0,
            'oxygen': -21.938351,
            'total': 520.875467,
            'active': 49,
        },
        'anaerobic_wild_type': {
            'growth': 0.211662950,
            'glucose': -10.0,
            'oxygen': 0.0,
            'total': 335.650617,
            'active': 47,
        },
        'anaerobic_knockout': {
            'growth': 0.0,
            # With a zero biomass optimum FBA has alternative optima.  This is
            # one valid returned solution; the validator deliberately requires
            # numeric evidence and capacity compliance rather than exactly 10.
            'glucose': -3.356,
            'oxygen': 0.0,
            'total': 107.392,
            'active': 20,
        },
    }

    def _genes(self, knockout=False, extra=None):
        genes = simulation._build_active_genes_data()
        if knockout:
            genes[simulation.MISSION25_TARGET_GENE] = False
        for gene_id in extra or []:
            genes[gene_id] = False
        return genes

    def _reactions(self, context='aerobic', *, extra_change=None, incomplete=False):
        reactions = simulation._build_default_reactions_data()
        oxygen_index = list(simulation.REACTIONS.index).index(simulation.MISSION25_OXYGEN_REACTION)
        if context == 'anaerobic':
            reactions[f'reaction_{oxygen_index}_lb'] = False
        if extra_change:
            reaction_id, bound = extra_change
            index = list(simulation.REACTIONS.index).index(reaction_id)
            key = f'reaction_{index}_{bound}'
            reactions[key] = not bool(reactions[key])
        if incomplete:
            reactions.pop(next(iter(reactions)))
        return reactions

    def _production(self, key, *, diagnostics=None, biomass=None, error=None):
        data = self.EXPECTED[key]
        growth = data['growth'] if biomass is None else biomass
        result = {
            'selected_ids': [],
            'items': [],
            'biomass_raw': growth,
            'method_diagnostics': {
                'method': simulation.MISSION25_METHOD,
                'objective_reaction': simulation.MISSION25_GROWTH_OBJECTIVE,
                'primary_objective_flux': growth,
                'method_score': growth,
                'method_score_name': 'primary_objective_flux',
                'total_absolute_flux': data['total'],
                'active_reaction_count': data['active'],
            },
        }
        if diagnostics:
            result['method_diagnostics'].update(diagnostics)
        if error:
            result['error'] = error
        return result

    def _medium(self, key, *, missing=None, glucose=None, oxygen=None, error=None):
        data = self.EXPECTED[key]
        raw_glucose = data['glucose'] if glucose is None else glucose
        raw_oxygen = data['oxygen'] if oxygen is None else oxygen
        items = []
        for reaction_id, raw in (
            (simulation.MISSION25_GLUCOSE_REACTION, raw_glucose),
            (simulation.MISSION25_OXYGEN_REACTION, raw_oxygen),
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

    def _cell(self, key, *, method=None, objective=None, genes=None, reactions=None,
              production=None, medium=None, objective_result=None, existing=None,
              objective_error=None):
        context = 'anaerobic' if key.startswith('anaerobic') else 'aerobic'
        knockout = key.endswith('knockout')
        data = self.EXPECTED[key]
        with patch.object(simulation, 'save_mission25_comparison_check'):
            return simulation._build_mission25_data(
                method or simulation.MISSION25_METHOD,
                objective or simulation.MISSION25_GROWTH_OBJECTIVE,
                data['growth'] if objective_result is None else objective_result,
                genes if genes is not None else self._genes(knockout),
                reactions if reactions is not None else self._reactions(context),
                production_fluxes=production if production is not None else self._production(key),
                medium_fluxes=medium if medium is not None else self._medium(key),
                existing_report={} if existing is None else existing,
                objective_error=objective_error,
            )

    def _complete(self, order=None):
        report = {}
        for key in order or (
            'aerobic_wild_type',
            'aerobic_knockout',
            'anaerobic_wild_type',
            'anaerobic_knockout',
        ):
            report = self._cell(key, existing=report)
        return report

    def test_constants_and_progression(self):
        self.assertEqual(simulation.MISSION25_CHECK_VERSION, 2)
        self.assertEqual(simulation.MISSION25_METHOD, 'FBA')
        self.assertEqual(simulation.MISSION25_TARGET_GENE, 'b3956')
        self.assertEqual(simulation.MISSION25_TARGET_GENE_NAME, 'ppc')
        self.assertEqual(simulation.MISSION25_TARGET_REACTION, 'PPC')
        self.assertFalse(simulation.is_mission25_unlocked([]))
        self.assertFalse(simulation.is_mission25_unlocked(['23']))
        self.assertTrue(simulation.is_mission25_unlocked(['24']))

    def test_initial_state_contains_four_empty_cells(self):
        with patch.object(simulation, 'save_mission25_comparison_check'):
            report = simulation.initialise_mission25_context_matrix()
        self.assertEqual(report['recorded_run_count'], 0)
        self.assertEqual(len(report['missing_conditions']), 4)
        self.assertFalse(report['evidence_ready'])

    def test_four_valid_cells_complete_relationship(self):
        report = self._complete()
        self.assertEqual(report['recorded_run_count'], 4)
        self.assertTrue(report['matrix_complete'])
        self.assertTrue(report['evidence_ready'])
        self.assertTrue(report['relationship_supported'])
        self.assertTrue(report['ready_to_deliver'])
        self.assertAlmostEqual(report['aerobic_growth_retention'], 0.996365, delta=1e-5)
        self.assertAlmostEqual(report['anaerobic_growth_retention'], 0.0, delta=1e-9)
        self.assertGreater(report['context_effect_difference'], 0.99)

    def test_cells_can_arrive_in_any_order(self):
        report = self._complete([
            'anaerobic_knockout',
            'aerobic_knockout',
            'anaerobic_wild_type',
            'aerobic_wild_type',
        ])
        self.assertTrue(report['relationship_supported'])
        self.assertEqual(report['missing_conditions'], [])

    def test_three_cells_are_incomplete(self):
        report = {}
        for key in ('aerobic_wild_type', 'aerobic_knockout', 'anaerobic_wild_type'):
            report = self._cell(key, existing=report)
        self.assertEqual(report['recorded_run_count'], 3)
        self.assertEqual(report['missing_conditions'], ['anaerobic_knockout'])
        self.assertFalse(report['evidence_ready'])

    def test_repeated_cell_replaces_without_duplication(self):
        report = self._complete()
        repeated = self._cell('aerobic_knockout', existing=report)
        self.assertEqual(repeated['recorded_run_count'], 4)
        self.assertEqual(repeated['aerobic_knockout']['run_type'], 'aerobic_knockout')

    def test_wrong_method_or_objective_is_rejected(self):
        self.assertFalse(self._cell('aerobic_wild_type', method='pFBA')['current_run_valid'])
        self.assertFalse(self._cell('aerobic_wild_type', objective='EX_ac_e')['current_run_valid'])

    def test_genotype_must_be_wild_type_or_single_target_knockout(self):
        wrong = self._cell('aerobic_knockout', genes=self._genes(False, ['b0728']))
        self.assertFalse(wrong['current_run_valid'])
        two = self._cell('aerobic_knockout', genes=self._genes(True, ['b0728']))
        self.assertFalse(two['current_run_valid'])
        self.assertIn('either every gene active or only', ' '.join(two['current_issues']))

    def test_environment_is_key_order_independent(self):
        reordered = dict(reversed(list(self._reactions('anaerobic').items())))
        report = self._cell('anaerobic_wild_type', reactions=reordered)
        self.assertTrue(report['current_run_valid'])
        self.assertEqual(report['current_run_type'], 'anaerobic_wild_type')

    def test_incomplete_or_extra_environment_change_is_rejected(self):
        incomplete = self._cell('aerobic_wild_type', reactions=self._reactions('aerobic', incomplete=True))
        self.assertFalse(incomplete['current_run_valid'])
        changed = self._cell(
            'aerobic_wild_type',
            reactions=self._reactions('aerobic', extra_change=('EX_nh4_e', 'lb')),
        )
        self.assertFalse(changed['current_run_valid'])
        self.assertIn('unrelated environmental bound', ' '.join(changed['current_issues']))

    def test_numeric_glucose_and_oxygen_evidence_is_required(self):
        report = self._cell(
            'aerobic_wild_type',
            medium=self._medium('aerobic_wild_type', missing=simulation.MISSION25_OXYGEN_REACTION),
        )
        self.assertFalse(report['current_run_valid'])
        self.assertIn('Numeric glucose and oxygen', ' '.join(report['current_issues']))

    def test_aerobic_cell_requires_oxygen_uptake(self):
        report = self._cell(
            'aerobic_wild_type',
            medium=self._medium('aerobic_wild_type', oxygen=0.0),
        )
        self.assertFalse(report['current_run_valid'])
        self.assertIn('measurable oxygen uptake', ' '.join(report['current_issues']))

    def test_anaerobic_cell_requires_zero_oxygen_flux(self):
        report = self._cell(
            'anaerobic_wild_type',
            medium=self._medium('anaerobic_wild_type', oxygen=-1.0),
        )
        self.assertFalse(report['current_run_valid'])
        self.assertIn('zero oxygen uptake', ' '.join(report['current_issues']))

    def test_glucose_must_be_numeric_and_within_default_capacity(self):
        report = self._cell(
            'aerobic_wild_type',
            medium=self._medium('aerobic_wild_type', glucose=-11.0),
        )
        self.assertFalse(report['current_run_valid'])
        self.assertIn('exceeds the model-default capacity', ' '.join(report['current_issues']))

    def test_zero_growth_anaerobic_knockout_is_valid_evidence(self):
        report = self._cell('anaerobic_knockout')
        self.assertTrue(report['current_run_valid'])
        self.assertEqual(report['anaerobic_knockout']['growth'], 0.0)

    def test_biomass_and_primary_diagnostics_must_match(self):
        report = self._cell(
            'aerobic_wild_type',
            production=self._production('aerobic_wild_type', biomass=0.5),
        )
        self.assertFalse(report['current_run_valid'])
        self.assertIn('does not match the biomass-reaction flux', ' '.join(report['current_issues']))
        report = self._cell(
            'aerobic_wild_type',
            production=self._production('aerobic_wild_type', diagnostics={'primary_objective_flux': 0.5}),
        )
        self.assertFalse(report['current_run_valid'])
        self.assertIn('does not match biomass', ' '.join(report['current_issues']))

    def test_fba_score_semantics_and_distribution_diagnostics_are_required(self):
        report = self._cell(
            'aerobic_wild_type',
            production=self._production('aerobic_wild_type', diagnostics={'method_score_name': 'total_absolute_flux'}),
        )
        self.assertFalse(report['current_run_valid'])
        self.assertIn('method-score meaning', ' '.join(report['current_issues']))
        report = self._cell(
            'aerobic_wild_type',
            production=self._production('aerobic_wild_type', diagnostics={'total_absolute_flux': None}),
        )
        self.assertFalse(report['current_run_valid'])
        self.assertIn('flux-distribution diagnostics', ' '.join(report['current_issues']))

    def test_relationship_rejects_wrong_retention_pattern(self):
        report = self._complete()
        altered = dict(report)
        altered['anaerobic_knockout'] = dict(report['anaerobic_knockout'])
        altered['anaerobic_knockout']['growth'] = 0.20
        rebuilt = self._cell('aerobic_wild_type', existing=altered)
        self.assertFalse(rebuilt['relationship_supported'])

    def test_invalid_later_run_preserves_complete_matrix(self):
        valid = self._complete()
        invalid = self._cell('aerobic_wild_type', method='pFBA', existing=valid)
        self.assertFalse(invalid['current_run_recorded'])
        self.assertEqual(invalid['recorded_run_count'], 4)
        self.assertTrue(invalid['evidence_ready'])
        self.assertTrue(invalid['ready_to_deliver'])
        text = simulation.build_mission25_context_report_text(invalid)
        self.assertIn('Latest run was not recorded', text)
        self.assertIn('Previously valid Mission 25 matrix evidence remains available', text)

    def test_explicit_visible_result_wrapper_does_not_load_compare_runs(self):
        results = [
            simulation.MISSION25_GROWTH_OBJECTIVE,
            self.EXPECTED['aerobic_wild_type']['growth'],
            self._production('aerobic_wild_type'),
            self._medium('aerobic_wild_type'),
        ]
        with patch.object(simulation, '_read_simulation_file', return_value=(
            simulation.MISSION25_METHOD,
            simulation.MISSION25_GROWTH_OBJECTIVE,
            self._genes(False),
            self._reactions('aerobic'),
        )):
            with patch.object(simulation, 'load_mission25_comparison_check', return_value={}):
                with patch.object(simulation, 'save_mission25_comparison_check'):
                    report = simulation.run_mission25_context_check(results)
        self.assertTrue(report['current_run_recorded'])
        self.assertEqual(report['current_run_type'], 'aerobic_wild_type')

    def test_answer_aliases_are_accepted(self):
        report = self._complete()
        for answer in (
            'anaerobic', 'anaerobiosis', 'without oxygen', 'oxygen blocked',
            'anaeróbio', 'anaerobiose', 'sem oxigénio', 'oxigénio bloqueado',
        ):
            with self.subTest(answer=answer):
                self.assertTrue(simulation.mission25_answer_matches(answer, report))

    def test_wrong_multiple_or_gene_answers_are_rejected(self):
        report = self._complete()
        for answer in ('aerobic', 'with oxygen', 'both', 'b3956', 'ppc', 'anaerobic and aerobic', ''):
            with self.subTest(answer=answer):
                self.assertFalse(simulation.mission25_answer_matches(answer, report))

    def test_report_exposes_matrix_without_declaring_answer(self):
        text = simulation.build_mission25_context_report_text(self._complete())
        self.assertIn('Matrix cells recorded: 4/4', text)
        self.assertIn('Evidence complete', text)
        self.assertIn('99.6%', text)
        self.assertIn('0.0%', text)
        self.assertNotIn('The answer is anaerobic', text)
        self.assertNotIn('Submit anaerobic', text)
        self.assertNotIn('Anaerobic is the stronger context', text)

    def test_state_is_json_serialisable(self):
        json.dumps(self._complete())

    def test_validator_and_remote_wrapper_launch_no_solver_or_http_request(self):
        source = inspect.getsource(simulation._build_mission25_data)
        source += inspect.getsource(simulation.run_mission25_context_check)
        source += inspect.getsource(simulation.run_mission25_context_check_remote)
        self.assertNotIn('simul.simulate', source)
        self.assertNotIn('_http_post_json', source)
        self.assertNotIn('run_simul', source)

    def test_window_integrates_visible_result_and_highlights_gene(self):
        source = (CODE_DIR / 'window.py').read_text()
        self.assertIn("('25', [MISSION25_TARGET_GENE])", source)
        self.assertIn('run_mission25_context_check_remote(BACKEND_URL, self.results)', source)
        self.assertIn('run_mission25_context_check(self.results)', source)
        self.assertIn('return build_mission25_context_report_text(report_data)', source)
        self.assertNotIn('run_mission25_comparison_check(compare_runs)', source)

    def test_mission_ui_has_gating_idempotence_and_answer_guards(self):
        source = (CODE_DIR / 'mission25.py').read_text()
        self.assertIn('is_mission25_unlocked', source)
        self.assertIn("if '25' in self.missions_activated", source)
        self.assertIn('initialise_mission25_context_matrix', source)
        self.assertIn('mission25_answer_matches', source)
        self.assertIn('Dr. Smith', source)
        self.assertIn('Context-Dependent Gene Essentiality', source)
        self.assertNotIn('Deliver Final Report', source)
        self.assertNotIn('Dr. Vega', source)

    def test_documentation_matches_redesign(self):
        documentation = (PROJECT_ROOT / 'data' / 'missions' / 'mission25.md').read_text()
        self.assertIn('Dr. Smith', documentation)
        self.assertIn('b3956', documentation)
        self.assertIn('ppc', documentation)
        self.assertIn('four', documentation.lower())
        self.assertNotIn('Dr. Vega', documentation)
        self.assertNotIn('Final Controlled Report', documentation)

    def test_ppc_gpr_is_single_b3956_gene(self):
        model_path = PROJECT_ROOT / 'data' / 'models' / 'e_coli_core.xml.gz'
        ns = {
            'sbml': 'http://www.sbml.org/sbml/level3/version1/core',
            'fbc': 'http://www.sbml.org/sbml/level3/version1/fbc/version2',
        }
        with gzip.open(model_path, 'rb') as handle:
            root = ET.parse(handle).getroot()
        reaction = next(
            item for item in root.findall('.//sbml:reaction', ns)
            if item.attrib.get('id') == 'R_PPC'
        )
        refs = reaction.findall('.//fbc:geneProductRef', ns)
        self.assertEqual([item.attrib[f"{{{ns['fbc']}}}geneProduct"] for item in refs], ['G_b3956'])

    def test_independent_fba_values_for_four_matrix_cells(self):
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
        oxygen = reaction_index['R_EX_o2_e']
        ppc = reaction_index['R_PPC']
        objective = np.zeros(len(reactions))
        objective[biomass] = -1.0

        for key, expected in self.EXPECTED.items():
            with self.subTest(cell=key):
                current_bounds = list(bounds)
                if key.startswith('anaerobic'):
                    current_bounds[oxygen] = (0.0, current_bounds[oxygen][1])
                if key.endswith('knockout'):
                    current_bounds[ppc] = (0.0, 0.0)
                result = linprog(
                    objective,
                    A_eq=matrix,
                    b_eq=np.zeros(len(species)),
                    bounds=current_bounds,
                    method='highs',
                )
                self.assertTrue(result.success)
                self.assertAlmostEqual(result.x[biomass], expected['growth'], delta=1e-6)
                self.assertAlmostEqual(result.x[reaction_index['R_EX_o2_e']], expected['oxygen'], delta=1e-5)
                if not key.endswith('knockout') or key.startswith('aerobic'):
                    self.assertAlmostEqual(result.x[reaction_index['R_EX_glc__D_e']], expected['glucose'], delta=1e-5)

    def test_backend_contract_when_dependencies_exist(self):
        backend_dir = PROJECT_ROOT / 'backend'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        try:
            from app.schemas import SimulateRequest
            from app.simulator import simulate as backend_simulate
        except (ModuleNotFoundError, ImportError) as exc:
            self.skipTest(f'Backend MEWpy/COBRApy unavailable: {exc}')

        default_env = simulation._build_default_env_conditions_payload()
        for key, expected in self.EXPECTED.items():
            env = {reaction: list(bounds) for reaction, bounds in default_env.items()}
            if key.startswith('anaerobic'):
                env[simulation.MISSION25_OXYGEN_REACTION][0] = 0.0
            knockouts = [simulation.MISSION25_TARGET_GENE] if key.endswith('knockout') else []
            response = backend_simulate(SimulateRequest(
                method=simulation.MISSION25_METHOD,
                objective=simulation.MISSION25_GROWTH_OBJECTIVE,
                gene_knockouts=knockouts,
                env_conditions=env,
            ))
            self.assertEqual(response.status, 'ok', response.message)
            self.assertAlmostEqual(float(response.primary_objective_flux), expected['growth'], delta=1e-3)
            self.assertEqual(response.method_score_name, 'primary_objective_flux')
            self.assertAlmostEqual(float(response.fluxes[simulation.MISSION25_GROWTH_OBJECTIVE]), expected['growth'], delta=1e-3)
            self.assertAlmostEqual(float(response.fluxes[simulation.MISSION25_OXYGEN_REACTION]), expected['oxygen'], delta=1e-3)


if __name__ == '__main__':
    unittest.main()
