"""Cenários hipotéticos de perda em 30 dias; não é uma implementação FAIR completa.
EPSS não é probabilidade de comprometimento do ativo. Custos, fatores de cenário,
independência entre vínculos e máximo por ativo exigem validação no ambiente.
Não anualiza EPSS, não interpola dias e não inventa EPSS a partir de CVSS.
"""
from collections import defaultdict
import hashlib
import math
import numpy as np

CUSTOS_CLIENTE = {"C": (200_000, 1_500_000, 12_000_000),
                  "I": (30_000, 250_000, 2_000_000), "A": (50_000, 400_000, 3_000_000)}
PESO_CIA = {"N": 0., "L": .3, "H": 1.}


def numero(valor, nome, minimo=0., maximo=1e15):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or not minimo <= valor <= maximo:
        raise ValueError(f"{nome}: informe número finito entre {minimo:g} e {maximo:g}.")
    return float(valor)


def validar_custos(custos):
    if not isinstance(custos, dict) or set(custos) != {"C", "I", "A"}:
        raise ValueError("Informe custos para C, I e A.")
    saida = {}
    for dim, custo in custos.items():
        if isinstance(custo, (list, tuple)):
            if len(custo) != 3:
                raise ValueError(f"Custo {dim}: PERT exige mínimo, moda e máximo.")
            a, m, b = [numero(v, f"Custo {dim}") for v in custo]
            if not a < m < b:
                raise ValueError(f"Custo {dim}: PERT exige mínimo < moda < máximo.")
            saida[dim] = (a, m, b)
        else:
            saida[dim] = numero(custo, f"Custo fixo {dim}")
    return saida


def pert(minimo, moda, maximo, size, rng, lamb=4):
    """A mesma distribuição beta-PERT do protótipo, com RNG explícito."""
    minimo, moda, maximo = validar_custos({d: (minimo, moda, maximo) for d in "CIA"})["C"]
    numero(lamb, "Parâmetro PERT", 0.000001, 100)
    a = 1 + lamb * (moda - minimo) / (maximo - minimo)
    b = 1 + lamb * (maximo - moda) / (maximo - minimo)
    return minimo + rng.beta(a, b, size) * (maximo - minimo)


def parse_vetor(vetor, cvss):
    """CVSS 3.x; vetor ausente/versão não suportada usa impacto estimado CVSS/10."""
    if not isinstance(vetor, str):
        raise ValueError("O vetor CVSS deve ser texto.")
    if not vetor.startswith(("CVSS:3.0/", "CVSS:3.1/")):
        return {d: cvss / 10 for d in "CIA"}, True
    try:
        partes = [p.split(":") for p in vetor.split("/")[1:]]
        if any(len(p) != 2 for p in partes) or len(dict(partes)) != len(partes):
            raise ValueError
        cia = dict(partes)
        return {d: PESO_CIA[cia[d]] for d in "CIA"}, False
    except (KeyError, ValueError) as erro:
        raise ValueError("Vetor CVSS 3 inválido: informe C/I/A com N, L ou H.") from erro


def prob_30dias(v):
    numero(v.get("cvss"), "CVSS", 0, 10)
    if v.get("epss") is None:
        raise ValueError("Sem EPSS: não é possível atribuir uma probabilidade ao cenário.")
    epss = numero(v["epss"], "EPSS", 0, 1)
    if type(v.get("kev", False)) is not bool:
        raise ValueError("KEV deve ser verdadeiro ou falso.")
    fator = numero(v.get("exposicao", 1.), "Fator de cenário", 0, 1)
    return epss*fator, epss


def resumo(x):
    pontos = np.percentile(x, [5, 50, 90, 95, 99])
    return {"media": float(x.mean()), **{f"P{p}": float(v) for p, v in zip((5, 50, 90, 95, 99), pontos)},
            "probabilidade_perda": float((x > 0).mean())}


