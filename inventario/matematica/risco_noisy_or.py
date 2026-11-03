"""Noisy-OR experimental: menor ponto fixo em [0,1], sem integração à aplicação.

P_i = 1 - (1-p_i) produto_j (1-a_ij P_j). Pesos e p são probabilidades
adimensionais; soma de linha pode exceder 1. Monotonicidade garante sequência
crescente iniciada em zero, não unicidade do ponto fixo nem velocidade uniforme.
Para probabilidades pequenas, Leontief é aproximação de primeira ordem,
mas soma pontos e pode ultrapassar 1; os dois modelos não são intercambiáveis.
"""
import numpy as np
from scipy import sparse


def calcular(p,a,tolerancia=1e-10,max_iteracoes=10000,historico=False):
    p=np.asarray(p,dtype=float)
    a=sparse.csr_matrix(a,dtype=float)
    if p.ndim!=1 or a.shape!=(len(p),len(p)) or not np.all(np.isfinite(p)):
        raise ValueError("Dimensões ou probabilidades inválidas.")
    if np.any((p<0)|(p>1)) or not np.all(np.isfinite(a.data)) or np.any((a.data<0)|(a.data>1)):
        raise ValueError("Probabilidades e pesos devem estar em [0,1].")
    if not np.isfinite(tolerancia) or tolerancia<=0 or type(max_iteracoes) is not int or max_iteracoes<1:
        raise ValueError("Tolerância/iterações inválidas.")
    x=np.zeros(len(p))
    coo=a.tocoo()
    passos=[x.tolist()] if historico else None
    def aplicar(x):
        with np.errstate(divide="ignore",invalid="raise"):
            log=np.log1p(-coo.data*x[coo.col])
            produto=np.exp(np.bincount(coo.row,weights=log,minlength=len(p)))
        return np.clip(1-(1-p)*produto,0,1)
    for iteracao in range(1,max_iteracoes+1):
        novo=np.maximum(x,aplicar(x))
        erro=float(np.max(abs(novo-x))) if len(p) else 0
        x=novo
        if historico:
            passos.append(x.tolist())
        if erro<tolerancia:
            residuo=float(np.max(abs(aplicar(x)-x))) if len(p) else 0
            return {"probabilidades":x.tolist(),"iteracoes":iteracao,"residuo":residuo,
                    "historico":passos}
    raise ValueError("Ponto fixo não convergiu no limite; amplie iterações ou revise os parâmetros.")

