"""Validação esparsa; diagnósticos densos são opcionais acima de 300 ativos."""
import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import eigs, ArpackNoConvergence


def validar_matriz(a, limite_condicao=1e12, diagnostico=False):
    a = sparse.csr_matrix(a, dtype=float)
    n = a.shape[0]
    if a.shape[0] != a.shape[1]:
        raise ValueError("A matriz A deve ser quadrada.")
    if not np.all(np.isfinite(a.data)) or np.any(a.data < 0) or np.any(a.data >= 1):
        raise ValueError("A matriz A exige valores finitos em 0 ≤ Aij < 1.")
    if np.any(a.diagonal() != 0):
        raise ValueError("A diagonal de A deve ser zero.")
    if n == 0:
        return 1.0, 0.0
    if n <= 300 or diagnostico:
        densa = a.toarray()
        raio = float(np.max(np.abs(np.linalg.eigvals(densa))))
    elif connected_components(a, directed=True, connection="strong", return_labels=False) == n:
        # Sem diagonal e sem componentes fortemente conexos não triviais:
        # o grafo é acíclico, A é nilpotente e o raio espectral é exatamente zero.
        raio = 0.0
    else:
        try:
            raio = float(abs(eigs(a, k=1, which="LM", return_eigenvectors=False,
                                  tol=1e-10, maxiter=5000, v0=np.ones(n))[0]))
        except ArpackNoConvergence as erro:
            raise ValueError("Estimativa espectral não convergiu; diagnóstico explícito necessário.") from erro
    if raio >= 1:
        raise ValueError(f"Raio espectral de A = {raio:.6f}; o modelo exige raio espectral menor que 1.")
    if n > 300 and not diagnostico:
        return None, raio
    sistema = np.eye(n)-densa
    condicao = float(np.linalg.cond(sistema))
    if not np.isfinite(condicao) or condicao > limite_condicao:
        raise ValueError(f"Sistema numericamente instável (condição={condicao:.3e}).")
    return condicao, raio

