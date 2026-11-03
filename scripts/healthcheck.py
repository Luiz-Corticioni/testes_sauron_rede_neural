"""Liveness HTTP + sinal de vida do agendador; nenhum acesso ao ORM."""
import argparse
import os
from pathlib import Path
import sys
from urllib.request import urlopen

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inventario.infraestrutura.heartbeat import verificar_heartbeat


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--somente-rotina",action="store_true")
    args=parser.parse_args()
    pasta=Path(os.getenv("SAURON_DATA_DIR","dados"))
    if not verificar_heartbeat(pasta/"ultima_rotina.json",int(os.getenv("SAURON_ROTINAS_INTERVALO","3600"))):
        return 1
    if not args.somente_rotina:
        try:
            with urlopen("http://127.0.0.1:8000/api/saude/",timeout=3) as resposta:
                if resposta.status!=200:
                    return 1
        except OSError:
            return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())

