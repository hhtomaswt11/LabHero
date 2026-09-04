from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))


def load_teacher_mode():
    path = ROOT / 'code' / 'teacher_mode.py'
    spec = importlib.util.spec_from_file_location('teacher_mode_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Teacher1AProtectedAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.teacher_mode = load_teacher_mode()

    def test_public_root_query_cannot_activate_teacher_mode(self):
        self.assertIsNone(
            self.teacher_mode.parse_teacher_web_request('/', '?teacher=1&mission=17')
        )

    def test_protected_teacher_path_accepts_mission_selector(self):
        request = self.teacher_mode.parse_teacher_web_request('/teacher/', '?mission=17')
        self.assertEqual('17', request['mission_id'])
        self.assertEqual('normal', request['campaign_mode'])
        self.assertEqual('web', request['source'])

    def test_teacher_path_still_validates_mission_range(self):
        self.assertIsNone(
            self.teacher_mode.parse_teacher_web_request('/teacher/', '?mission=99')
        )

    def test_desktop_teacher_flags_remain_supported(self):
        request = self.teacher_mode.parse_teacher_argv(['--teacher', '--mission', '36'])
        self.assertEqual('36', request['mission_id'])
        self.assertEqual('normal', request['campaign_mode'])
        self.assertEqual('desktop', request['source'])

    def test_podman_nginx_protects_teacher_entry_but_not_pygbag_assets(self):
        nginx = (ROOT / 'deploy' / 'nginx.podman.conf').read_text(encoding='utf-8')
        self.assertIn('location = /teacher/', nginx)
        self.assertIn('location = /teacher/index.html', nginx)
        self.assertIn('location ^~ /teacher/', nginx)
        self.assertEqual(nginx.count('auth_basic "LabHero Teacher";'), 3)
        self.assertEqual(
            nginx.count('auth_basic_user_file /etc/nginx/.htpasswd;'), 3
        )
        asset_start = nginx.index('location ^~ /teacher/')
        asset_end = nginx.index('}', asset_start)
        self.assertNotIn('auth_basic', nginx[asset_start:asset_end])
        self.assertIn('rewrite ^/teacher/(.*)$ /$1 break;', nginx[asset_start:asset_end])


    def test_shift_t_auth_probe_is_exact_and_basic_auth_protected(self):
        nginx = (ROOT / 'deploy' / 'nginx.podman.conf').read_text(encoding='utf-8')
        start = nginx.index('location = /teacher-auth')
        end = nginx.index('}', start)
        block = nginx[start:end]
        self.assertIn('auth_basic "LabHero Teacher";', block)
        self.assertIn('auth_basic_user_file /etc/nginx/.htpasswd;', block)
        self.assertIn('try_files /index.html =404;', block)
        self.assertIn('Cache-Control "no-store"', block)


    def test_local_docker_nginx_exposes_same_teacher_auth_contract(self):
        nginx = (ROOT / 'deploy' / 'nginx.conf').read_text(encoding='utf-8')
        self.assertIn('location = /teacher-auth', nginx)
        self.assertIn('location = /teacher/', nginx)
        self.assertIn('location = /teacher/index.html', nginx)
        self.assertIn('location ^~ /teacher/', nginx)
        self.assertEqual(nginx.count('auth_basic "LabHero Teacher";'), 3)
        self.assertEqual(
            nginx.count('auth_basic_user_file /etc/nginx/.htpasswd;'), 3
        )

        compose = (ROOT / 'deploy' / 'docker-compose.yml').read_text(encoding='utf-8')
        self.assertIn(
            '${HOME}/.config/labhero/teacher.htpasswd:/etc/nginx/.htpasswd:ro',
            compose,
        )

    def test_public_root_is_not_basic_auth_protected(self):
        nginx = (ROOT / 'deploy' / 'nginx.podman.conf').read_text(encoding='utf-8')
        root_start = nginx.index('location = / {')
        root_end = nginx.index('}', root_start)
        self.assertNotIn('auth_basic', nginx[root_start:root_end])

    def test_deploy_requires_teacher_password_and_hashes_outside_repo(self):
        script = (ROOT / 'deploy.sh').read_text(encoding='utf-8')
        self.assertIn('LABHERO_TEACHER_PASSWORD', script)
        self.assertIn('openssl passwd -apr1 -stdin', script)
        self.assertIn('${HOME}/.config/labhero', script)
        self.assertIn('chmod 644 "$TEACHER_HTPASSWD_FILE"', script)
        self.assertIn('/etc/nginx/.htpasswd:ro', script)

    def test_no_teacher_password_is_hardcoded(self):
        script = (ROOT / 'deploy.sh').read_text(encoding='utf-8')
        self.assertIn('TEACHER_PASSWORD="${LABHERO_TEACHER_PASSWORD:-}"', script)
        self.assertNotIn('changeme', script.lower())
        self.assertFalse((ROOT / 'deploy' / '.htpasswd').exists())
        self.assertFalse((ROOT / 'teacher.htpasswd').exists())
        self.assertIn('UNAUTH_STATUS=', script)
        self.assertIn('AUTH_STATUS=', script)
        self.assertIn('TEACHER_ARCHIVE=', script)
        self.assertIn('TEACHER_AUTH_URL=', script)
        self.assertIn('AUTH_PROBE_UNAUTH_STATUS=', script)
        self.assertIn('AUTH_PROBE_AUTH_STATUS=', script)
        self.assertIn('ASSET_STATUS=', script)
        self.assertIn('Expected unauthenticated entry HTTP 401', script)
        self.assertIn('Expected authenticated entry HTTP 200', script)
        self.assertIn('Expected unauthenticated Pygbag teacher asset HTTP 200', script)

    def test_docs_use_protected_teacher_url(self):
        readme = (ROOT / 'deploy' / 'README.md').read_text(encoding='utf-8')
        self.assertIn('/teacher/?mission=17', readme)
        self.assertIn("LABHERO_TEACHER_PASSWORD", readme)
        self.assertIn('/?teacher=1&mission=17', readme)
        self.assertIn('does **not** activate Teacher Mode', readme)


if __name__ == '__main__':
    unittest.main()
