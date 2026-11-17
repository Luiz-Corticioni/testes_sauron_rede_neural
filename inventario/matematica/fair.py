"""Simulação quantitativa de fatores FAIR, com horizonte fixo de 30 dias."""
import numpy as np

from inventario.matematica.montecarlo import numero, resumo

MODOS = {"LEF", "TEF", "TEF_CAPACIDADE", "CONTATO_SUSC", "DECOMPOSTO"}
CATEGORIAS = {"PRODUTIVIDADE", "RESPOSTA", "SUBSTITUICAO", "VANTAGEM", "MULTAS", "REPUTACAO"}
TIPOS = {"PRIMARIA", "SECUNDARIA"}
MAX_EVENTOS = 1_000_000


def faixa(valor, nome, teto):
    if not isinstance(valor, (list, tuple)) or len(valor) != 3:
        raise ValueError(f"{nome}: informe mínimo, mais provável e máximo.")
    minimo, moda, maximo = [numero(v, nome, 0, teto) for v in valor]
    if not minimo <= moda <= maximo or (minimo == maximo and moda != minimo):
        raise ValueError(f"{nome}: informe mínimo ≤ mais provável ≤ máximo.")
    return [minimo, moda, maximo]


def validar(dados):
    campos = {"modo", "frequencia", "acao", "suscetibilidade", "capacidade", "resistencia", "perdas"}
    if not isinstance(dados, dict) or set(dados) != campos or not isinstance(dados["modo"], str) or dados["modo"] not in MODOS:
        raise ValueError("Informe o modo e todos os campos esperados do modelo.")
    modo = dados["modo"]
    resultado = {"modo": modo, "frequencia": faixa(dados["frequencia"], "Frequência em 30 dias", 20)}
    exigidos = {
        "LEF": set(), "TEF": {"suscetibilidade"}, "TEF_CAPACIDADE": {"capacidade", "resistencia"},
        "CONTATO_SUSC": {"acao", "suscetibilidade"}, "DECOMPOSTO": {"acao", "capacidade", "resistencia"},
    }[modo]
    for chave in ("acao", "suscetibilidade", "capacidade", "resistencia"):
        if chave in exigidos:
            resultado[chave] = faixa(dados[chave], chave, 1)
        else:
            if dados[chave] is not None:
                raise ValueError(f"{chave} não se aplica ao modo escolhido.")
            resultado[chave] = None
    perdas = dados["perdas"]
    if not isinstance(perdas, list) or not 1 <= len(perdas) <= 12:
        raise ValueError("Informe de uma a doze parcelas de perda.")
    resultado["perdas"] = []
    vistos = set()
    for item in perdas:
        if not isinstance(item, dict) or set(item) != {"tipo", "categoria", "valor", "probabilidade"}:
            raise ValueError("Parcela de perda inválida.")
        tipo, categoria = item["tipo"], item["categoria"]
        if not isinstance(tipo, str) or not isinstance(categoria, str) or tipo not in TIPOS or categoria not in CATEGORIAS or (tipo, categoria) in vistos:
            raise ValueError("Tipo/categoria inválido ou repetido.")
        vistos.add((tipo, categoria))
        chance = faixa(item["probabilidade"], "Chance condicional da parcela", 1)
        resultado["perdas"].append({"tipo": tipo, "categoria": categoria, "valor": faixa(item["valor"], "Magnitude", 1e12), "probabilidade": chance})
    if not any(item["tipo"] == "PRIMARIA" for item in resultado["perdas"]):
        raise ValueError("Informe pelo menos uma parcela de perda primária.")
    return resultado


def amostrar(limites, tamanho, rng):
    minimo, moda, maximo = limites
    if minimo == maximo:
        return np.full(tamanho, minimo, dtype=float)
    alfa = 1 + 4 * (moda - minimo) / (maximo - minimo)
    beta = 1 + 4 * (maximo - moda) / (maximo - minimo)
    return minimo + (maximo - minimo) * rng.beta(alfa, beta, size=tamanho)


def simular(dados, n=10000, seed=42):
    dados = validar(dados)
    if type(n) is not int or not 100 <= n <= 20000:
        raise ValueError("Informe de 100 a 20.000 simulações.")
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("Semente inválida.")
    rng = np.random.default_rng(seed)
    frequencia = amostrar(dados["frequencia"], n, rng)
    contatos = rng.poisson(frequencia)
    if int(contatos.sum()) > MAX_EVENTOS:
        raise ValueError("Limite de eventos excedido; reduza frequência ou simulações.")
    janelas = np.repeat(np.arange(n), contatos)
    total_contatos = len(janelas)
    modo = dados["modo"]
    if modo in {"DECOMPOSTO", "CONTATO_SUSC"}:
        acao = amostrar(dados["acao"], n, rng)
        acoes = rng.random(total_contatos) < acao[janelas]
        janelas_ameaca = janelas[acoes]
    elif modo in {"TEF", "TEF_CAPACIDADE"}:
        janelas_ameaca = janelas
    else:
        janelas_ameaca = None
    if modo in {"DECOMPOSTO", "TEF_CAPACIDADE"}:
        capacidade = amostrar(dados["capacidade"], len(janelas_ameaca), rng)
        resistencia = amostrar(dados["resistencia"], len(janelas_ameaca), rng)
        janelas_perda = janelas_ameaca[capacidade > resistencia]
        ameacas = len(janelas_ameaca)
    elif modo in {"TEF", "CONTATO_SUSC"}:
        susc = amostrar(dados["suscetibilidade"], n, rng)
        janelas_perda = janelas_ameaca[rng.random(len(janelas_ameaca)) < susc[janelas_ameaca]]
        ameacas = len(janelas_ameaca)
    else:
        janelas_perda = janelas
        ameacas = None
    total_eventos = len(janelas_perda)
    primaria, secundaria = np.zeros(n), np.zeros(n)
    parcelas = []
    for item in dados["perdas"]:
        custos = amostrar(item["valor"], total_eventos, rng)
        if item["tipo"] == "SECUNDARIA" or item["probabilidade"] != [1., 1., 1.]:
            prob = amostrar(item["probabilidade"], total_eventos, rng)
            custos *= rng.random(total_eventos) < prob
        acumulado = np.bincount(janelas_perda, weights=custos, minlength=n)
        if item["tipo"] == "PRIMARIA":
            primaria += acumulado
        else:
            secundaria += acumulado
        parcelas.append({"tipo": item["tipo"], "categoria": item["categoria"], "media": float(acumulado.mean())})
    total = primaria + secundaria
    limites = np.unique(np.r_[0., np.percentile(total, [50, 75, 90, 95, 99, 100])])
    return {"versao_modelo": "sauron.fair/30d-v1", "horizonte_dias": 30, "modo": modo, "n": n, "seed": seed,
            "perda": resumo(total), "probabilidade_evento": float(np.count_nonzero(np.bincount(janelas_perda, minlength=n)) / n),
            "eventos_medios": float(total_eventos / n), "ameacas_medias": None if ameacas is None else float(ameacas / n),
            "contatos_medios": float(total_contatos / n) if modo in {"DECOMPOSTO", "CONTATO_SUSC"} else None,
            "media_por_evento": float(total.sum() / total_eventos) if total_eventos else None,
            "media_primaria": float(primaria.mean()), "media_secundaria": float(secundaria.mean()),
            "parcelas": parcelas,
            "excedencia": [{"valor": float(x), "percentual": float((total > x).mean() * 100)} for x in limites]}
