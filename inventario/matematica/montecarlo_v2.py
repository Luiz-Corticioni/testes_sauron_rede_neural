"""Modelo hipotético de 30 dias; evidências ausentes interrompem o cálculo."""
import hashlib
import json
import math

import numpy as np
from scipy.special import ndtr, ndtri

from inventario.matematica.montecarlo import CUSTOS_CLIENTE, numero, simular, validar_custos

FATORES = ("exploracao", "alcance", "falha_controle")


def gerador(seed, chave):
    resumo = hashlib.sha256(f"{seed}|{chave}".encode()).digest()
    return np.random.default_rng(int.from_bytes(resumo[:16], "big"))


def validar_fator(item):
    if not isinstance(item, dict) or set(item) != {"faixa", "origem"}:
        raise ValueError("Cada fator exige faixa e origem declarada.")
    origem, faixa = item["origem"], item["faixa"]
    if not isinstance(origem, str) or not 1 <= len(origem.strip()) <= 300:
        raise ValueError("Informe a origem de cada fator (até 300 caracteres).")
    if not isinstance(faixa, (list, tuple)) or len(faixa) != 3:
        raise ValueError("Cada faixa exige mínimo, mais provável e máximo.")
    baixo, moda, alto = [numero(x, "Fator de probabilidade", 0, 1) for x in faixa]
    if not baixo <= moda <= alto:
        raise ValueError("A faixa deve estar em ordem crescente.")
    return {"faixa": [baixo, moda, alto], "origem": origem.strip()}


def amostrar_fator(fator, n, rng):
    baixo, moda, alto = fator["faixa"]
    if baixo == alto:
        return baixo
    alfa = 1 + 4 * (moda - baixo) / (alto - baixo)
    beta = 1 + 4 * (alto - moda) / (alto - baixo)
    return baixo + (alto - baixo) * rng.beta(alfa, beta, n)


def grupos_causa(entradas):
    """União transitiva de rótulos declarados; a CVE é sempre uma causa comum."""
    pais = list(range(len(entradas)))
    vistos = {}

    def raiz(i):
        while pais[i] != i:
            pais[i] = pais[pais[i]]
            i = pais[i]
        return i

    for i, entrada in enumerate(entradas):
        causas = entrada.get("causas", [])
        if not isinstance(causas, list) or len(causas) > 101 or any(not isinstance(x, str) or not 1 <= len(x) <= 530 for x in causas):
            raise ValueError("Causas comuns devem ser uma lista de até 101 identificadores.")
        for chave in ["cve:" + entrada["cve"], *causas]:
            if chave in vistos:
                pais[raiz(i)] = raiz(vistos[chave])
            else:
                vistos[chave] = i
    grupos = {}
    for i, entrada in enumerate(entradas):
        grupos.setdefault(raiz(i), []).append(entrada["id"])
    return {identificador: json.dumps(sorted(ids), ensure_ascii=True) for ids in grupos.values() for identificador in ids}


