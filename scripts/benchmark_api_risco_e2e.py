"""Mede rota Django com banco SQLite temporário e dados fictícios, sem rede.

Uso: python scripts/benchmark_api_risco_e2e.py 10000
O pico RSS inclui criação dos dados e carregamento de bibliotecas. Não usa o
banco da aplicação nem executa requests contra um servidor externo.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

parser = argparse.ArgumentParser()
parser.add_argument("ativos", type=int, choices=(10000, 100000))
quantidade = parser.parse_args().ativos
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def codigo(indice):
    return f"1{'A' if indice <= 99999 else 'B'}{((indice - 1) % 99999) + 1:05d}"


with TemporaryDirectory(prefix="sauron-benchmark-api-") as pasta:
    os.environ.update(SAURON_DATA_DIR=pasta, SAURON_DB_PATH=str(Path(pasta) / "teste.sqlite3"),
                      SAURON_DEBUG="1", SAURON_ALLOWED_HOSTS="testserver", SAURON_ROTINAS_SEM_REDE="1",
                      DJANGO_SETTINGS_MODULE="sauron_web.settings")
    os.environ.pop("DATABASE_URL", None)
    import django
    django.setup()
    from django.contrib.auth import get_user_model
    from django.core.cache import cache
    from django.core.management import call_command
    from django.db import connection, reset_queries
    from django.test import Client
    from django.utils import timezone
    from django_otp.plugins.otp_totp.models import TOTPDevice
    from inventario.models import Ativo, Dependencia, Incidencia, Sala, Vulnerabilidade

    inicio = perf_counter()
    call_command("migrate", verbosity=0, interactive=False)
    usuario = get_user_model().objects.create_superuser("benchmark", "benchmark@example.invalid", "Senha-ficticia-123!")
    dispositivo = TOTPDevice.objects.create(user=usuario, name="Teste", confirmed=True)
    sala = Sala.objects.create(id="SALA-BENCH", nome="Sala fictícia")
    for primeira in range(1, quantidade + 1, 1000):
        Ativo.objects.bulk_create([Ativo(id=codigo(i), id_numerico=i, tipo="1", nome=f"Ativo {i}",
            hostname=f"host-{i}", fabricante="A fictício" if i <= 99999 else "B fictício", sala=sala)
            for i in range(primeira, min(primeira + 1000, quantidade + 1))], batch_size=500)
    for primeira in range(2, quantidade + 1, 1000):
        Dependencia.objects.bulk_create([Dependencia(dependente_id=codigo(i), fornecedor_id=codigo(i-1), peso=0.2)
            for i in range(primeira, min(primeira + 1000, quantidade + 1))], batch_size=500)
    vulnerabilidade = Vulnerabilidade.objects.create(id="VUL-RCE-0001", descricao="Fictícia", categoria="RCE", cvss=5.3)
    Incidencia.objects.create(id="INC-BENCH", ativo_id=codigo(1), vulnerabilidade=vulnerabilidade)
    cliente = Client()
    cliente.force_login(usuario)
    sessao = cliente.session
    sessao["otp_device_id"] = dispositivo.persistent_id
    sessao["sauron_reauth_em"] = timezone.now().timestamp()
    sessao.save()
    preparacao = perf_counter() - inicio
    cache.clear()
    reset_queries()
    inicio = perf_counter()
    resposta = cliente.get("/api/v1/ativos/", {"ordenar": "-risco", "pagina": 1, "tamanho": 25})
    duracao = perf_counter() - inicio
    if resposta.status_code != 200:
        raise RuntimeError(f"Rota retornou HTTP {resposta.status_code}; benchmark interrompido.")
    dados = resposta.json()
    if dados["total"] != quantidade or len(dados["resultados"]) != 25:
        raise RuntimeError("Contagem ou tamanho de página inesperados.")
    try:
        import resource
        pico_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except ImportError:
        pico_mib = None
    resultado = {"ativos": quantidade, "incidencias": 1, "vulnerabilidades": 1, "dependencias": quantidade - 1,
        "preparacao_s": round(preparacao, 3), "requisicao_s": round(duracao, 3),
        "rss_pico_processo_mib": round(pico_mib, 2) if pico_mib is not None else None,
        "consultas_sql_registradas": len(connection.queries), "http": resposta.status_code,
        "total": dados["total"], "pagina": dados["pagina"], "tamanho": len(dados["resultados"]),
        "metodo": "Django Client/WSGI; cache limpo; SQLite temporário; inclui conversão e cálculo do modelo",
        "limites": "Dados fictícios; uma vulnerabilidade e uma incidência; cadeia esparsa; sem TCP, TLS ou concorrência; pico inclui preparação."}
    print(json.dumps(resultado, ensure_ascii=False))
