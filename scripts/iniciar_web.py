"""Entrada local portátil: prepara o projeto e abre Django em localhost."""

import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--porta', type=int, default=8000)
    args = parser.parse_args()
    if not 1024 <= args.porta <= 65535:
        parser.error('Escolha uma porta de 1024 a 65535.')
    raiz = Path(__file__).resolve().parent.parent
    subprocess.run([sys.executable, 'scripts/preparar_ambiente.py'], cwd=raiz, check=True)
    subprocess.run([sys.executable, 'manage.py', 'preparar_servidor'], cwd=raiz, check=True)
    print(f'Abra http://127.0.0.1:{args.porta}/entrar/ . Ctrl+C encerra o servidor.', flush=True)
    return subprocess.call([sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{args.porta}', '--noreload'], cwd=raiz)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError:
        print('A preparação falhou. Corrija a mensagem acima antes de iniciar o servidor.', file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        pass