def simular_v2(entradas, fatores, custos=None, n=20000, seed=42, teto=None, correlacao=0, intervencoes=None, apetite=None, sensibilidade=False):
    if type(n) is not int or not 100 <= n <= 100000 or type(seed) is not int or not 0 <= seed <= 2**32-1:
        raise ValueError("Use 100 a 100000 simulações e semente inteira válida.")
    custos = validar_custos(CUSTOS_CLIENTE if custos is None else custos)
    if not isinstance(entradas, list) or len(entradas) * n > 1_000_000:
        raise ValueError("Reduza o cenário: limite de um milhão de vínculos × simulações.")
    if not isinstance(fatores, dict):
        raise ValueError("Informe os fatores de cada incidência.")
    if any(not isinstance(v, dict) or not isinstance(v.get("id"), str) or not v["id"]
           or not isinstance(v.get("ativo"), str) or not isinstance(v.get("cve"), str) for v in entradas):
        raise ValueError("Cada entrada exige ID, ativo e CVE.")
    ids = [v["id"] for v in entradas]
    if len(set(ids)) != len(ids) or set(ids) != set(fatores):
        raise ValueError("Os fatores devem corresponder exatamente às incidências, sem duplicatas.")
    correlacao = numero(correlacao, "Correlação latente", 0, 1)
    normalizados = {}
    for identificador in ids:
        if not isinstance(fatores[identificador], dict) or set(fatores[identificador]) != set(FATORES):
            raise ValueError("Informe exploração, alcance e falha de controle para cada incidência.")
        normalizados[identificador] = {k: validar_fator(fatores[identificador][k]) for k in FATORES}
    if type(sensibilidade) is not bool:
        raise ValueError("Sensibilidade deve ser verdadeira ou falsa.")
    intervencoes = [] if intervencoes is None else intervencoes
    if not isinstance(intervencoes, list) or len(intervencoes) > 5:
        raise ValueError("Informe até cinco intervenções.")
    if len(entradas) * n * (1 + len(intervencoes) + 6 * int(sensibilidade)) > 8_000_000:
        raise ValueError("Reduza as simulações ou comparações: limite de trabalho do cenário excedido.")
    probabilidades, amostras_por_fator = {}, {}
    for identificador in ids:
        amostras = {k: amostrar_fator(normalizados[identificador][k], n, gerador(seed, f"fator|{identificador}|{k}")) for k in FATORES}
        amostras_por_fator[identificador] = amostras
        probabilidades[identificador] = amostras["exploracao"] * amostras["alcance"] * amostras["falha_controle"]
    grupos = grupos_causa(entradas)
    uniformes = None
    if correlacao:
        comuns, uniformes = {}, {}
        for entrada in entradas:
            chave = grupos[entrada["id"]]
            if chave not in comuns:
                comuns[chave] = gerador(seed, "causa|" + chave).standard_normal(n)
            origem = gerador(seed, entrada["ativo"] + "|" + entrada["cve"]).random(n)
            independente = ndtri(np.clip(origem, np.finfo(float).eps, 1 - np.finfo(float).eps))
            uniformes[entrada["id"]] = ndtr(math.sqrt(correlacao) * comuns[chave] + math.sqrt(1-correlacao) * independente)
    if apetite is not None:
        if not isinstance(apetite, dict) or set(apetite) != {"limite", "probabilidade_tolerada"}:
            raise ValueError("Apetite exige limite e probabilidade tolerada.")
        limite = numero(apetite["limite"], "Limite de apetite")
        tolerada = numero(apetite["probabilidade_tolerada"], "Probabilidade tolerada", 0, 1)
    else:
        limite = tolerada = None
    base = simular(entradas, custos=custos, n=n, seed=seed, teto=teto,
                   probabilidades=probabilidades, uniformes=uniformes, limite_excedencia=limite)
    comparacoes = []
    for intervencao in intervencoes:
        if not isinstance(intervencao, dict) or set(intervencao) != {"nome", "incidencias", "custo"}:
            raise ValueError("Intervenção exige nome, incidências e custo.")
        nome, corrigidas = intervencao["nome"], intervencao["incidencias"]
        if not isinstance(nome, str) or not nome.strip() or len(nome) > 120 or not isinstance(corrigidas, list) or not corrigidas:
            raise ValueError("Informe nome e incidências da intervenção.")
        if any(not isinstance(i, str) for i in corrigidas) or len(set(corrigidas)) != len(corrigidas) or set(corrigidas) - set(ids):
            raise ValueError("Intervenção contém incidências repetidas ou desconhecidas.")
        custo = numero(intervencao["custo"], "Custo da intervenção")
        resultado = simular(entradas, custos=custos, n=n, seed=seed, teto=teto, corrigidas=corrigidas,
                            probabilidades=probabilidades, uniformes=uniformes)
        ganho = resultado["ganho_media"]
        ganho_p95 = resultado["antes"]["P95"] - resultado["depois"]["P95"]
        comparacoes.append({"nome": nome.strip(), "incidencias": corrigidas, "custo": custo,
                            "reducao_media": ganho, "reducao_p95": ganho_p95,
                            "ganho_por_custo": ganho / custo if custo else None,
                            "p95_por_custo": ganho_p95 / custo if custo else None,
                            "retorno_liquido": ganho - custo,
                            "retorno_relativo": (ganho - custo) / custo if custo else None})
    tornado = []
    if sensibilidade:
        for campo in FATORES:
            medias = []
            for extremo in (0, 2):
                variacao = {}
                for identificador in ids:
                    valores = dict(amostras_por_fator[identificador])
                    valores[campo] = normalizados[identificador][campo]["faixa"][extremo]
                    variacao[identificador] = valores["exploracao"] * valores["alcance"] * valores["falha_controle"]
                alternativo = simular(entradas, custos=custos, n=n, seed=seed, teto=teto,
                    probabilidades=variacao, uniformes=uniformes)
                medias.append(alternativo["antes"]["media"])
            tornado.append({"fator": campo, "media_minimo": medias[0], "media_maximo": medias[1],
                            "variacao_media": medias[1] - medias[0]})
        tornado.sort(key=lambda item: abs(item["variacao_media"]), reverse=True)
        maior = max((abs(item["variacao_media"]) for item in tornado), default=0)
        for item in tornado:
            item["percentual_relativo"] = 100 * abs(item["variacao_media"]) / maior if maior else 0
    if apetite is not None:
        estimada = base.pop("probabilidade_acima_limite")
        base["apetite"] = {"limite": limite, "probabilidade_tolerada": tolerada,
                           "probabilidade_simulada": estimada, "violado": estimada > tolerada,
                           "observacao": "Calculado sobre perdas após eventual teto informado."}
    else:
        base["apetite"] = None
    base.update(versao_modelo="sauron.montecarlo/30d-v2", fatores=normalizados, custos_utilizados=custos, teto=teto,
                correlacao_latente=correlacao, intervencoes=comparacoes, sensibilidade=tornado,
                aviso="Cenário hipotético em 30 dias, não é previsão nem FAIR completo. Fatores e correlação são hipóteses declaradas, não probabilidades medidas pelo grafo.")
    return base
