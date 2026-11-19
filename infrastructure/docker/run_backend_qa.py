"""Run the target branch's own dependencies and tests in an isolated container."""
from pathlib import Path
import json
import os
import platform
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

SOURCE = Path('/target')
WORK = Path('/work')
REQUIRED = ('src/backend/requirements-dev.txt', 'src/backend/alembic.ini',
            'src/backend/app/main.py', 'tests/integration/backend/conftest.py',
            'docs/testing/fixtures/mvp-normal.json', 'docs/contracts/mvp-openapi.json')


def redact(content):
    for name in ('DATABASE_URL', 'TEST_DATABASE_URL'):
        url = os.environ.get(name, '')
        if url:
            content = content.replace(url, '[DATABASE_URL]')
            password = urlsplit(url).password
            if password:
                content = content.replace(password, '[REDACTED]')
    return content


def run(command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=300)
    print(redact(result.stdout), end='')
    print(redact(result.stderr), end='', file=sys.stderr)
    return result


def main():
    missing = [path for path in REQUIRED if not (SOURCE / path).is_file()]
    if missing:
        print('BLOCKED: Backend chưa sẵn sàng. Thiếu: ' + ', '.join(missing), file=sys.stderr)
        return 2
    for relative in ('src/backend', 'tests/integration/backend', 'docs/testing/fixtures', 'docs/contracts'):
        shutil.copytree(SOURCE / relative, WORK / relative, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('.env', '.venv', '__pycache__', '.pytest_cache'))
    shutil.copytree('/extra-tests', WORK / 'tests/integration/backend', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache'))
    backend = WORK / 'src/backend'
    # Reuse dependency versions selected by Backend owner; no QA-specific libraries.
    installed = run([sys.executable, '-m', 'pip', 'install', '--no-cache-dir',
                     '-r', 'requirements-dev.txt'], backend)
    if installed.returncode:
        return installed.returncode
    resolved = run([sys.executable, '-m', 'pip', 'freeze'], backend)
    Path('/reports/backend-requirements-resolved.txt').write_text(redact(resolved.stdout))
    Path('/reports/environment.json').write_text(json.dumps({
        'python': platform.python_version(), 'platform': platform.platform()}, indent=2))
    result = run([sys.executable, '-m', 'pytest', '-v', '-p', 'no:cacheprovider',
                  '--junitxml=/reports/backend-junit.xml'], backend)
    report = Path('/reports/backend-junit.xml')
    if report.exists():
        report.write_text(redact(report.read_text()))
    return result.returncode


if __name__ == '__main__':
    try:
        sys.exit(main())
    except subprocess.SubprocessError:
        print('FAIL: cài dependencies hoặc chạy test Backend không thành công.', file=sys.stderr)
        sys.exit(1)
