"""Check repository documentation/JSON without third-party packages."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
IGNORED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'build', 'dist', 'coverage'}


def main():
    errors = []
    count = 0
    for path in ROOT.rglob('*'):
        if set(path.relative_to(ROOT).parts) & IGNORED or not path.is_file():
            continue
        if path.suffix not in ('.json', '.md', '.py'):
            continue
        count += 1
        try:
            content = path.read_text(encoding='utf-8')
            if path.suffix == '.json':
                json.loads(content)
            elif path.suffix == '.py':
                ast.parse(content, filename=str(path.relative_to(ROOT)))
            else:
                for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', content):
                    if '://' in target or target.startswith(('mailto:', '#', '/')):
                        continue
                    relative = target.split('#', 1)[0]
                    if relative and not (path.parent / relative).exists():
                        errors.append(f'{path.relative_to(ROOT)}: broken link {target}')
        except (ValueError, SyntaxError, UnicodeError) as error:
            errors.append(f'{path.relative_to(ROOT)}: {type(error).__name__}')
    for options in ([], ['--cached']):
        diff = subprocess.run(['git', 'diff', *options, '--check'], cwd=ROOT,
                              capture_output=True, text=True)
        if diff.returncode:
            errors.append('git diff ' + ' '.join([*options, '--check']) + ' failed')
    tracked = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    if '.env' in tracked:
        errors.append('.env must not be tracked')
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f'PASS: {count} Markdown/JSON/Python files; links, JSON, syntax and diff checked.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
