"""Travas entre processos e substituição atômica de arquivos JSON."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


@contextmanager
def trava_arquivo(caminho):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a+b") as arquivo:
        if os.name == "nt":
            import msvcrt

            if arquivo.tell() == 0:
                arquivo.write(b"0")
                arquivo.flush()
            arquivo.seek(0)
            msvcrt.locking(arquivo.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                arquivo.seek(0)
                msvcrt.locking(arquivo.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(arquivo.fileno(), fcntl.LOCK_UN)


def salvar_json_atomico(caminho, dados):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with NamedTemporaryFile("w", dir=caminho.parent, delete=False, encoding="utf-8") as f:
            temporario = Path(f.name)
            json.dump(dados, f, ensure_ascii=False, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        temporario.replace(caminho)
    finally:
        if temporario:
            temporario.unlink(missing_ok=True)
