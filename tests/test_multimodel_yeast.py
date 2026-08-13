"""Regression tests for the post-Mission-35 multi-model/yeast simulator layer.

Run from the project root with:
    python3 tests/test_multimodel_yeast.py

The suite intentionally avoids importing COBRA/MEWpy so it can also run in a
lightweight CI container.  A small independent SciPy LP verifies that the
bundled iMM904 SBML still produces its expected default biomass optimum.
"""
from __future__ import annotations

import gzip
import hashlib
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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / 'code'
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

# simulation.py uses these imports only on native solver paths.  For the
# request-contract tests below we deliberately keep execution on the browser
# branch so no COBRA/MEWpy installation is required.
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

import model_registry  # noqa: E402
import progression  # noqa: E402
import simulation  # noqa: E402
sys.platform = _original_platform


class MultiModelYeastRegressionTests(unittest.TestCase):
    CORE_NS = 'http://www.sbml.org/sbml/level3/version1/core'
    FBC_NS = 'http://www.sbml.org/sbml/level3/version1/fbc/version2'

    @classmethod
    def setUpClass(cls):
        cls.yeast_model_path = PROJECT_ROOT / 'data' / 'models' / 'iMM904.xml.gz'
        cls.yeast_meta_path = PROJECT_ROOT / 'data' / 'models' / 'iMM904_meta.json'
        with cls.yeast_meta_path.open(encoding='utf-8') as handle:
            cls.meta = json.load(handle)

    def test_registry_keeps_ecoli_and_adds_yeast(self):
        self.assertEqual(model_registry.DEFAULT_MODEL_ID, 'ecoli_core')
        self.assertIn('ecoli_core', model_registry.MODEL_REGISTRY)
        self.assertIn('yeast_iMM904', model_registry.MODEL_REGISTRY)
        self.assertEqual(
            model_registry.MODEL_REGISTRY['ecoli_core']['default_objective'],
            'BIOMASS_Ecoli_core_w_GAM',
        )
        self.assertEqual(
            model_registry.MODEL_REGISTRY['yeast_iMM904']['default_objective'],
            'BIOMASS_SC5_notrace',
        )

    def test_sweep_config_default_cannot_leak_from_last_saved_model(self):
        """Historic E. coli sweep parsing must not depend on the last model save."""
        menu = {
            'sweep_variable': [[('Ammonium', 'EX_nh4_e:lower')]],
            'sweep_values': [[('Ammonium sensitivity', 'ammonium_sensitivity')]],
        }
        with patch.object(simulation, '_read_simulation_model_id', return_value='yeast_iMM904'):
            ecoli = simulation._normalise_sweep_config(menu)
        self.assertEqual(ecoli['model_id'], model_registry.DEFAULT_MODEL_ID)
        self.assertEqual(ecoli['reaction_id'], 'EX_nh4_e')
        self.assertEqual(ecoli['preset'], 'ammonium_sensitivity')

        yeast = simulation._normalise_sweep_config(
            {
                'sweep_variable': [[('Glucose', 'EX_glc__D_e:lower')]],
                'sweep_values': [[('Yeast threshold', 'yeast_glucose_fermentation_threshold')]],
            },
            model_id='yeast_iMM904',
        )
        self.assertEqual(yeast['model_id'], 'yeast_iMM904')
        self.assertEqual(yeast['reaction_id'], 'EX_glc__D_e')
        self.assertEqual(yeast['preset'], 'yeast_glucose_fermentation_threshold')

    def test_yeast_metadata_matches_expected_model_scale(self):
        self.assertEqual(self.meta['model_id'], 'yeast_iMM904')
        self.assertEqual(self.meta['objective'], 'BIOMASS_SC5_notrace')
        self.assertEqual(len(self.meta['reactions_all']['index']), 1577)
        self.assertEqual(len(self.meta['reactions_ex']['index']), 164)
        self.assertEqual(len(self.meta['genes']), 905)
        self.assertEqual(len(self.meta['gene_names']), 905)
        for reaction_id in (
            'EX_glc__D_e', 'EX_o2_e', 'EX_nh4_e', 'EX_pi_e', 'EX_so4_e',
            'EX_etoh_e', 'EX_ac_e', 'EX_glyc_e', 'EX_pyr_e', 'EX_succ_e',
        ):
            self.assertIn(reaction_id, self.meta['reactions_ex']['index'])

    def test_large_model_ui_is_scalable_and_complete(self):
        context = model_registry.build_ui_context('yeast_iMM904')
        self.assertEqual(context['gene_ui_mode'], 'text')
        self.assertEqual(context['objective_ui_mode'], 'text')
        self.assertEqual(context['environment_ui_mode'], 'compact_text')
        self.assertEqual(context['supported_methods'], ['FBA', 'pFBA'])
        # No 905 gene toggles or 1577 objective drop-down entries are required,
        # but the complete catalogues remain available for validation.
        self.assertEqual(len(context['genes']), 905)
        self.assertEqual(len(context['all_reaction_ids']), 1577)
        self.assertEqual(len(context['objective_ids']), 1577)
        self.assertIn('BIOMASS_SC5_notrace', context['objective_ids'])
        self.assertLessEqual(max(len(reaction_id) for reaction_id in context['objective_ids']), 24)
        self.assertGreater(len(context['production_flux_options']), 0)
        for option in context['production_flux_options']:
            self.assertIn(option['id'], self.meta['reactions_ex']['index'])

        ecoli_context = model_registry.build_ui_context('ecoli_core')
        self.assertEqual(ecoli_context['environment_ui_mode'], 'toggles')

    def test_compact_environment_editor_preserves_defaults_and_applies_exact_overrides(self):
        context = model_registry.build_ui_context('yeast_iMM904')
        exchanges = context['exchanges']
        payload, errors = model_registry.build_compact_environment_payload(exchanges)
        self.assertEqual(errors, [])
        oxygen_index = next(i for i, row in enumerate(exchanges) if row['id'] == 'EX_o2_e')
        glucose_index = next(i for i, row in enumerate(exchanges) if row['id'] == 'EX_glc__D_e')
        self.assertTrue(payload[f'reaction_{oxygen_index}_lb'])
        self.assertTrue(payload[f'reaction_{glucose_index}_lb'])

        payload, errors = model_registry.build_compact_environment_payload(
            exchanges,
            lower_close_text='EX_o2_e',
        )
        self.assertEqual(errors, [])
        self.assertFalse(payload[f'reaction_{oxygen_index}_lb'])
        self.assertTrue(payload[f'reaction_{glucose_index}_lb'])

        # Find a yeast exchange whose uptake is closed by default and prove
        # that the compact UI can open it without a dedicated widget.
        closed_index = next(i for i, row in enumerate(exchanges) if float(row['lb']) == 0.0)
        closed_id = exchanges[closed_index]['id']
        payload, errors = model_registry.build_compact_environment_payload(
            exchanges,
            lower_open_text=closed_id,
        )
        self.assertEqual(errors, [])
        self.assertTrue(payload[f'reaction_{closed_index}_lb'])

    def test_compact_environment_editor_rejects_unknown_and_conflicting_edits(self):
        context = model_registry.build_ui_context('yeast_iMM904')
        exchanges = context['exchanges']
        _payload, errors = model_registry.build_compact_environment_payload(
            exchanges,
            lower_open_text='THIS_IS_NOT_AN_EXCHANGE',
        )
        self.assertTrue(any('Unknown exchange id' in error for error in errors))

        _payload, errors = model_registry.build_compact_environment_payload(
            exchanges,
            lower_open_text='EX_o2_e',
            lower_close_text='EX_o2_e',
        )
        self.assertTrue(any('both opened and closed' in error for error in errors))

    def test_yeast_gene_text_parser_is_strict_and_supports_common_names(self):
        context = model_registry.build_ui_context('yeast_iMM904')
        payload, knockouts, unknown, ambiguous = model_registry.parse_gene_knockout_text(
            'YOL086C ADH1', context['genes'], context['gene_names']
        )
        self.assertEqual(knockouts, ['YOL086C'])
        self.assertFalse(payload['YOL086C'])
        self.assertEqual(unknown, [])
        self.assertEqual(ambiguous, [])

        payload, knockouts, unknown, ambiguous = model_registry.parse_gene_knockout_text(
            'THIS_IS_NOT_A_GENE', context['genes'], context['gene_names']
        )
        self.assertEqual(knockouts, [])
        self.assertEqual(unknown, ['THIS_IS_NOT_A_GENE'])
        self.assertEqual(ambiguous, [])
        self.assertTrue(all(payload.values()))

    def test_large_model_gene_preview_confirms_canonical_ids_and_rejects_bad_tokens(self):
        context = model_registry.build_ui_context('yeast_iMM904')
        preview = model_registry.build_gene_knockout_preview(
            'adh1', context['genes'], context['gene_names']
        )
        self.assertIn('Registered knockouts:', preview)
        self.assertIn('YOL086C (ADH1)', preview)

        preview = model_registry.build_gene_knockout_preview(
            '', context['genes'], context['gene_names']
        )
        self.assertIn('none (wild type)', preview)

        preview = model_registry.build_gene_knockout_preview(
            'THIS_IS_NOT_A_GENE', context['genes'], context['gene_names']
        )
        self.assertIn('Selection not registered:', preview)
        self.assertIn('Unknown gene id/name', preview)

    def test_large_model_environment_preview_matches_strict_validation(self):
        context = model_registry.build_ui_context('yeast_iMM904')
        exchanges = context['exchanges']

        preview = model_registry.build_compact_environment_preview(exchanges)
        self.assertIn('none (model defaults)', preview)

        preview = model_registry.build_compact_environment_preview(
            exchanges,
            lower_close_text='EX_o2_e',
        )
        self.assertIn('Registered environmental changes:', preview)
        self.assertIn('EX_o2_e', preview)
        self.assertIn('lower bound CLOSED', preview)
        self.assertIn('-2.0 -> 0.0', preview)

        preview = model_registry.build_compact_environment_preview(
            exchanges,
            lower_open_text='EX_o2_e',
            lower_close_text='EX_o2_e',
        )
        self.assertIn('Changes not registered:', preview)
        self.assertIn('both opened and closed', preview)

        preview = model_registry.build_compact_environment_preview(
            exchanges,
            lower_close_text='THIS_IS_NOT_AN_EXCHANGE',
        )
        self.assertIn('Changes not registered:', preview)
        self.assertIn('Unknown exchange id', preview)

    def test_large_model_text_fields_offer_explicit_preview_feedback(self):
        window_source = (PROJECT_ROOT / 'code' / 'window.py').read_text(encoding='utf-8')
        self.assertIn('Validate / Preview Genes', window_source)
        self.assertIn('Validate / Preview Environment', window_source)
        self.assertIn('build_gene_knockout_preview(', window_source)
        self.assertIn('build_compact_environment_preview(', window_source)
        self.assertIn('onreturn=refresh_gene_preview', window_source)
        self.assertGreaterEqual(window_source.count('onreturn=refresh_environment_preview'), 4)

    def test_tiled_yeast_simulator_is_on_player_layer(self):
        root = ET.parse(PROJECT_ROOT / 'data' / 'map_lb.tmx').getroot()
        matches = []
        for group in root.findall('objectgroup'):
            if group.attrib.get('name') != 'Player':
                continue
            matches.extend(
                obj for obj in group.findall('object')
                if obj.attrib.get('name') == 'YeastSimulator'
            )
        self.assertEqual(len(matches), 1)
        self.assertGreater(float(matches[0].attrib.get('width', 0)), 0)
        self.assertGreater(float(matches[0].attrib.get('height', 0)), 0)

    def test_player_and_level_wire_the_new_interaction(self):
        player_source = (PROJECT_ROOT / 'code' / 'player.py').read_text(encoding='utf-8')
        level_source = (PROJECT_ROOT / 'code' / 'level.py').read_text(encoding='utf-8')
        self.assertIn("collided_interaction_sprite[0].name == 'YeastSimulator'", player_source)
        self.assertIn('self.yeast_simulator()', player_source)
        self.assertIn("if obj.name == 'YeastSimulator':", level_source)
        self.assertIn("model_id='yeast_iMM904'", level_source)
        self.assertIn("is_model_unlocked('yeast_iMM904'", level_source)
        self.assertIn('self.yeast_simulator_active', level_source)
        self.assertIn('await self.yeast_window.update()', level_source)
        self.assertIn('self.yeast_window = None', level_source)

    def test_ecoli_environment_toggle_defaults_are_builtin_bools(self):
        # Native MEWpy tables may return numpy.bool_ for comparisons.
        # pygame-menu 4.4.3 rejects numpy.bool_ as a toggle default even
        # though it prints as False/True, so the UI must cast explicitly.
        window_source = (PROJECT_ROOT / 'code' / 'window.py').read_text(encoding='utf-8')
        self.assertIn(
            'default_lb_bool = bool(REACTIONS.lb.iloc[i] != 0)',
            window_source,
        )
        self.assertIn(
            'default_ub_bool = bool(REACTIONS.ub.iloc[i] != 0)',
            window_source,
        )

    def test_yeast_window_does_not_build_one_widget_pair_per_exchange(self):
        window_source = (PROJECT_ROOT / 'code' / 'window.py').read_text(encoding='utf-8')
        self.assertIn("environment_ui_mode') == 'compact_text'", window_source)
        self.assertIn('build_compact_environment_payload', window_source)
        self.assertIn('Large-model mode:', window_source)

    def test_yeast_text_inputs_use_fixed_geometry_and_objective_value_is_not_truncated(self):
        window_source = (PROJECT_ROOT / 'code' / 'window.py').read_text(encoding='utf-8')
        # pygame-menu TextInput with a dynamic full-width underline forces menu
        # surface relayout on cursor blink.  Large-model fields therefore use
        # bounded, fixed underline geometry.
        self.assertIn('input_underline_len=24', window_source)
        self.assertIn('input_underline_len=44', window_source)
        self.assertIn('input_underline_len=52', window_source)
        self.assertGreaterEqual(window_source.count('maxwidth_dynamically_update=False'), 6)
        self.assertNotIn('maxwidth=75', window_source)
        self.assertNotIn('maxwidth=90', window_source)
        # TextInput returns a plain string.  The exact objective must be read
        # from the widget rather than through DropSelect tuple indexing.
        self.assertIn('objective_text_input = menu_objective.add.text_input(', window_source)
        self.assertIn('objective_name = str(objective_text_input.get_value()).strip()', window_source)
        self.assertIn('if isinstance(value, str):', window_source)

    def test_yeast_unlock_is_derived_from_mission35(self):
        self.assertFalse(progression.is_model_unlocked('yeast_iMM904', []))
        self.assertFalse(progression.is_model_unlocked('yeast_iMM904', ['34']))
        self.assertTrue(progression.is_model_unlocked('yeast_iMM904', ['35']))
        self.assertTrue(progression.is_model_unlocked('yeast_iMM904', ['35', '34']))

    def test_simulation_request_carries_model_id_and_full_default_medium(self):
        context = model_registry.build_ui_context('yeast_iMM904')
        genes = {gene_id: True for gene_id in context['genes']}
        # Use a real yeast knockout to prove the request does not reuse E. coli genes.
        genes['YOL086C'] = False
        reactions = {}
        for index, row in enumerate(context['exchanges']):
            reactions[f'reaction_{index}_lb'] = bool(float(row['lb']) != 0.0)
            reactions[f'reaction_{index}_ub'] = bool(float(row['ub']) != 0.0)

        with (
            patch.object(simulation, '_read_simulation_file', return_value=(
                'pFBA', 'BIOMASS_SC5_notrace', genes, reactions,
            )),
            # Explicit request context must win over stale persisted state.
            patch.object(simulation, '_read_simulation_model_id', return_value='ecoli_core'),
        ):
            payload = simulation._build_request_payload(model_id='yeast_iMM904')

        self.assertEqual(payload['model_id'], 'yeast_iMM904')
        self.assertEqual(payload['method'], 'pFBA')
        self.assertEqual(payload['objective'], 'BIOMASS_SC5_notrace')
        self.assertEqual(payload['gene_knockouts'], ['YOL086C'])
        self.assertEqual(len(payload['env_conditions']), 164)
        self.assertEqual(payload['env_conditions']['EX_glc__D_e'][0], -10.0)
        self.assertEqual(payload['env_conditions']['EX_o2_e'][0], -2.0)

    def test_remote_yeast_sweep_uses_explicit_model_and_glucose_payloads(self):
        """Every browser row must use the same explicit yeast model context."""
        values = [-0.5, -1.0, -2.0, -10.0]
        responses = []
        for value in values:
            responses.append({
                'status': 'ok',
                'model_id': 'yeast_iMM904',
                'method': 'pFBA',
                'objective': 'BIOMASS_SC5_notrace',
                'objective_reaction': 'BIOMASS_SC5_notrace',
                'primary_objective_flux': 0.1,
                'method_score': 100.0,
                'method_score_name': 'total_absolute_flux',
                'total_absolute_flux': 100.0,
                'active_reaction_count': 10,
                'fluxes': {
                    'BIOMASS_SC5_notrace': 0.1,
                    'EX_glc__D_e': value,
                    'EX_o2_e': -2.0,
                    'EX_etoh_e': 1.0,
                    'EX_co2_e': 2.0,
                },
            })
        base_env = {
            row['id']: [float(row['lb']), float(row['ub'])]
            for row in model_registry.build_ui_context('yeast_iMM904')['exchanges']
        }
        with (
            patch.object(simulation, '_read_simulation_file', return_value=(
                'pFBA', 'BIOMASS_SC5_notrace', {}, {},
            )),
            patch.object(simulation, '_read_simulation_model_id', return_value='ecoli_core'),
            patch.object(simulation, '_read_selected_production_fluxes', return_value=['EX_etoh_e', 'EX_co2_e']),
            patch.object(simulation, '_build_request_payload', return_value={
                'model_id': 'ecoli_core',
                'method': 'pFBA',
                'objective': 'BIOMASS_SC5_notrace',
                'gene_knockouts': [],
                'env_conditions': base_env,
            }),
            patch.object(simulation, '_http_post_json', side_effect=responses) as post,
            patch.object(simulation, 'save_bound_sweep'),
        ):
            data = simulation.run_bound_sweep_remote(
                '/api',
                {
                    'sweep_variable': [[('Glucose', 'EX_glc__D_e:lower')]],
                    'sweep_values': [[('Yeast threshold', 'yeast_glucose_fermentation_threshold')]],
                },
                model_id='yeast_iMM904',
            )

        self.assertEqual(data['model_id'], 'yeast_iMM904')
        self.assertEqual(data['reaction_id'], 'EX_glc__D_e')
        self.assertEqual(post.call_count, 4)
        for call, value in zip(post.call_args_list, values):
            payload = call.args[1]
            self.assertEqual(payload['model_id'], 'yeast_iMM904')
            self.assertEqual(float(payload['env_conditions']['EX_glc__D_e'][0]), value)

    def test_window_passes_active_model_explicitly_to_bound_sweep(self):
        window_source = (CODE_DIR / 'window.py').read_text()
        self.assertIn(
            'BACKEND_URL, menu_bound_sweep.get_input_data(), model_id=self.model_id',
            window_source,
        )
        self.assertIn(
            'menu_bound_sweep.get_input_data(), model_id=self.model_id',
            window_source,
        )

    def test_old_simulation_save_defaults_to_ecoli(self):
        legacy_save = [{}, {}, {}, {}, {}]
        new_save = [{}, {}, {}, {}, {}, {'model_id': 'yeast_iMM904'}]
        with patch.object(simulation, 'load_file', return_value=legacy_save):
            self.assertEqual(simulation._read_simulation_model_id(), 'ecoli_core')
        with patch.object(simulation, 'load_file', return_value=new_save):
            self.assertEqual(simulation._read_simulation_model_id(), 'yeast_iMM904')

    def test_simulation_reader_preserves_text_objective_and_legacy_dropselect(self):
        # Yeast TextInput is a plain string.  It must never be indexed like a
        # DropSelect or BIOMASS_SC5_notrace silently becomes just 'B'.
        yeast_save = [
            {'method': [['FBA', 'FBA']]},
            {'objective': 'BIOMASS_SC5_notrace'},
            {'YOL086C': True},
            {},
        ]
        with patch.object(simulation, 'load_file', return_value=yeast_save):
            method, objective, _genes, _reactions = simulation._read_simulation_file()
        self.assertEqual(method, 'FBA')
        self.assertEqual(objective, 'BIOMASS_SC5_notrace')

        # Existing E. coli selector-shaped saves must remain readable.
        ecoli_save = [
            {'method': [['pFBA', 'pFBA']]},
            {'objective': [['BIOMASS_Ecoli_core_w_GAM', 'BIOMASS_Ecoli_core_w_GAM']]},
            {},
            {},
        ]
        with patch.object(simulation, 'load_file', return_value=ecoli_save):
            method, objective, _genes, _reactions = simulation._read_simulation_file()
        self.assertEqual(method, 'pFBA')
        self.assertEqual(objective, 'BIOMASS_Ecoli_core_w_GAM')

    def test_window_persists_canonical_yeast_objective_and_wraps_result_errors(self):
        window_source = (PROJECT_ROOT / 'code' / 'window.py').read_text(encoding='utf-8')
        self.assertIn("{'objective': objective_name}", window_source)
        self.assertIn('saved_objective_data', window_source)
        self.assertIn("label_id='results',\n                wordwrap=True", window_source)

    def test_backend_contract_is_multi_model_and_request_isolated(self):
        schema_source = (PROJECT_ROOT / 'backend' / 'app' / 'schemas.py').read_text(encoding='utf-8')
        simulator_source = (PROJECT_ROOT / 'backend' / 'app' / 'simulator.py').read_text(encoding='utf-8')
        registry_source = (PROJECT_ROOT / 'backend' / 'app' / 'model_registry.py').read_text(encoding='utf-8')
        self.assertIn("Literal['ecoli_core', 'yeast_iMM904']", schema_source)
        self.assertIn('model_id: ModelId', schema_source)
        self.assertIn("'yeast_iMM904'", registry_source)
        self.assertIn("'supported_methods': ('FBA', 'pFBA')", registry_source)
        self.assertIn('working_model = template.copy()', simulator_source)
        self.assertNotIn('_simul = get_simulator(_model)', simulator_source)
        self.assertIn('Unknown gene id(s) for model', simulator_source)
        self.assertIn('Method {req.method} is not enabled for model', simulator_source)

    def test_backend_and_game_ship_the_same_yeast_model(self):
        backend_path = PROJECT_ROOT / 'backend' / 'models' / 'iMM904.xml.gz'
        self.assertTrue(backend_path.is_file())
        digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest(self.yeast_model_path), digest(backend_path))

    def test_mission36_files_are_present(self):
        self.assertTrue((PROJECT_ROOT / 'code' / 'mission36.py').exists())
        self.assertTrue((PROJECT_ROOT / 'data' / 'missions' / 'mission36.md').exists())

    def test_yeast_default_fba_growth_independent_sbml_smoke(self):
        """Independently solve the bundled default iMM904 biomass LP."""
        with gzip.open(self.yeast_model_path, 'rb') as handle:
            root = ET.parse(handle).getroot()
        model = root.find(f'{{{self.CORE_NS}}}model')
        params = {
            item.attrib['id']: float(item.attrib['value'])
            for item in model.find(f'{{{self.CORE_NS}}}listOfParameters')
        }
        species = [item.attrib['id'] for item in model.find(f'{{{self.CORE_NS}}}listOfSpecies')]
        species_index = {species_id: index for index, species_id in enumerate(species)}
        reaction_nodes = list(model.find(f'{{{self.CORE_NS}}}listOfReactions'))
        reaction_ids = [
            node.attrib['id'][2:] if node.attrib['id'].startswith('R_') else node.attrib['id']
            for node in reaction_nodes
        ]
        reaction_index = {reaction_id: index for index, reaction_id in enumerate(reaction_ids)}
        matrix = lil_matrix((len(species), len(reaction_nodes)), dtype=float)
        bounds = []
        for col, reaction in enumerate(reaction_nodes):
            lb_ref = reaction.attrib[f'{{{self.FBC_NS}}}lowerFluxBound']
            ub_ref = reaction.attrib[f'{{{self.FBC_NS}}}upperFluxBound']
            bounds.append((params[lb_ref], params[ub_ref]))
            reactants = reaction.find(f'{{{self.CORE_NS}}}listOfReactants')
            products = reaction.find(f'{{{self.CORE_NS}}}listOfProducts')
            if reactants is not None:
                for ref in reactants:
                    matrix[species_index[ref.attrib['species']], col] -= float(ref.attrib.get('stoichiometry', '1'))
            if products is not None:
                for ref in products:
                    matrix[species_index[ref.attrib['species']], col] += float(ref.attrib.get('stoichiometry', '1'))

        objective_index = reaction_index['BIOMASS_SC5_notrace']
        objective = np.zeros(len(reaction_nodes))
        objective[objective_index] = -1.0
        solution = linprog(
            objective,
            A_eq=matrix.tocsr(),
            b_eq=np.zeros(len(species)),
            bounds=bounds,
            method='highs',
        )
        self.assertTrue(solution.success, solution.message)
        self.assertAlmostEqual(solution.x[objective_index], 0.287865704, places=6)

    def test_yeast_default_pfba_independent_sbml_smoke(self):
        """Independently verify the default iMM904 parsimonious optimum."""
        with gzip.open(self.yeast_model_path, 'rb') as handle:
            root = ET.parse(handle).getroot()
        model = root.find(f'{{{self.CORE_NS}}}model')
        params = {
            item.attrib['id']: float(item.attrib['value'])
            for item in model.find(f'{{{self.CORE_NS}}}listOfParameters')
        }
        species = [item.attrib['id'] for item in model.find(f'{{{self.CORE_NS}}}listOfSpecies')]
        species_index = {species_id: index for index, species_id in enumerate(species)}
        reaction_nodes = list(model.find(f'{{{self.CORE_NS}}}listOfReactions'))
        reaction_ids = [
            node.attrib['id'][2:] if node.attrib['id'].startswith('R_') else node.attrib['id']
            for node in reaction_nodes
        ]
        reaction_index = {reaction_id: index for index, reaction_id in enumerate(reaction_ids)}
        matrix = lil_matrix((len(species), len(reaction_nodes)), dtype=float)
        bounds = []
        for col, reaction in enumerate(reaction_nodes):
            lb_ref = reaction.attrib[f'{{{self.FBC_NS}}}lowerFluxBound']
            ub_ref = reaction.attrib[f'{{{self.FBC_NS}}}upperFluxBound']
            bounds.append((params[lb_ref], params[ub_ref]))
            reactants = reaction.find(f'{{{self.CORE_NS}}}listOfReactants')
            products = reaction.find(f'{{{self.CORE_NS}}}listOfProducts')
            if reactants is not None:
                for ref in reactants:
                    matrix[species_index[ref.attrib['species']], col] -= float(ref.attrib.get('stoichiometry', '1'))
            if products is not None:
                for ref in products:
                    matrix[species_index[ref.attrib['species']], col] += float(ref.attrib.get('stoichiometry', '1'))

        matrix = matrix.tocsr()
        n_reactions = len(reaction_nodes)
        biomass_index = reaction_index['BIOMASS_SC5_notrace']
        primary_objective = np.zeros(n_reactions)
        primary_objective[biomass_index] = -1.0
        primary = linprog(
            primary_objective,
            A_eq=matrix,
            b_eq=np.zeros(len(species)),
            bounds=bounds,
            method='highs',
        )
        self.assertTrue(primary.success, primary.message)
        biomass_optimum = float(primary.x[biomass_index])

        # Secondary LP: minimise sum(abs(v)) while fixing biomass at its optimum.
        secondary_objective = np.concatenate([np.zeros(n_reactions), np.ones(n_reactions)])
        a_eq = hstack([matrix, csr_matrix((len(species), n_reactions))], format='csr')
        biomass_row = np.zeros(2 * n_reactions)
        biomass_row[biomass_index] = 1.0
        a_eq = vstack([a_eq, csr_matrix(biomass_row)], format='csr')
        b_eq = np.concatenate([np.zeros(len(species)), [biomass_optimum]])
        identity = eye(n_reactions, format='csr')
        a_ub = vstack([
            hstack([identity, -identity]),
            hstack([-identity, -identity]),
        ], format='csr')
        secondary = linprog(
            secondary_objective,
            A_ub=a_ub,
            b_ub=np.zeros(2 * n_reactions),
            A_eq=a_eq,
            b_eq=b_eq,
            bounds=bounds + [(0.0, None)] * n_reactions,
            method='highs',
        )
        self.assertTrue(secondary.success, secondary.message)
        fluxes = secondary.x[:n_reactions]
        self.assertAlmostEqual(fluxes[biomass_index], 0.287865704, places=6)
        self.assertAlmostEqual(float(secondary.fun), 338.005992, places=5)
        self.assertAlmostEqual(fluxes[reaction_index['EX_glc__D_e']], -10.0, places=6)
        self.assertAlmostEqual(fluxes[reaction_index['EX_o2_e']], -2.0, places=6)
        self.assertAlmostEqual(fluxes[reaction_index['EX_etoh_e']], 15.815475, places=5)
        self.assertAlmostEqual(fluxes[reaction_index['EX_co2_e']], 18.021084, places=5)


if __name__ == '__main__':
    unittest.main()
