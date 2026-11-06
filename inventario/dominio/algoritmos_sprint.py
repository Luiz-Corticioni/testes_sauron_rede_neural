"""Estruturas didáticas; o caminho operacional usa índices SQL e sorted do Python."""

from collections import deque


class TabelaHash:
    def __init__(self, capacidade=101):
        if capacidade < 1:
            raise ValueError("A capacidade deve ser positiva.")
        self._baldes = [[] for _ in range(capacidade)]

    def inserir(self, chave, valor):
        balde = self._baldes[hash(chave) % len(self._baldes)]
        for i, (existente, _) in enumerate(balde):
            if existente == chave:
                balde[i] = (chave, valor)
                return
        balde.append((chave, valor))

    def buscar(self, chave):
        for existente, valor in self._baldes[hash(chave) % len(self._baldes)]:
            if existente == chave:
                return valor
        raise KeyError(chave)


class ArvoreBinaria:
    """Chaves repetidas são ignoradas; não há rebalanceamento automático."""

    def __init__(self):
        self.raiz = None

    def inserir(self, chave):
        novo = [chave, None, None]
        if self.raiz is None:
            self.raiz = novo
            return
        atual = self.raiz
        while True:
            if chave == atual[0]:
                return
            lado = 1 if chave < atual[0] else 2
            if atual[lado] is None:
                atual[lado] = novo
                return
            atual = atual[lado]

    def buscar(self, chave):
        atual = self.raiz
        while atual is not None:
            if chave == atual[0]:
                return True
            atual = atual[1 if chave < atual[0] else 2]
        return False

    def percurso(self, ordem="em_ordem"):
        if ordem not in {"pre", "em_ordem", "pos", "nivel"}:
            raise ValueError("Ordem inválida.")
        if self.raiz is None:
            return []
        if ordem == "nivel":
            fila, resultado = deque([self.raiz]), []
            while fila:
                no = fila.popleft()
                resultado.append(no[0])
                fila.extend(filho for filho in no[1:] if filho is not None)
            return resultado
        resultado, pilha = [], [(self.raiz, False)]
        while pilha:
            no, visitar = pilha.pop()
            if no is None:
                continue
            if visitar:
                resultado.append(no[0])
                continue
            esquerda, direita = no[1], no[2]
            etapas = {"pre": [(no, True), (esquerda, False), (direita, False)],
                      "em_ordem": [(esquerda, False), (no, True), (direita, False)],
                      "pos": [(esquerda, False), (direita, False), (no, True)]}
            pilha.extend(reversed(etapas[ordem]))
        return resultado

    def altura(self):
        if self.raiz is None:
            return 0
        pilha, altura = [(self.raiz, 1)], 0
        while pilha:
            no, nivel = pilha.pop()
            altura = max(altura, nivel)
            pilha.extend((filho, nivel + 1) for filho in no[1:] if filho is not None)
        return altura


def merge_sort(itens, chave=lambda x: x):
    """Ordenação estável; retorna nova lista."""
    itens = list(itens)
    if len(itens) < 2:
        return itens
    meio = len(itens) // 2
    esquerda, direita = merge_sort(itens[:meio], chave), merge_sort(itens[meio:], chave)
    resultado, i, j = [], 0, 0
    while i < len(esquerda) and j < len(direita):
        if chave(esquerda[i]) <= chave(direita[j]):
            resultado.append(esquerda[i])
            i += 1
        else:
            resultado.append(direita[j])
            j += 1
    return resultado + esquerda[i:] + direita[j:]


def quick_sort(itens, chave=lambda x: x, *, randomizador=None):
    """Lomuto iterativo; randomizador opcional escolhe o pivô antes da partição."""
    resultado = list(itens)
    pilha = [(0, len(resultado) - 1)]
    while pilha:
        inicio, fim = pilha.pop()
        if inicio >= fim:
            continue
        if randomizador is not None:
            indice_pivo = randomizador.randrange(inicio, fim + 1)
            resultado[indice_pivo], resultado[fim] = resultado[fim], resultado[indice_pivo]
        pivo, i = chave(resultado[fim]), inicio
        for j in range(inicio, fim):
            if chave(resultado[j]) <= pivo:
                resultado[i], resultado[j] = resultado[j], resultado[i]
                i += 1
        resultado[i], resultado[fim] = resultado[fim], resultado[i]
        pilha.extend(((inicio, i - 1), (i + 1, fim)))
    return resultado


def dfs_ciclos(vizinhos, origem):
    """Retorna alcance e existência de ciclo alcançável em grafo dirigido."""
    if origem not in vizinhos:
        raise ValueError("Origem inexistente.")
    cores, alcance, ciclo = {origem: 1}, [], False
    pilha = [(origem, iter(vizinhos[origem]))]
    while pilha:
        atual, filhos = pilha[-1]
        try:
            destino = next(filhos)
        except StopIteration:
            cores[atual] = 2
            pilha.pop()
            continue
        if destino not in vizinhos:
            raise ValueError("Aresta referencia vértice inexistente.")
        if cores.get(destino) == 1:
            ciclo = True
        elif destino not in cores:
            cores[destino] = 1
            alcance.append(destino)
            pilha.append((destino, iter(vizinhos[destino])))
    return alcance, ciclo
