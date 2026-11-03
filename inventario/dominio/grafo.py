"""Alcance estrutural: fornecedores apontam para seus dependentes, como A[i,j]."""

from collections import deque
import math


class GrafoDependencias:
    """Lista de adjacência; filas e predecessores evitam recursão e cópia de caminhos."""

    def __init__(self, ids_ativos, dependencias):
        self.vizinhos = {codigo: [] for codigo in ids_ativos}
        if len(self.vizinhos) != len(ids_ativos):
            raise ValueError("A lista de ativos contém códigos repetidos.")
        self.total_arestas = 0
        for dep in dependencias:
            if dep.fornecedor_id not in self.vizinhos or dep.dependente_id not in self.vizinhos:
                raise ValueError("Dependência referencia um ativo inexistente.")
            if (type(dep.peso) not in (int, float) or not math.isfinite(dep.peso)
                    or not 0 <= dep.peso < 1 or dep.fornecedor_id == dep.dependente_id):
                raise ValueError("Use fornecedores distintos e pesos finitos em [0,1).")
            if dep.peso > 0:
                self.vizinhos[dep.fornecedor_id].append(dep.dependente_id)
                self.total_arestas += 1

    def alcance(self, origem, limite=50):
        """BFS encontra um caminho com o menor número de saltos, não o maior risco.

        Visitação: O(V+E). Predecessores ocupam O(V). Apenas os caminhos exibidos
        são reconstruídos: custo adicional O(soma de seus comprimentos).
        O limite de exibição não interrompe a análise do inventário completo.
        """
        if origem not in self.vizinhos:
            raise ValueError("Ativo de origem inexistente.")
        if type(limite) is not int or not 1 <= limite <= 200:
            raise ValueError("O limite deve ser um inteiro de 1 a 200.")
        fila = deque([origem])
        anteriores = {origem: None}
        distancias = {origem: 0}
        while fila:
            atual = fila.popleft()
            for destino in self.vizinhos[atual]:
                if destino not in anteriores:
                    anteriores[destino] = atual
                    distancias[destino] = distancias[atual] + 1
                    fila.append(destino)
        itens = []
        for destino in anteriores:
            if destino == origem:
                continue
            if len(itens) >= limite:
                break
            caminho = []
            cursor = destino
            while cursor is not None:
                caminho.append(cursor)
                cursor = anteriores[cursor]
            itens.append({"id": destino, "saltos": distancias[destino], "caminho": caminho[::-1]})
        total = len(anteriores) - 1
        return {"origem": origem, "total_dependentes": total, "itens": itens,
                "total_ativos": len(self.vizinhos), "arestas_positivas": self.total_arestas,
                "limitado": total > len(itens), "limite": limite,
                "aviso": "Alcance das dependências cadastradas com peso positivo. Não mede "
                         "probabilidade, tempo de contágio nem confirma comprometimento."}
