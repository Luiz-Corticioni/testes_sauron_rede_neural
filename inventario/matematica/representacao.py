"""Leitura das matrizes JSON densas (pequenas) ou CSR (inventários grandes)."""
from scipy import sparse


def como_csr(dados, shape=None):
    if isinstance(dados, dict):
        if dados.get("formato") != "csr":
            raise ValueError("Representação de matriz desconhecida.")
        return sparse.csr_matrix((dados["data"], dados["indices"], dados["indptr"]), shape=tuple(dados["shape"]))
    if shape is not None and (not shape[0] or not shape[1]):
        return sparse.csr_matrix(shape, dtype=float)
    return sparse.csr_matrix(dados, dtype=float)


def janela(dados, linhas=40, colunas=40):
    if isinstance(dados, dict):
        return como_csr(dados)[:linhas, :colunas].toarray().tolist()
    return [linha[:colunas] for linha in dados[:linhas]]
