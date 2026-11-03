"""Interpretação de M e conferência numérica, sem interface ou persistência."""

import numpy as np
from scipy import sparse
from inventario.matematica.representacao import como_csr


def residuos(sistema, x, b):
    """Resíduo bruto e erro retroativo normwise, calculados antes de arredondar x."""
    if not len(b):
        return 0.0, 0.0
    with np.errstate(over="ignore", invalid="ignore"):
        absoluto = float(np.linalg.norm(sistema @ x - b, ord=np.inf))
        norma_x = float(np.linalg.norm(x, ord=np.inf))
        norma_b = float(np.linalg.norm(b, ord=np.inf))
        escala = max(norma_x, norma_b, 1.0)
        norma_s = float(np.asarray(abs(sistema).sum(axis=1)).max()) if sparse.issparse(sistema) else float(np.linalg.norm(sistema, ord=np.inf))
        denominador = norma_s * (norma_x / escala) + norma_b / escala
        relativo = (absoluto / escala) / denominador if denominador else 0.0
    if not np.isfinite(absoluto) or not np.isfinite(relativo):
        raise ValueError("Não foi possível conferir o resíduo dentro da faixa numérica.")
    return absoluto, relativo


class DiagnosticoLinear:
    LIMITE_POSTO = 200

    @classmethod
    def analisar(cls, risco, ativo_id=None):
        ids, falhas = risco["ids_ativos"], risco["ids_vulnerabilidades"]
        n, m = len(ids), len(falhas)
        matriz = como_csr(risco["matriz_incidencia"], (n, m))
        ocupadas = np.asarray(matriz.getnnz(axis=0)).ravel()
        diagnostico = {
            "n": n, "m": m, "dimensao": f"R^{m} → R^{n}",
            "posto": None, "nulidade": None, "posto_limitado": max(n, m) > cls.LIMITE_POSTO,
            "colunas_nulas": [falhas[j] for j in range(m) if not ocupadas[j]],
            "residuo_absoluto": risco["residuo_absoluto"],
            "residuo_relativo": risco["residuo_relativo"],
            "numero_condicao": risco["numero_condicao"], "equacao": None,
        }
        if not diagnostico["posto_limitado"]:
            posto = int(np.linalg.matrix_rank(matriz.toarray())) if n and m else 0
            diagnostico.update(posto=posto, nulidade=m-posto)
        if ativo_id is not None:
            if ativo_id not in ids:
                raise ValueError("Ativo fora do modelo de risco.")
            i = ids.index(ativo_id)
            parcelas = [
                {"vulnerabilidade": falhas[j], "cvss": risco["vetor_cvss"][j],
                 "severidade": risco["vetor_severidade"][j]}
                for j in matriz.getrow(i).indices
            ]
            linha_a = como_csr(risco["matriz_dependencias"], (n, n)).getrow(i)
            fornecedores = [
                {"id": ids[j], "peso": peso, "risco_efetivo": risco["risco_efetivo"][j],
                 "parcela": peso * risco["risco_efetivo"][j]}
                for j, peso in zip(linha_a.indices, linha_a.data) if peso > 0
            ]
            diagnostico["equacao"] = {
                "id": ativo_id, "parcelas": parcelas, "fornecedores": fornecedores,
                "risco_proprio": risco["risco_proprio"][i], "risco_efetivo": risco["risco_efetivo"][i],
                "perfil": risco["perfil"],
                "fator_aplicado": risco["fatores_aplicados"][i],
            }
        return diagnostico
