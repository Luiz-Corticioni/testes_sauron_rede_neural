"""Comparação de gravidade: 3.1 calculado localmente e 4.0 publicado na NVD.

A diferença entre versões não representa erro, probabilidade ou risco matricial.
A validação do 4.0 cobre estrutura e faixa; não implementa seu algoritmo de score.
"""

from decimal import Decimal
import math
from inventario.matematica.cvss import CalculadoraCVSS31, vetor_base31
from inventario.dominio.enums import classificar_cvss

GRUPOS = {
    "3.1": "cvssMetricV31",
    "3.0": "cvssMetricV30",
    "4.0": "cvssMetricV40",
    "2.0": "cvssMetricV2",
}
BASE40 = {
    "AV": "NALP",
    "AC": "LH",
    "AT": "NP",
    "PR": "NLH",
    "UI": "NPA",
    **{c: "HLN" for c in ("VC", "VI", "VA", "SC", "SI", "SA")},
}
OPCIONAIS40 = {
    "E": "XAPU",
    "CR": "XHML",
    "IR": "XHML",
    "AR": "XHML",
    **{"M" + k: "X" + v for k, v in BASE40.items()},
    "MSI": "XSHLN",
    "MSA": "XSHLN",
    "S": "XNP",
    "AU": "XNY",
    "R": "XAUI",
    "V": "XDC",
    "RE": "XLMH",
    "U": ("X", "CLEAR", "GREEN", "AMBER", "RED"),
}


def metrica_ausente(versao):
    return {
        "versao": versao,
        "nota": None,
        "vetor": "",
        "publicador": "",
        "tipo": "",
        "origem": "NVD",
        "nomenclatura": "",
        "severidade": "",
        "utilizavel": False,
        "verificacao": "não disponível",
        "aviso": "Nota não disponível nesta versão.",
    }


def estrutura40(vetor):
    if not isinstance(vetor, str) or len(vetor) > 2048:
        raise ValueError("Vetor CVSS 4.0 inválido.")
    partes = vetor.strip().upper().split("/")
    if partes[0] != "CVSS:4.0":
        raise ValueError("O vetor não é CVSS 4.0.")
    m = {}
    for parte in partes[1:]:
        if parte.count(":") != 1:
            raise ValueError("Métrica 4.0 malformada.")
        chave, valor = parte.split(":")
        validos = BASE40.get(chave, OPCIONAIS40.get(chave, ()))
        if (
            chave in m
            or not valor
            or valor not in validos
            or (isinstance(validos, str) and len(valor) != 1)
        ):
            raise ValueError("Métrica 4.0 inválida ou repetida.")
        m[chave] = valor
    if not BASE40.keys() <= m.keys():
        raise ValueError("Faltam métricas base 4.0.")
    t = m.get("E", "X") != "X"
    e = any(
        v != "X"
        for k, v in m.items()
        if k in OPCIONAIS40 and (k.startswith("M") or k in ("CR", "IR", "AR"))
    )
    return "CVSS-B" + ("T" if t else "") + ("E" if e else "")


def avaliacoes(cve, versao):
    metricas = cve.get("metrics", {})
    itens = metricas.get(GRUPOS[versao], []) if isinstance(metricas, dict) else []
    if not isinstance(itens, list):
        return []
    resultado = []
    for item in itens[:100]:
        if not isinstance(item, dict) or not isinstance(item.get("cvssData"), dict):
            continue
        dados = item["cvssData"]
        nota = dados.get("baseScore")
        if (
            dados.get("version") != versao
            or type(nota) not in (int, float)
            or not math.isfinite(nota)
            or not 0 <= nota <= 10
            or abs(nota * 10 - round(nota * 10)) > 1e-8
        ):
            continue
        r = metrica_ausente(versao)
        r.update(
            nota=float(nota),
            vetor=dados.get("vectorString", ""),
            publicador=str(item.get("source") or "não informado")[:200],
            tipo=str(item.get("type", "não informado"))[:40],
        )
        try:
            if versao == "3.1":
                r["vetor_base"] = vetor_base31(r["vetor"])
                r["nomenclatura"] = "CVSS-B"
            elif versao == "4.0":
                r["nomenclatura"] = estrutura40(r["vetor"])
            elif not isinstance(r["vetor"], str):
                raise ValueError("Vetor inválido.")
            r.update(
                utilizavel=True, verificacao="estrutura; nota não recalculada localmente", aviso=""
            )
        except (ValueError, TypeError, KeyError, AttributeError):
            r.update(
                aviso="Vetor ausente ou inválido; comparação indisponível.",
                vetor=r["vetor"] if isinstance(r["vetor"], str) else "",
            )
        r["severidade"] = classificar_cvss(nota).value
        resultado.append(r)
    return sorted(
        resultado,
        key=lambda r: (
            not r["utilizavel"],
            r["publicador"].casefold() != "nvd@nist.gov",
            r["tipo"] != "Primary",
            r["publicador"],
            r["vetor"],
        ),
    )


