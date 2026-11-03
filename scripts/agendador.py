"""Um supervisor leve de rotinas; encerra também o subprocesso ao receber SIGTERM."""

import os
from pathlib import Path
import signal
import subprocess
import sys
from threading import Event

PARAR = Event()
PROCESSO = None


def encerrar(sig, frame):
    PARAR.set()
    if PROCESSO is not None and PROCESSO.poll() is None:
        PROCESSO.terminate()


def main():
    global PROCESSO
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from sauron_web.ambiente import carregar_ambiente
    carregar_ambiente(Path(__file__).resolve().parents[1]/".env")
    signal.signal(signal.SIGTERM, encerrar)
    signal.signal(signal.SIGINT, encerrar)
    intervalo = int(os.getenv("SAURON_ROTINAS_INTERVALO", "3600"))
    if intervalo < 1:
        raise ValueError("Intervalo de rotinas precisa ser positivo.")
    pasta = Path(__file__).resolve().parent.parent
    while not PARAR.is_set():
        comando = [sys.executable, "manage.py", "rotinas"]
        if os.getenv("SAURON_ROTINAS_SEM_REDE", "0") == "1":
            comando.append("--sem-rede")
        PROCESSO = subprocess.Popen(comando, cwd=pasta)
        try:
            codigo = PROCESSO.wait(timeout=300)
            print(f"[agendador] rotina encerrada, código={codigo}", flush=True)
        except subprocess.TimeoutExpired:
            PROCESSO.terminate()
            try:
                PROCESSO.wait(timeout=10)
            except subprocess.TimeoutExpired:
                PROCESSO.kill()
                PROCESSO.wait()
            print("[agendador] rotina interrompida: limite de 300 segundos", flush=True)
        finally:
            PROCESSO = None
        PARAR.wait(intervalo)


if __name__ == "__main__":
    main()
