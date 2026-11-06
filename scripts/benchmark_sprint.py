"""Medições didáticas sintéticas, não um teste de carga nem garantia de desempenho."""

import cProfile
import io
import json
from pathlib import Path
import pstats
import random
import sqlite3
import sys
from time import perf_counter
from timeit import timeit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inventario.dominio.algoritmos_sprint import ArvoreBinaria, TabelaHash, merge_sort, quick_sort  # noqa: E402
from inventario.dominio.vulnerabilidades import Dependencia, Incidencia, Vulnerabilidade  # noqa: E402
from inventario.matematica.risco import ModeloRisco  # noqa: E402


def medir(funcao):
    inicio = perf_counter()
    resultado = funcao()
    return perf_counter() - inicio, resultado


def main():
    rng = random.Random(42)
    dados = [rng.randrange(10000) for _ in range(1000)]
    ordenacao = {}
    for nome, funcao in (("merge", merge_sort), ("quick", quick_sort), ("sorted", sorted)):
        tempo, obtido = medir(lambda: funcao(dados))
        assert obtido == sorted(dados)
        ordenacao[nome] = tempo
    crescente = list(range(1000))
    ordenacao["quick_crescente_pivo_final"], resultado_final = medir(lambda: quick_sort(crescente))
    ordenacao["quick_crescente_pivo_aleatorio"], resultado_aleatorio = medir(
        lambda: quick_sort(crescente, randomizador=random.Random(42)))
    assert resultado_final == resultado_aleatorio == crescente
    arvores = {}
    for nome, numeros in (("crescente", range(500)), ("embaralhada", rng.sample(range(500), 500))):
        arvore = ArvoreBinaria()
        for numero in numeros:
            arvore.inserir(numero)
        arvores[nome] = arvore.altura()
    tabela = TabelaHash(1009)
    for i in range(1000):
        tabela.inserir(i, i)
    tempo_hash, _ = medir(lambda: [tabela.buscar(i) for i in range(1000)])
    buscas = {}
    for tamanho in (10, 1000, 100000):
        lista = list(range(tamanho))
        indice = {i: i for i in lista}
        buscas[str(tamanho)] = {
            "lista": timeit(lambda: tamanho - 1 in lista, number=100),
            "dict": timeit(lambda: tamanho - 1 in indice, number=100),
        }
    with sqlite3.connect(":memory:") as banco:
        banco.execute("CREATE TABLE amostra (codigo TEXT, valor INTEGER)")
        banco.executemany("INSERT INTO amostra VALUES (?, ?)", ((str(i), i) for i in range(10000)))
        consulta = "SELECT valor FROM amostra WHERE codigo = ?"
        plano_antes = banco.execute("EXPLAIN QUERY PLAN " + consulta, ("9999",)).fetchall()
        tempo_antes = timeit(lambda: banco.execute(consulta, ("9999",)).fetchone(), number=100)
        banco.execute("CREATE INDEX amostra_codigo ON amostra(codigo)")
        plano_depois = banco.execute("EXPLAIN QUERY PLAN " + consulta, ("9999",)).fetchall()
        tempo_depois = timeit(lambda: banco.execute(consulta, ("9999",)).fetchone(), number=100)
    medicoes = {}
    perfil = cProfile.Profile()
    for n in (10, 100, 1000):
        ids = [str(i) for i in range(n)]
        falha = Vulnerabilidade("VUL-RCE-0001", "Exemplo", "RCE", 8)
        modelo = ModeloRisco(ids, [falha], [Incidencia("I", "0", falha.id)],
                             [Dependencia(ids[i], ids[i-1], 0.1) for i in range(1, n)])
        if n == 100:
            perfil.enable()
        tempo, resultado = medir(modelo.calcular)
        if n == 100:
            perfil.disable()
        assert len(resultado.risco_efetivo) == n
        medicoes[str(n)] = tempo
    saida_perfil = io.StringIO()
    pstats.Stats(perfil, stream=saida_perfil).strip_dirs().sort_stats("cumulative").print_stats(8)
    print(json.dumps({"ordenacao_segundos": ordenacao, "altura_arvore": arvores,
                      "busca_hash_1000_segundos": tempo_hash, "risco_segundos": medicoes,
                      "buscas_100_repeticoes": buscas,
                      "indice_sql_sintetico": {"antes": plano_antes, "depois": plano_depois,
                                               "segundos_antes": tempo_antes, "segundos_depois": tempo_depois},
                      "perfil_100_ativos": saida_perfil.getvalue()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
