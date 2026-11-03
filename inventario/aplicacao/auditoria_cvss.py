"""Conferência somente de leitura; não corrige avaliações sem revisão humana."""

import math
from inventario.matematica.cvss import CalculadoraCVSS31, vetor_base31


def auditar_notas(registros):
    r = {
        "verificados": 0,
        "base31_conferida": 0,
        "sem_vetor31": 0,
        "outras_versoes": 0,
        "divergencias": [],
    }
    for v in registros:
        r["verificados"] += 1
        nota = v.get("cvss")
        problema = {"id": v.get("id"), "cve": v.get("cve_id"), "nota_cadastrada": nota}
        if (
            type(nota) not in (int, float)
            or not math.isfinite(nota)
            or not 0 <= nota <= 10
            or abs(nota * 10 - round(nota * 10)) > 1e-8
        ):
            problema.update(
                nota_cadastrada=str(nota),
                erro="Nota inválida: exige 0–10, finita e uma casa decimal.",
            )
            r["divergencias"].append(problema)
        elif v.get("cvss_versao") != "3.1":
            r["outras_versoes"] += 1
        elif not v.get("cvss_vetor"):
            r["sem_vetor31"] += 1
        else:
            try:
                calculada = CalculadoraCVSS31.calcular(vetor_base31(v["cvss_vetor"])).score
                r["base31_conferida"] += 1
                if calculada != nota:
                    problema.update(
                        nota_calculada=calculada,
                        erro="Nota cadastrada diverge da base 3.1 calculada.",
                    )
                    r["divergencias"].append(problema)
            except ValueError as erro:
                problema["erro"] = str(erro)
                r["divergencias"].append(problema)
    r["ok"] = not r["divergencias"]
    r["escopo"] = (
        "Recálculo da base CVSS 3.1; ausência de vetor e outras versões não são atestadas por esta conferência."
    )
    return r
