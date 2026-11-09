"""Run real Backend migration/API tests from this checkout or a separate snapshot."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from dev import COMPOSE, ENV, ROOT, require_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT,
                        help='Root containing src/backend and its integration tests')
    args = parser.parse_args()
    source = args.source_root.resolve()
    required = ['src/backend/requirements-dev.txt', 'src/backend/app/main.py',
                'src/backend/alembic.ini', 'tests/integration/backend/conftest.py',
                'docs/contracts/mvp-openapi.json']
    missing = [path for path in required if not (source / path).is_file()]
    if missing:
        print('BLOCKED: chưa có Backend cần kiểm thử: ' + ', '.join(missing), file=sys.stderr)
        return 2
    require_env()
    (ROOT / 'build/qa').mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'QA_SOURCE_ROOT': str(source)}
    command = ['docker', 'compose', '--project-name', 'app05-ngoc-qa', '--env-file', str(ENV),
               '-f', str(COMPOSE), '-f', str(ROOT / 'infrastructure/docker/compose.backend-qa.yml')]
    try:
        subprocess.run([*command, 'up', '-d', '--wait', '--wait-timeout', '120', 'db-test'],
                       cwd=ROOT, env=env, check=True, timeout=180)
        result = subprocess.run([*command, 'run', '--build', '--rm', 'backend-qa'],
                                cwd=ROOT, env=env, timeout=900)
        return result.returncode
    finally:
        # Stop just the disposable test DB; leave development db/mqtt untouched.
        subprocess.run([*command, 'stop', 'db-test'], cwd=ROOT, env=env, timeout=60)
        subprocess.run([*command, 'rm', '-f', 'db-test'], cwd=ROOT, env=env, timeout=60)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.SubprocessError):
        print('FAIL: không chạy được Backend QA; xem trạng thái Docker và cấu hình.', file=sys.stderr)
        sys.exit(1)
