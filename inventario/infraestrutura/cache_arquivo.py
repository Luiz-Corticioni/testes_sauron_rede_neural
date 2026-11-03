"""FileBasedCache com substituição atômica, inclusive no Windows.

O fallback de cópia do Django pode truncar o destino enquanto outro leitor o
consulta. Aqui um leitor recebe o arquivo anterior inteiro ou o novo inteiro.
"""
import os
from pathlib import Path
import tempfile
import time
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.filebased import FileBasedCache


class CacheArquivoAtomico(FileBasedCache):
    def get(self, key, default=None, version=None):
        for tentativa in range(50):
            try:
                return super().get(key, default, version)
            except PermissionError:
                if tentativa == 49:
                    raise
                time.sleep(.02)

    def has_key(self, key, version=None):
        return self.get(key, self._missing_key, version) is not self._missing_key

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        self._createdir()
        self._cull()
        destino = self._key_to_file(key, version)
        fd, nome = tempfile.mkstemp(dir=self._dir)
        temporario = Path(nome)
        try:
            with os.fdopen(fd, 'wb') as arquivo:
                self._write_content(arquivo, timeout, value)
            for tentativa in range(50):
                try:
                    os.replace(temporario, destino)
                    return
                except PermissionError:
                    if tentativa == 49:
                        raise
                    time.sleep(.02)  # Handle de leitura/antivírus pode estar fechando.
        finally:
            temporario.unlink(missing_ok=True)

    def _delete(self, fname):
        try:
            return super()._delete(fname)
        except PermissionError:
            # Arquivo aberto: expiração continua verificada a cada leitura.
            return False

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        valor = self.get(key, self._missing_key, version)
        if valor is self._missing_key:
            return False
        self.set(key, valor, timeout, version)
        return True
