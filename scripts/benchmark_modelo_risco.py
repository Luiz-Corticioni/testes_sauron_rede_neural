"""Mede o modelo matemático real em grafo sintético; não mede banco nem HTTP.

Execute cada tamanho em processo separado: python scripts/benchmark_modelo_risco.py 100000
"""
import argparse
import os
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inventario.dominio.vulnerabilidades import Dependencia, Incidencia, Vulnerabilidade
from inventario.matematica.risco import ModeloRisco


def memoria_pico_mib():
    if os.name != "nt":
        import resource
        pico = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return pico / (1024 * 1024 if sys.platform == "darwin" else 1024)
    import ctypes
    from ctypes import wintypes

    class Contadores(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("falhas", wintypes.DWORD)] + [
            (nome, ctypes.c_size_t) for nome in (
                "pico", "atual", "pool_paginado_pico", "pool_paginado",
                "pool_nao_paginado_pico", "pool_nao_paginado", "pagina_pico", "pagina_atual",
            )
        ]

    memoria = Contadores()
    memoria.cb = ctypes.sizeof(memoria)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Contadores), wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(memoria), memoria.cb):
        raise OSError(ctypes.get_last_error(), "Falha ao obter memória do processo")
    return memoria.pico / 1024 / 1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ativos", type=int, choices=(10_000, 100_000))
    total = parser.parse_args().ativos
    inicio = perf_counter()
    ids = [str(i) for i in range(total)]
    vulnerabilidade = Vulnerabilidade("VUL-RCE-0001", "fixture", "RCE", 8)
    modelo = ModeloRisco(ids, [vulnerabilidade], [Incidencia("INC-1", "0", vulnerabilidade.id)],
                         [Dependencia(str(i), str(i - 1), .2) for i in range(1, total)])
    preparado = perf_counter()
    resultado = modelo.calcular().to_dict()
    fim = perf_counter()
    if len(resultado["risco_efetivo"]) != total or resultado["residuo_relativo"] > 1e-8:
        raise AssertionError("Resultado ou resíduo inesperado.")
    print(f"ativos={total} vulnerabilidades=1 incidencias=1 dependencias={total - 1} "
          f"preparo={preparado - inicio:.3f}s calculo={fim - preparado:.3f}s "
          f"pico_rss_processo={memoria_pico_mib():.2f}MiB "
          f"residuo_relativo={resultado['residuo_relativo']}")


if __name__ == "__main__":
    main()
