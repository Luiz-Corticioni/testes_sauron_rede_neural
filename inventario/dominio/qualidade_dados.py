"""Índice explicável de completude de evidências; não mede risco nem segurança."""
from math import isfinite


def componente(codigo, nome, validos, total, origem, data=None, motivo=""):
    if (not codigo or not nome or not origem or (total is None) != (validos is None)
            or (total is not None and (type(total) is not int or type(validos) is not int
                                       or total < 1 or not 0 <= validos <= total))):
        raise ValueError("Componente de qualidade inválido.")
    return {"codigo": codigo, "nome": nome, "validos": validos, "total": total,
            "percentual": round(100 * validos / total, 2) if total is not None else None,
            "origem": origem, "data": data, "idade_dias": None, "motivo": motivo}


def avaliar(componentes):
    if not isinstance(componentes, list) or not componentes:
        raise ValueError("Informe os componentes de qualidade.")
    codigos = [item["codigo"] for item in componentes]
    if len(set(codigos)) != len(codigos):
        raise ValueError("Componente de qualidade repetido.")
    valores = [item["percentual"] for item in componentes]
    if any(v is not None and (not isinstance(v, (int, float)) or not isfinite(v) or not 0 <= v <= 100) for v in valores):
        raise ValueError("Percentual de qualidade inválido.")
    completo = all(v is not None for v in valores)
    return {"versao": "sauron.qualidade/1", "score": round(sum(valores) / len(valores), 2) if completo else None,
            "metodo": "Média aritmética de componentes com pesos iguais; indisponível se algum componente for indeterminado.",
            "componentes": componentes,
            "aviso": "Índice de completude das evidências declaradas, não mede segurança, risco, precisão nem probabilidade."}