def selecionar_metrica(cve, versao):
    itens = avaliacoes(cve, versao)
    return itens[0] if itens else metrica_ausente(versao)


def diferenca(a, b):
    return float(Decimal(str(a)) - Decimal(str(b))) if a is not None and b is not None else None


def comparar_notas(cve, vetor_local="", origem_local="vetor 3.1 da NVD recalculado no Sauron"):
    cve = cve if isinstance(cve, dict) else {}
    n31, n40 = (selecionar_metrica(cve, v) for v in ("3.1", "4.0"))
    local = {
        "nota": None,
        "vetor": "",
        "origem": origem_local,
        "severidade": "",
        "impacto": None,
        "explorabilidade": None,
    }
    avisos = []
    if cve.get("vulnStatus") == "Rejected":
        avisos.append("CVE rejeitada pela fonte; não use suas notas para decisão.")
    else:
        vetor = vetor_local or (n31.get("vetor_base", "") if n31["utilizavel"] else "")
        if vetor:
            r = CalculadoraCVSS31.calcular(vetor)
            local.update(
                nota=r.score,
                vetor=r.vetor,
                severidade=r.severidade,
                impacto=r.impacto,
                explorabilidade=r.explorabilidade,
            )
    if local["nota"] is None:
        local["origem"] = "sem vetor 3.1 disponível para cálculo"
    if (
        n31["nota"] is not None
        and n40["nota"] is not None
        and n31["publicador"] != n40["publicador"]
    ):
        avisos.append(
            "As notas da NVD têm publicadores diferentes; a diferença pode refletir também avaliações distintas."
        )
    mesmo = None
    delta31 = None
    if local["nota"] is not None and n31["utilizavel"]:
        mesmo = dict(p.split(":") for p in local["vetor"].split("/")[1:]) == dict(
            p.split(":") for p in n31["vetor_base"].split("/")[1:]
        )
        delta31 = diferenca(n31["nota"], local["nota"])
        if not mesmo:
            avisos.append(
                "São vetores diferentes em 3.1; a diferença pode refletir avaliações distintas, não um erro do cálculo."
            )
        elif delta31:
            avisos.append(
                "Divergência em 3.1 para o mesmo vetor: revise a nota publicada antes de usá-la."
            )
    if not n31["utilizavel"]:
        avisos.append(
            "A NVD não forneceu vetor 3.1 utilizável; informe um vetor base para cálculo local."
        )
    if not n40["utilizavel"]:
        avisos.append("CVSS 4.0 não disponível com vetor válido; ausência não equivale a zero.")
    elif n40["nomenclatura"] != "CVSS-B":
        avisos.append(
            "O vetor 4.0 inclui ameaça/ambiente; não se calcula diferença contra a base 3.1."
        )
    delta40 = (
        diferenca(n40["nota"], local["nota"])
        if n40["utilizavel"] and n40["nomenclatura"] == "CVSS-B"
        else None
    )
    return {
        "cve_id": str(cve.get("id", "")),
        "local31": local,
        "nvd31": n31,
        "nvd40": n40,
        "diferenca_40_menos_31": delta40,
        "diferenca_31_nvd_menos_local": delta31,
        "mesmo_vetor31": mesmo,
        "avaliacoes": avaliacoes(cve, "3.1") + avaliacoes(cve, "4.0"),
        "avisos": avisos,
        "aviso_versoes": "3.1 e 4.0 usam modelos diferentes. A diferença em pontos não representa probabilidade nem erro por si só.",
    }
