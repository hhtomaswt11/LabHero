import ast
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'


class CheckpointBInfrastructureTests(unittest.TestCase):
    def test_carter_reveal_is_anchored_to_current_tiled_mission03_object(self):
        root = ET.parse(ROOT / 'data' / 'map_lb.tmx').getroot()
        player_group = next(
            group for group in root.findall('objectgroup')
            if group.get('name') == 'Player'
        )
        carter = next(obj for obj in player_group.findall('object') if obj.get('name') == 'Mission03')
        self.assertGreater(float(carter.get('y')), 2000.0)  # redesigned-map checkpoint

        source = (CODE / 'level.py').read_text(encoding='utf-8')
        self.assertIn("if obj.name == 'Mission03':", source)
        self.assertIn('carter_reveal_pos = (obj.x, obj.y)', source)
        self.assertRegex(source, r'CarterRevealSprite\(\s*pos\s*=\s*carter_reveal_pos')
        self.assertNotIn('pos = (1216, 1024)', source)

    def test_carter_reveal_still_depends_only_on_mission06_completion(self):
        source = (CODE / 'sprites.py').read_text(encoding='utf-8')
        start = source.index('class CarterRevealSprite')
        block = source[start: start + 1200]
        self.assertIn("if '06' in self.player.missions_completed:", block)
        self.assertIn('self.image = self.evil_surf', block)
        self.assertIn('self.image = self.transparent_surf', block)

    def test_live_simulation_callback_is_async_and_schedules_one_task(self):
        source = (CODE / 'window.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        data_fun = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == 'data_fun'
        )
        data_source = ast.get_source_segment(source, data_fun)
        self.assertIn('await asyncio.to_thread(run_simul)', data_source)
        self.assertIn('await run_simul_remote_async(BACKEND_URL)', data_source)

        self.assertIn('task = asyncio.create_task(data_fun())', source)
        self.assertIn('bound_sweep_input_data = copy.deepcopy(', source)
        self.assertIn('if simulation_running:', source)
        self.assertNotIn('self.results = run_simul_remote(BACKEND_URL)', source)
        self.assertNotRegex(source, r'(?m)^\s*self\.results\s*=\s*run_simul\(\)')

    def test_live_bound_sweep_is_nonblocking_on_desktop_and_browser(self):
        source = (CODE / 'window.py').read_text(encoding='utf-8')
        self.assertIn('await run_bound_sweep_remote_async(', source)
        self.assertRegex(
            source,
            r'await asyncio\.to_thread\(\s*run_bound_sweep,\s*bound_sweep_input_data,\s*model_id=self\.model_id',
        )
        self.assertNotRegex(source, r'(?m)^\s*bound_sweep_data\s*=\s*run_bound_sweep_remote\(')

    def test_browser_http_path_uses_pyfetch_and_shared_result_normaliser(self):
        source = (CODE / 'simulation.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        funcs = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        async_http = ast.get_source_segment(source, funcs['_http_post_json_async'])
        async_sim = ast.get_source_segment(source, funcs['run_simul_remote_async'])
        sync_sim = ast.get_source_segment(source, funcs['run_simul_remote'])

        self.assertIn('from pyodide.http import pyfetch', async_http)
        self.assertNotIn('XMLHttpRequest', async_http)
        self.assertIn('_normalise_remote_simulation_response', async_sim)
        self.assertIn('_normalise_remote_simulation_response', sync_sim)

    def test_remote_sweep_requests_are_sequential_not_parallel(self):
        source = (CODE / 'simulation.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        async_sweep = next(
            node for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == 'run_bound_sweep_remote_async'
        )
        block = ast.get_source_segment(source, async_sweep)
        self.assertIn('for bound_value in', block)
        self.assertIn('await _http_post_json_async', block)
        self.assertNotIn('asyncio.gather', block)
        self.assertNotIn('create_task', block)


if __name__ == '__main__':
    unittest.main()
