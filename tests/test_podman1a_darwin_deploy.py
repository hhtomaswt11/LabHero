from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Podman1ADarwinDeployTests(unittest.TestCase):
    def test_local_docker_proxy_is_preserved(self):
        nginx = (ROOT / 'deploy' / 'nginx.conf').read_text(encoding='utf-8')
        self.assertIn('proxy_pass http://backend:8000/;', nginx)

    def test_podman_proxy_uses_shared_pod_localhost(self):
        nginx = (ROOT / 'deploy' / 'nginx.podman.conf').read_text(encoding='utf-8')
        self.assertIn('location /api/', nginx)
        self.assertIn('proxy_pass http://127.0.0.1:8000/;', nginx)
        self.assertNotIn('proxy_pass http://backend:8000/;', nginx)
        self.assertIn('proxy_read_timeout 60s;', nginx)

    def test_frontend_dockerfile_defaults_to_local_docker_nginx(self):
        dockerfile = (ROOT / 'deploy' / 'Dockerfile.frontend').read_text(encoding='utf-8')
        self.assertIn('ARG NGINX_CONF=deploy/nginx.conf', dockerfile)
        self.assertIn('COPY ${NGINX_CONF} /etc/nginx/conf.d/default.conf', dockerfile)

    def test_container_base_images_are_fully_qualified_for_podman(self):
        backend = (ROOT / 'backend' / 'Dockerfile').read_text(encoding='utf-8')
        frontend = (ROOT / 'deploy' / 'Dockerfile.frontend').read_text(encoding='utf-8')

        self.assertIn('FROM docker.io/library/python:3.10-slim', backend)
        self.assertIn('FROM docker.io/library/python:3.11-slim AS bundler', frontend)
        self.assertIn('FROM docker.io/library/nginx:1.27-alpine', frontend)
        self.assertNotRegex(backend, r'(?m)^FROM\s+python:')
        self.assertNotRegex(frontend, r'(?m)^FROM\s+(?:python|nginx):')

    def test_deploy_script_builds_backend_from_backend_context(self):
        script = (ROOT / 'deploy.sh').read_text(encoding='utf-8')
        self.assertRegex(script, r'podman build -t "\$BACKEND_IMAGE" ./backend')

    def test_deploy_script_builds_frontend_with_podman_nginx(self):
        script = (ROOT / 'deploy.sh').read_text(encoding='utf-8')
        self.assertIn('-f deploy/Dockerfile.frontend', script)
        self.assertIn('--build-arg NGINX_CONF=deploy/nginx.podman.conf', script)

    def test_deploy_script_uses_one_pod_and_only_publishes_frontend_port(self):
        script = (ROOT / 'deploy.sh').read_text(encoding='utf-8')
        self.assertIn('podman pod create', script)
        self.assertIn('-p "${HOST_PORT}:80"', script)
        self.assertGreaterEqual(script.count('--pod "$POD_NAME"'), 2)
        self.assertNotIn('${HOST_PORT}:8000', script)

    def test_deploy_script_starts_backend_before_frontend(self):
        script = (ROOT / 'deploy.sh').read_text(encoding='utf-8')
        backend = script.index('echo "[LabHero] Starting backend..."')
        frontend = script.index('echo "[LabHero] Starting frontend..."')
        self.assertLess(backend, frontend)

    def test_deploy_script_uses_restart_policy(self):
        script = (ROOT / 'deploy.sh').read_text(encoding='utf-8')
        self.assertEqual(2, script.count('--restart=unless-stopped'))

    def test_deploy_script_waits_on_same_origin_health_endpoint(self):
        script = (ROOT / 'deploy.sh').read_text(encoding='utf-8')
        self.assertIn('http://127.0.0.1:${HOST_PORT}/api/health', script)
        self.assertIn('curl -fsS "$HEALTH_URL"', script)


    def test_deploy_script_smoke_tests_teacher_probe_and_both_metabolic_models(self):
        script = (ROOT / 'deploy.sh').read_text(encoding='utf-8')
        self.assertIn('/teacher-auth', script)
        self.assertIn('AUTH_PROBE_UNAUTH_STATUS=', script)
        self.assertIn('AUTH_PROBE_AUTH_STATUS=', script)
        self.assertIn('"model_id":"ecoli_core"', script)
        self.assertIn('"method":"FBA"', script)
        self.assertIn('"objective":"BIOMASS_Ecoli_core_w_GAM"', script)
        self.assertIn('"model_id":"yeast_iMM904"', script)
        self.assertIn('"method":"pFBA"', script)
        self.assertIn('"objective":"BIOMASS_SC5_notrace"', script)
        self.assertGreaterEqual(script.count('"status"[[:space:]]*:[[:space:]]*"ok"'), 2)

    def test_podman_nginx_keeps_cache_policy(self):
        nginx = (ROOT / 'deploy' / 'nginx.podman.conf').read_text(encoding='utf-8')
        self.assertRegex(nginx, r'location\s*=\s*/index\.html')
        self.assertIn('public, max-age=31536000, immutable', nginx)

    def test_docs_keep_docker_local_and_podman_production_distinct(self):
        readme = (ROOT / 'deploy' / 'README.md').read_text(encoding='utf-8')
        self.assertIn('Darwin / Podman production path', readme)
        self.assertIn('deploy/docker-compose.yml', readme)
        self.assertIn('./deploy.sh', readme)
        self.assertIn('deploy/nginx.podman.conf', readme)


if __name__ == '__main__':
    unittest.main()
