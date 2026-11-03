"""Projeções de apresentação; nunca alteram o modelo ou resolvem o risco."""

from collections import deque
import numpy as np
from inventario.matematica.representacao import janela

LIMITE_GRAFO = 60
LIMITE_HEATMAP = 40


def faixa_indice(indice):
    """Faixas visuais do índice 0–100, distintas das faixas CVSS."""
    return ("baixo", "medio", "alto", "critico")[min(3, int(max(0, indice) // 25))]


def indicadores(risco):
    return {
        id_: {"indice": valor, "faixa": faixa_indice(valor), "efetivo": efetivo}
        for id_, valor, efetivo in zip(
            risco["ids_ativos"], risco["indices"], risco["risco_efetivo"]
        )
    }


def grafo_dependencias(risco, nomes):
    """A[i,j] significa i depende de j; a seta mostra o fluxo j → i."""
    ids = risco["ids_ativos"][:LIMITE_GRAFO]
    matriz = janela(risco["matriz_dependencias"], LIMITE_GRAFO, LIMITE_GRAFO)
    arestas = [
        {"origem": ids[j], "destino": ids[i], "peso": peso, "espessura": 1 + 8 * peso}
        for i in range(len(ids))
        for j, peso in enumerate(matriz[i][: len(ids)])
        if peso > 0
    ]
    entradas = {id_: 0 for id_ in ids}
    vizinhos = {id_: [] for id_ in ids}
    for aresta in arestas:
        entradas[aresta["destino"]] += 1
        vizinhos[aresta["origem"]].append(aresta["destino"])
    camadas = {}
    fila = deque(id_ for id_ in ids if entradas[id_] == 0)
    while fila:
        atual = fila.popleft()
        camadas.setdefault(atual, 0)
        for destino in vizinhos[atual]:
            camadas[destino] = max(camadas.get(destino, 0), camadas[atual] + 1)
            entradas[destino] -= 1
            if entradas[destino] == 0:
                fila.append(destino)
    ciclico = len(camadas) != len(ids)
    # Ciclos são válidos quando rho < 1. A grade evita travar a ordenação.
    if ciclico:
        camadas = {id_: i // 4 for i, id_ in enumerate(ids)}
    grupos = {}
    for id_, camada in camadas.items():
        grupos.setdefault(camada, []).append(id_)
    dados = indicadores(risco)
    nos = []
    largura = max(760, max((len(g) for g in grupos.values()), default=1) * 220)
    for camada, grupo in sorted(grupos.items()):
        for posicao, id_ in enumerate(grupo):
            nos.append(
                dict(
                    id=id_,
                    nome=nomes.get(id_, id_),
                    x=(posicao + 0.5) * largura / len(grupo),
                    y=65 + camada * 145,
                    **dados[id_]
                )
            )
    return dict(
        nos=nos,
        arestas=arestas,
        largura=largura,
        altura=max(190, 150 * len(grupos)),
        ciclico=ciclico,
        total=len(risco["ids_ativos"]),
        limitado=len(risco["ids_ativos"]) > len(ids),
    )


def heatmap(titulo, matriz, linhas, colunas, explicacao):
    """Janela limitada e escala por mapa; valores permanecem acessíveis no HTML."""
    if isinstance(matriz, dict):
        maior = max((abs(v) for v in matriz["data"]), default=1) or 1
        matriz = janela(matriz, LIMITE_HEATMAP, LIMITE_HEATMAP)
    else:
        maior = max((abs(v) for linha in matriz for v in linha), default=1) or 1
    return dict(
        titulo=titulo,
        explicacao=explicacao,
        maximo=maior,
        colunas=colunas[:LIMITE_HEATMAP],
        linhas=[
            {
                "id": id_,
                "celulas": [
                    {"valor": v, "nivel": round(9 * abs(v) / maior), "coluna": coluna}
                    for coluna, v in zip(colunas[:LIMITE_HEATMAP], linha[:LIMITE_HEATMAP])
                ],
            }
            for id_, linha in zip(linhas[:LIMITE_HEATMAP], matriz[:LIMITE_HEATMAP])
        ],
        limitado=len(linhas) > LIMITE_HEATMAP or len(colunas) > LIMITE_HEATMAP,
    )


def mapas_calor(risco):
    ids, vuls = risco["ids_ativos"], risco["ids_vulnerabilidades"]
    a = risco["matriz_dependencias"]
    mapas = [
        heatmap(
            "M · incidência",
            risco["matriz_incidencia"],
            ids,
            vuls,
            "Linha = ativo; coluna = vulnerabilidade. 1 indica incidência considerada.",
        ),
        heatmap(
            "A · dependência",
            a,
            ids,
            ids,
            "A[i,j] é quanto do risco do fornecedor j chega ao dependente i.",
        ),
    ]
    inversa = []
    if ids and len(ids) <= 200:
        # Somente apresentação da resposta a impulsos. O domínio calcula x com solve(I-A,b).
        inversa = np.linalg.solve(np.eye(len(ids)) - np.array(a), np.eye(len(ids))).tolist()
        mapas.append(
            heatmap(
                "(I − A)⁻¹ · amplificação",
                inversa,
                ids,
                ids,
                "Cada coluna é a resposta a uma unidade de risco próprio naquele ativo.",
            )
        )
    return mapas, inversa
