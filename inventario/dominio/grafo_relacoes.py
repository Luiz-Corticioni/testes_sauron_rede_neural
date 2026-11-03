"""Grafos dirigidos sem pesos: alcance não representa probabilidade ou exploração."""
from collections import deque

MAX_NOS = 10000
MAX_ARESTAS = 50000
MAX_PASSOS_EXIBIDOS = 100


class GrafoRelacoes:
    def __init__(self, nos, arestas):
        if len(nos) > MAX_NOS or len(arestas) > MAX_ARESTAS:
            raise ValueError("Análise excede 10.000 ativos ou 50.000 relações; reduza o escopo.")
        self.saidas = {n: [] for n in nos}
        self.entradas = {n: [] for n in nos}
        self.arestas = {}
        if len(self.saidas) != len(nos):
            raise ValueError("Ativos repetidos no grafo.")
        for a in arestas:
            pk, origem, destino = a["id"], a["origem_id"], a["destino_id"]
            if origem not in self.saidas or destino not in self.saidas or origem == destino or pk in self.arestas:
                raise ValueError("Relação inválida no grafo.")
            self.arestas[pk] = a
            self.saidas[origem].append((destino, pk))
            self.entradas[destino].append((origem, pk))

    def busca(self, origem, remover_relacao=None, remover_ativo=None):
        if origem not in self.saidas or remover_ativo == origem:
            raise ValueError("Selecione origem operacional diferente do ativo retirado.")
        if remover_ativo is not None and remover_ativo not in self.saidas:
            raise ValueError("Ativo retirado não pertence ao inventário operacional.")
        if remover_relacao is not None and remover_relacao not in self.arestas:
            raise ValueError("A relação retirada não pertence à camada/escopo elegível.")
        anteriores, distancias = {origem: None}, {origem: 0}
        fila = deque([origem])
        while fila:
            atual = fila.popleft()
            for destino, pk in self.saidas[atual]:
                if pk == remover_relacao or destino == remover_ativo or destino in anteriores:
                    continue
                anteriores[destino] = (atual, pk)
                distancias[destino] = distancias[atual] + 1
                fila.append(destino)
        return anteriores, distancias

    @staticmethod
    def caminho(destino, anteriores, distancias):
        if destino not in anteriores:
            return {"id": destino, "alcancavel": False, "saltos": None, "passos": [], "completo": True}
        passos, cursor = [], destino
        # Percorre de trás para frente; só guarda os 100 passos iniciais do caminho.
        while anteriores[cursor] is not None:
            origem, pk = anteriores[cursor]
            if distancias[cursor] <= MAX_PASSOS_EXIBIDOS:
                passos.append({"relacao": pk, "origem": origem, "destino": cursor})
            cursor = origem
        return {"id": destino, "alcancavel": True, "saltos": distancias[destino],
                "passos": passos[::-1], "completo": distancias[destino] <= MAX_PASSOS_EXIBIDOS}

    def ciclos(self):
        """Kosaraju iterativo O(V+E); sem limite de recursão ou matriz densa."""
        vistos, ordem = set(), []
        for n in self.saidas:
            if n in vistos:
                continue
            vistos.add(n)
            pilha = [(n, iter(self.saidas[n]))]
            while pilha:
                atual, vizinhos = pilha[-1]
                proximo = next(vizinhos, None)
                if proximo is None:
                    ordem.append(atual)
                    pilha.pop()
                elif proximo[0] not in vistos:
                    vistos.add(proximo[0])
                    pilha.append((proximo[0], iter(self.saidas[proximo[0]])))
        vistos, grupos, total = set(), [], 0
        for n in reversed(ordem):
            if n in vistos:
                continue
            vistos.add(n)
            grupo, fila = [], [n]
            while fila:
                atual = fila.pop()
                grupo.append(atual)
                for anterior, _ in self.entradas[atual]:
                    if anterior not in vistos:
                        vistos.add(anterior)
                        fila.append(anterior)
            if len(grupo) > 1:
                total += 1
                if len(grupos) < 20:
                    grupos.append({"total": len(grupo), "ativos": sorted(grupo)[:50], "limitado": len(grupo) > 50})
        return {"total_grupos": total, "grupos": grupos, "limitado": total > len(grupos)}

    def analisar(self, origem, destino=None, remover_relacao=None, remover_ativo=None, limite=50):
        if type(limite) is not int or not 1 <= limite <= 100:
            raise ValueError("Limite de exibição deve ser inteiro de 1 a 100.")
        if destino is not None and destino not in self.saidas:
            raise ValueError("Destino não pertence ao inventário operacional.")
        base, distancias_base = self.busca(origem)
        depois, distancias = self.busca(origem, remover_relacao, remover_ativo)
        perdidos = sorted(set(base) - set(depois))
        alvos = [n for n in depois if n != origem]
        # Graus contam vizinhos distintos; relações paralelas continuam separadas no cenário.
        return {"origem": origem, "total_ativos": len(self.saidas), "total_relacoes": len(self.arestas),
                "grau_entrada": len({n for n, _ in self.entradas[origem]}),
                "grau_saida": len({n for n, _ in self.saidas[origem]}),
                "alcance_base": len(base)-1, "alcance_cenario": len(alvos),
                "perdidos_total": len(perdidos), "perdidos": perdidos[:limite],
                "perdidos_limitados": len(perdidos) > limite,
                "itens": [self.caminho(n, depois, distancias) for n in alvos[:limite]],
                "limitado": len(alvos) > limite, "limite": limite,
                "alvo_base": self.caminho(destino, base, distancias_base) if destino else None,
                "alvo_cenario": self.caminho(destino, depois, distancias) if destino else None,
                "remover_relacao": remover_relacao, "remover_ativo": remover_ativo,
                "ciclos_base": self.ciclos()}
