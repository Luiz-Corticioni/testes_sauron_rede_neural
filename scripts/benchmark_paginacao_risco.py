"""Compara apenas a seleção da primeira página, com risco sintético pré-calculado.

Executar: python scripts/benchmark_paginacao_risco.py
Banco temporário SQLite descartável; não mede o cálculo global de risco.
"""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
import tracemalloc
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

with TemporaryDirectory(prefix="sauron-benchmark-") as pasta:
    os.environ["SAURON_DATA_DIR"] = pasta
    os.environ["SAURON_DB_PATH"] = str(Path(pasta) / "benchmark.sqlite3")
    os.environ["SAURON_DEBUG"] = "1"
    os.environ.pop("DATABASE_URL", None)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sauron_web.settings")

    import django
    django.setup()
    from django.db import connection, models
    from inventario.web.api_v1 import ativos_por_risco

    class AtivoSintetico(models.Model):
        id = models.CharField(max_length=16, primary_key=True)
        nome = models.CharField(max_length=100)
        hostname = models.CharField(max_length=100)
        tipo = models.CharField(max_length=1)
        criticidade = models.IntegerField()
        status = models.CharField(max_length=20)

        class Meta:
            app_label = "inventario"
            db_table = "benchmark_ativo_sintetico"

    campos = ("id", "nome", "hostname", "tipo", "criticidade", "status")
    with connection.schema_editor() as schema:
        schema.create_model(AtivoSintetico)

    def medir(funcao):
        tracemalloc.start()
        inicio = perf_counter()
        resultado = funcao()
        tempo = perf_counter() - inicio
        _, pico = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return resultado, tempo, pico / 1024 / 1024

    for total in (10_000, 100_000):
        for inicio in range(AtivoSintetico.objects.count(), total, 1000):
            AtivoSintetico.objects.bulk_create([
                AtivoSintetico(id=f"A{i:07d}", nome=f"Ativo {i}", hostname=f"host-{i}",
                               tipo="1", criticidade=1, status="ATIVO")
                for i in range(inicio, min(inicio + 1000, total))
            ])
        ids = [f"A{i:07d}" for i in range(total)]
        riscos = {pk: float((i * 37) % 101) for i, pk in enumerate(ids)}
        qs = AtivoSintetico.objects.all()

        def anterior():
            registros = list(qs.order_by("id").values(*campos))
            for item in registros:
                item["risco_efetivo"] = riscos.get(item["id"], 0.0)
            registros.sort(key=lambda item: (-item["risco_efetivo"], item["id"]))
            return registros[:25]

        dados = {"ids_ativos": ids, "risco_efetivo": [riscos[pk] for pk in ids]}
        antes, tempo_a, memoria_a = medir(anterior)
        with patch("inventario.aplicacao.risco.calcular_risco_banco", return_value=dados):
            depois, tempo_d, memoria_d = medir(lambda: ativos_por_risco(qs, campos, 0, 25))
        if antes != depois:
            raise AssertionError("A página mudou em relação à implementação anterior.")
        print(f"ativos={total} anterior={tempo_a:.3f}s/{memoria_a:.2f}MiB "
              f"novo={tempo_d:.3f}s/{memoria_d:.2f}MiB")
    connection.close()
