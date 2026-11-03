"""Grafo de alcançabilidade hipotética por zonas/portas e regras explícitas.

Não faz descoberta de rede. Porta cadastrada não comprova serviço acessível e
alcançabilidade não comprova exploração. Custos positivos são relativos, não
probabilidades nem tempo de ataque. Gargalos são nós cuja remoção desconecta alvos.
"""
from collections import deque
import heapq
import math


def portas(valores):
    resultado=set()
    for valor in valores:
        valor=valor.get("porta") if isinstance(valor,dict) else valor
        if type(valor) is not int or not 1<=valor<=65535:
            raise ValueError("Porta deve ser inteiro de 1 a 65535.")
        resultado.add(valor)
    return resultado


def construir_grafo(ativos,regras):
    """Cria aresta i→j somente quando regra de zonas permite porta cadastrada em j."""
    ids=[a["id"] for a in ativos]
    if len(set(ids))!=len(ids) or not all(isinstance(i,str) for i in ids):
        raise ValueError("IDs de ativos devem ser textos únicos.")
    grafo={i:{} for i in ids}
    destinos={a["id"]:portas(a.get("portas_servicos",[])) for a in ativos}
    for regra in regras:
        custo=regra.get("custo",1.0)
        if not isinstance(custo,(int,float)) or not math.isfinite(custo) or custo<=0:
            raise ValueError("Custo deve ser positivo e finito.")
        permitidas=portas(regra.get("portas",[]))
        for origem in ativos:
            for destino in ativos:
                if (origem["id"]!=destino["id"] and origem.get("zona_rede")
                        and destino.get("zona_rede") and origem["zona_rede"]==regra["origem"]
                        and destino["zona_rede"]==regra["destino"]
                        and destinos[destino["id"]]&permitidas):
                    atual=grafo[origem["id"]].get(destino["id"],math.inf)
                    grafo[origem["id"]][destino["id"]]=min(atual,custo)
    return grafo


def validar(grafo,origem):
    if origem not in grafo:
        raise ValueError("Origem ausente do grafo.")
    for arestas in grafo.values():
        for alvo,custo in arestas.items():
            if alvo not in grafo or not math.isfinite(custo) or custo<=0:
                raise ValueError("Aresta inválida.")


def menor_custo(grafo,origem,destino):
    """Dijkstra; None indica alvo inalcançável."""
    validar(grafo,origem)
    if destino not in grafo:
        raise ValueError("Destino ausente do grafo.")
    custos={origem:0}
    anteriores={}
    fila=[(0,origem)]
    while fila:
        custo,no=heapq.heappop(fila)
        if custo!=custos[no]:
            continue
        if no==destino:
            caminho=[no]
            while caminho[-1]!=origem:
                caminho.append(anteriores[caminho[-1]])
            return {"custo":custo,"caminho":list(reversed(caminho))}
        for vizinho,peso in grafo[no].items():
            novo=custo+peso
            if novo<custos.get(vizinho,math.inf):
                custos[vizinho]=novo
                anteriores[vizinho]=no
                heapq.heappush(fila,(novo,vizinho))
    return None


def pontos_estrangulamento(grafo,origem,alvos):
    """Gargalos dirigidos por remoção de nó; O(V*(V+E)), apropriado a laboratório."""
    validar(grafo,origem)
    if any(a not in grafo for a in alvos):
        raise ValueError("Alvo ausente do grafo.")
    def alcancados(bloqueado=None):
        vistos={origem}
        fila=deque([origem])
        while fila:
            for vizinho in grafo[fila.popleft()]:
                if vizinho!=bloqueado and vizinho not in vistos:
                    vistos.add(vizinho)
                    fila.append(vizinho)
        return vistos
    relevantes=set(alvos)&alcancados()
    resultado={}
    for no in grafo:
        if no==origem or no in relevantes:
            continue
        perdidos=relevantes-alcancados(no)
        if perdidos:
            resultado[no]=sorted(perdidos)
    return resultado