def simular(vulns, custos=None, n=20_000, seed=42, teto=None, corrigidas=None):
    """Um evento por vínculo/30 dias; maior perda por ativo e soma entre ativos.
    Amostras comuns mantêm a comparação reprodutível. Ganhos marginais não somam.
    """
    if type(n) is not int or not 1 <= n <= 100_000:
        raise ValueError("Número de simulações deve ser inteiro de 1 a 100000.")
    if type(seed) is not int or not 0 <= seed <= 2**32-1:
        raise ValueError("Seed deve ser inteiro de 0 a 4294967295.")
    custos = validar_custos(CUSTOS_CLIENTE if custos is None else custos)
    teto = numero(teto, "Teto para 30 dias") if teto is not None else None
    if not isinstance(vulns, (list, tuple)):
        raise ValueError("Entradas e correções devem ser listas.")
    corrigidas = [] if corrigidas is None else corrigidas
    if not isinstance(corrigidas, (list, tuple)) or any(not isinstance(c, str) for c in corrigidas):
        raise ValueError("Correções exigem identificadores de texto.")
    grupos, vistos, metadados = defaultdict(list), set(), []
    for v in vulns:
        if not isinstance(v, dict) or any(not isinstance(v.get(k), str) or not v[k].strip() for k in ("ativo", "cve")):
            raise ValueError("Cada entrada exige ativo e CVE/ID.")
        chave = (v["ativo"], v["cve"])
        if chave in vistos:
            raise ValueError("Vínculo ativo/CVE duplicado.")
        vistos.add(chave)
        prob, epss = prob_30dias(v)
        cia, estimado = parse_vetor(v.get("vetor", ""), float(v["cvss"]))
        grupos[v["ativo"]].append((v, prob, cia))
        metadados.append({"ativo": v["ativo"], "cve": v["cve"], "epss": epss,
            "origem_epss": "informado", "epss_data": v.get("epss_data"), "impacto_estimado": estimado,
            "probabilidade_cenario_30d": prob, "kev": v.get("kev", False),
            "observacao_epss_id": v.get("observacao_epss_id"), "epss_fonte": v.get("epss_fonte"),
            "epss_situacao": v.get("epss_situacao", "Não informada")})
    ids = sorted({v["cve"] for v in vulns})
    if set(corrigidas) - (set(ids) | {v.get("id", v["cve"]) for v in vulns}):
        raise ValueError("Correção contém CVE/ID sem incidência elegível.")
    retiradas = set(corrigidas)
    total, depois = np.zeros(n), np.zeros(n)
    atribuicoes = {c: np.zeros(n) for c in ids}
    reducoes = {c: np.zeros(n) for c in ids}
    for ativo in sorted(grupos):
        maior, segundo, vencedor, apos = np.zeros(n), np.zeros(n), np.full(n, -1, dtype=int), np.zeros(n)
        entradas = sorted(grupos[ativo], key=lambda item: item[0]["cve"])
        for indice, (v, prob, cia) in enumerate(entradas):
            chave = hashlib.sha256(f"{seed}|{ativo}|{v['cve']}".encode()).digest()
            rng = np.random.default_rng(int.from_bytes(chave[:16], "big"))
            ocorre, custo = rng.random(n) < prob, np.zeros(n)
            for dim in "CIA":
                c = custos[dim]
                custo += cia[dim] * (pert(*c, n, rng) if isinstance(c, tuple) else c)
            perda = ocorre*custo
            if v["cve"] not in retiradas and v.get("id") not in retiradas:
                np.maximum(apos, perda, out=apos)
            troca = perda > maior
            segundo = np.where(troca, maior, np.maximum(segundo, perda))
            maior = np.maximum(maior, perda)
            vencedor[troca] = indice
        total += maior
        depois += apos
        for indice, (v, _, _) in enumerate(entradas):
            mascara = vencedor == indice
            atribuicoes[v["cve"]] += np.where(mascara, maior, 0)
            reducoes[v["cve"]] += np.where(mascara, maior-segundo, 0)
    bruto = total.copy()
    if teto is not None:
        np.minimum(total, teto, out=total)
        np.minimum(depois, teto, out=depois)
    fator = np.divide(total, bruto, out=np.zeros(n), where=bruto > 0)
    contribuicao = [{"cve": c, "media_atribuida": float((atribuicoes[c]*fator).mean()),
        "ganho_correcao": float((total-(np.minimum(bruto-reducoes[c], teto) if teto is not None else bruto-reducoes[c])).mean())} for c in ids]
    limites = np.unique(np.r_[0., np.percentile(total, np.linspace(0, 100, 41))])
    return {"versao_modelo": "sauron.montecarlo/30d-v1", "horizonte_dias": 30, "disponivel": True,
        "n": n, "seed": seed, "antes": resumo(total), "depois": resumo(depois),
        "ganho_media": float((total-depois).mean()),
        "excedencia": [{"perda": float(x), "probabilidade": float((total > x).mean()),
                        "probabilidade_depois": float((depois > x).mean())} for x in limites],
        "contribuicoes": contribuicao, "entradas": metadados,
        "aviso": "Estimativa, não previsão. Cenário hipotético de 30 dias; custos e fatores não calibrados. Não estima a chance de comprometimento de um ativo e não implementa FAIR completo."}
