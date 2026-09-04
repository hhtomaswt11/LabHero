import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'


class TeacherAccessTitleTests(unittest.TestCase):
    def test_shift_t_entry_exists_only_in_title_game_loop(self):
        game = (ROOT / 'LabHero.py').read_text(encoding='utf-8')
        self.assertIn('pygame.K_t and (event.mod & pygame.KMOD_SHIFT)', game)
        self.assertIn('await self.teacher_access.update()', game)
        self.assertIn('await self.run_teacher_preview(request)', game)
        self.assertIn('while True:', game)
        intro = (CODE / 'intro.py').read_text(encoding='utf-8')
        self.assertNotIn('Teacher Access', intro)
        self.assertNotIn('Teacher Preview', intro)

    def test_teacher_access_has_normal_easy_buttons_and_canonical_mission_input(self):
        source = (CODE / 'teacher_access.py').read_text(encoding='utf-8')
        self.assertIn('Teacher Access', source)
        self.assertIn('Mission number: ', source)
        self.assertIn('Open Normal Preview', source)
        self.assertIn('Open Easy Preview', source)
        self.assertIn('Easy keeps canonical IDs', source)
        self.assertIn('password=True', source)

    def test_web_credentials_are_validated_by_server_endpoint(self):
        source = (CODE / 'teacher_access.py').read_text(encoding='utf-8')
        self.assertIn('TEACHER_AUTH_ENDPOINT = "/teacher-auth"', source)
        self.assertIn("request.open('HEAD', endpoint, true)", source)
        self.assertIn("request.setRequestHeader('Authorization', `Basic ${token}`)", source)
        self.assertIn('new XMLHttpRequest()', source)
        self.assertNotIn('teacher_labhero_uminho', source)
        self.assertNotIn('LABHERO_TEACHER_PASSWORD =', source)

    def test_desktop_credentials_come_only_from_environment(self):
        source = (CODE / 'teacher_access.py').read_text(encoding='utf-8')
        self.assertIn('os.environ.get("LABHERO_TEACHER_PASSWORD")', source)
        self.assertIn('hmac.compare_digest', source)

    def test_preview_namespace_is_cleared_before_and_after_and_student_namespace_restored(self):
        source = (ROOT / 'LabHero.py').read_text(encoding='utf-8')
        method = source[source.index('async def run_teacher_preview'):source.index('async def intro_run')]
        self.assertGreaterEqual(method.count('clear_active_persistent_storage()'), 2)
        self.assertIn("set_save_namespace('teacher')", method)
        self.assertIn('set_save_namespace(None)', method)
        self.assertIn('clear_memstore()', method)


    def test_teacher_form_releases_web_text_focus_before_authentication(self):
        source = (CODE / 'teacher_access.py').read_text(encoding='utf-8')
        self.assertIn('pygame.key.stop_text_input()', source)
        self.assertIn('document.activeElement', source)
        self.assertIn("typeof active.blur === 'function'", source)
        self.assertIn('await _settle_teacher_text_input_focus()', source)

        update_start = source.index('    async def update(self):')
        update_source = source[update_start:]
        self.assertLess(
            update_source.index('await run_menu(menu, self.display_surface)'),
            update_source.index('await _settle_teacher_text_input_focus()'),
        )
        self.assertLess(
            update_source.index('await _settle_teacher_text_input_focus()'),
            update_source.index('await authenticate_teacher_credentials('),
        )

    def test_teacher_auth_uses_callback_polling_not_direct_js_promise_await(self):
        source = (CODE / 'teacher_access.py').read_text(encoding='utf-8')
        self.assertIn('new XMLHttpRequest()', source)
        self.assertIn("request.open('HEAD', endpoint, true)", source)
        self.assertIn('request.timeout = 8000', source)
        self.assertIn('window.__labheroTeacherAuthStatus', source)
        self.assertIn('status = int(poll_auth())', source)
        self.assertIn('await asyncio.sleep(0.05)', source)
        self.assertNotIn('await auth_fetch(', source)
        self.assertNotIn('await window.fetch(', source)
        self.assertIn('Teacher authentication timed out. Try again.', source)


    def test_successful_teacher_authentication_is_reused_only_in_memory(self):
        source = (CODE / 'teacher_access.py').read_text(encoding='utf-8')
        self.assertIn('self.session_authenticated = False', source)
        self.assertIn('self.session_authenticated = True', source)
        self.assertIn('Teacher session authenticated for this page.', source)
        self.assertIn('End Teacher Session', source)
        self.assertIn('pygame.key.start_text_input()', source)
        session_source = source[source.index('class TeacherAccessMenu:'):]
        self.assertNotIn('window.localStorage', session_source)
        self.assertNotIn('save_file(', session_source)

    def test_authenticated_teacher_session_can_switch_mission_without_reauth(self):
        game = (ROOT / 'LabHero.py').read_text(encoding='utf-8')
        settings = (CODE / 'menu_2.py').read_text(encoding='utf-8')
        level = (CODE / 'level.py').read_text(encoding='utf-8')

        self.assertIn("while current_request is not None:", game)
        self.assertIn("'teacher_switch_request'", game)
        self.assertIn("menu.add.button('Change Teacher Mission', teacher_switch)", settings)
        self.assertIn("'Switch to Normal Mission'", settings)
        self.assertIn("'Switch to Easy Mission'", settings)
        self.assertIn("source='preview'", settings)
        self.assertIn('self.player.teacher_switch_request = request', settings)
        self.assertIn('self.player.teacher_switch_request = None', level)
        self.assertIn(
            'Student save is isolated. T reopens target; M can change mission.',
            level,
        )

    def test_teacher_access_module_has_no_literal_password_secret(self):
        tree = ast.parse((CODE / 'teacher_access.py').read_text(encoding='utf-8'))
        strings = [
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        suspicious = [value for value in strings if 'teacher_labhero_uminho' in value.lower()]
        self.assertEqual(suspicious, [])


if __name__ == '__main__':
    unittest.main()
