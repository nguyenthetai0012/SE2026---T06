"""Local QA infrastructure only; no application scaffold is assumed."""
import argparse
from pathlib import Path
import secrets
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / '.env'
COMPOSE = ROOT / 'infrastructure/docker/compose.yml'


def compose(*args, input_text=None, capture=False):
    command = ['docker', 'compose', '--project-name', 'app05-ngoc-qa',
               '--env-file', str(ENV), '-f', str(COMPOSE), *args]
    return subprocess.run(command, cwd=ROOT, input=input_text, text=True,
                          capture_output=capture, check=True, timeout=180)


def require_env():
    if not ENV.exists():
        raise ValueError('Thiếu .env. Chạy: python3 tools/scripts/dev.py init')
    values = dict(line.split('=', 1) for line in ENV.read_text().splitlines()
                  if line and not line.startswith('#') and '=' in line)
    password = values.get('POSTGRES_PASSWORD', '')
    if not password or password.startswith('REPLACE_'):
        raise ValueError('POSTGRES_PASSWORD chưa được cấu hình; không dùng placeholder.')


def smoke():
    result = compose('exec', '-T', 'db', 'psql', '-XAt', '-v', 'ON_ERROR_STOP=1',
                     '-U', 'app05_qa', '-d', 'app05_qa', '-c', 'SELECT 1', capture=True)
    if result.stdout.strip() != '1':
        raise ValueError('PostgreSQL smoke thất bại.')
    topic = 'qa/smoke/' + str(uuid.uuid4())
    try:
        compose('exec', '-T', 'mqtt', 'mosquitto_pub', '-h', 'localhost',
                '-t', topic, '-m', 'app05-smoke', '-q', '1', '-r', capture=True)
        result = compose('exec', '-T', 'mqtt', 'mosquitto_sub', '-h', 'localhost',
                         '-t', topic, '-C', '1', '-W', '5', '-q', '1', capture=True)
        if result.stdout.strip() != 'app05-smoke':
            raise ValueError('MQTT round-trip thất bại.')
    finally:
        compose('exec', '-T', 'mqtt', 'mosquitto_pub', '-h', 'localhost',
                '-t', topic, '-n', '-q', '1', '-r', capture=True)
    print('PASS: PostgreSQL SELECT 1 và MQTT publish/subscribe. Chưa kiểm tra ứng dụng.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'config', 'up', 'smoke', 'status', 'down'])
    args = parser.parse_args()
    if args.command == 'init':
        # Exclusive creation protects existing developer configuration.
        try:
            with ENV.open('x') as output:
                ENV.chmod(0o600)
                output.write('POSTGRES_PASSWORD=' + secrets.token_urlsafe(32) + '\nMQTT_PORT=1883\n')
            print('Đã tạo .env với mật khẩu ngẫu nhiên; không in giá trị bí mật.')
        except FileExistsError:
            print('.env đã tồn tại; giữ nguyên.')
        return
    require_env()
    if args.command == 'config':
        compose('config', '--quiet')
        print('PASS: cấu hình Compose hợp lệ (không in secrets).')
    elif args.command == 'up':
        compose('up', '-d', '--wait', '--wait-timeout', '120', 'db', 'mqtt')
    elif args.command == 'smoke':
        smoke()
    elif args.command == 'status':
        compose('ps')
    else:
        compose('down')  # Deliberately retain volumes.


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        # subprocess output/env may contain credentials; do not echo them.
        print(str(error) if isinstance(error, ValueError) else
              'FAIL: lệnh Docker không thành công; kiểm tra Docker/service/config.', file=sys.stderr)
        sys.exit(1)
