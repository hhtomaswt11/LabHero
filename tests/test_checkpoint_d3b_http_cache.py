import hashlib
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FINGERPRINT_SCRIPT = ROOT / 'deploy' / 'fingerprint_web_bundle.py'
DOCKERFILE = ROOT / 'deploy' / 'Dockerfile.frontend'
NGINX = ROOT / 'deploy' / 'nginx.conf'


def _load_fingerprint_module():
    spec = importlib.util.spec_from_file_location('labhero_fingerprint_web_bundle', FINGERPRINT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CheckpointD3BHttpCacheTests(unittest.TestCase):
    def test_fingerprint_helper_renames_archive_from_its_content_hash(self):
        module = _load_fingerprint_module()
        payload = b'LabHero deterministic browser archive\n'
        expected_hash = hashlib.sha256(payload).hexdigest()[:16]

        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp)
            (web / 'src.tar.gz').write_bytes(payload)
            (web / 'index.html').write_text(
                'await platform.fopen("src.tar.gz", "rb")',
                encoding='utf-8',
            )

            final_archive = module.fingerprint_web_bundle(web)

            self.assertEqual(f'src.{expected_hash}.tar.gz', final_archive.name)
            self.assertEqual(payload, final_archive.read_bytes())
            self.assertFalse((web / 'src.tar.gz').exists())
            html = (web / 'index.html').read_text(encoding='utf-8')
            self.assertIn(final_archive.name, html)
            self.assertNotIn('src.tar.gz', html)

    def test_fingerprint_helper_is_idempotent_after_successful_build(self):
        module = _load_fingerprint_module()
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp)
            (web / 'src.tar.gz').write_bytes(b'archive')
            (web / 'index.html').write_text('src.tar.gz', encoding='utf-8')

            first = module.fingerprint_web_bundle(web)
            second = module.fingerprint_web_bundle(web)
            self.assertEqual(first, second)

    def test_fingerprint_helper_fails_closed_if_pygbag_html_contract_changes(self):
        module = _load_fingerprint_module()
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp)
            (web / 'src.tar.gz').write_bytes(b'archive')
            (web / 'index.html').write_text('different-archive-name.tar.gz', encoding='utf-8')

            with self.assertRaises(RuntimeError):
                module.fingerprint_web_bundle(web)
            self.assertTrue((web / 'src.tar.gz').is_file())

    def test_frontend_build_fingerprints_after_pygbag_and_before_nginx_copy(self):
        dockerfile = DOCKERFILE.read_text(encoding='utf-8')
        build_pos = dockerfile.index('python -m pygbag --build --ume_block 0 .')
        fingerprint_pos = dockerfile.index('python deploy/fingerprint_web_bundle.py build/web')
        copy_pos = dockerfile.index('COPY --from=bundler /src/build/web/ /usr/share/nginx/html/')
        self.assertLess(build_pos, fingerprint_pos)
        self.assertLess(fingerprint_pos, copy_pos)

    def test_nginx_keeps_entry_point_fresh_and_hashed_archive_immutable(self):
        nginx = NGINX.read_text(encoding='utf-8')

        self.assertRegex(
            nginx,
            r'location\s*=\s*/index\.html\s*\{[^}]*Cache-Control\s+"no-cache"',
        )
        self.assertRegex(
            nginx,
            r'location\s+~\s+"\^/src\\\.\[0-9a-f\]\{16\}\\\.tar\\\.gz\$"\s*\{'
            r'[^}]*Cache-Control\s+"public, max-age=31536000, immutable"',
        )

    def test_api_proxy_contract_is_unchanged(self):
        nginx = NGINX.read_text(encoding='utf-8')
        self.assertIn('location /api/', nginx)
        self.assertIn('proxy_pass http://backend:8000/;', nginx)
        self.assertIn('proxy_read_timeout 60s;', nginx)
        self.assertIn('proxy_connect_timeout 10s;', nginx)

    def test_deploy_docs_describe_versioned_archive_rollout(self):
        readme = (ROOT / 'deploy' / 'README.md').read_text(encoding='utf-8')
        self.assertIn('src.<sha256>.tar.gz', readme)
        self.assertIn('content-addressed game archive', readme)
        self.assertNotIn(
            'players will keep loading the cached bundle from their browser',
            readme,
        )


if __name__ == '__main__':
    unittest.main()
