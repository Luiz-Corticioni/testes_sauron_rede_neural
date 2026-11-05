"""Duas simulações simultâneas por diretório de dados, entre processos do host."""
from contextlib import contextmanager
import errno
import os
from django.conf import settings


class LimiteSimulacoes(ValueError):
    pass


@contextmanager
def vaga_simulacao():
    pasta = settings.DATA_DIR / 'cache' / 'vagas_montecarlo'
    pasta.mkdir(parents=True, exist_ok=True)
    escolhido = None
    for numero in range(2):
        arquivo = (pasta / f'{numero}.lock').open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                if arquivo.seek(0, os.SEEK_END) == 0:
                    arquivo.write(b'0')
                    arquivo.flush()
                arquivo.seek(0)
                msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            escolhido = arquivo
            break
        except OSError as erro:
            arquivo.close()
            if erro.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise
    if escolhido is None:
        raise LimiteSimulacoes('Simulações ocupadas; aguarde alguns segundos e tente novamente.')
    try:
        yield
    finally:
        try:
            if os.name == 'nt':
                import msvcrt
                escolhido.seek(0)
                msvcrt.locking(escolhido.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(escolhido.fileno(), fcntl.LOCK_UN)
        finally:
            escolhido.close()
