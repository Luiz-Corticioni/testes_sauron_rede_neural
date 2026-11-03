from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu, spsolve

from inventario.matematica.estabilidade import validar_matriz
from inventario.matematica.diagnostico import residuos
from inventario.dominio.vulnerabilidades import Dependencia, Incidencia, Vulnerabilidade


@dataclass(slots=True)
class ResultadoRisco:
    ids_ativos: list[str]
    ids_vulnerabilidades: list[str]
    matriz_incidencia: list[list[float]]
    vetor_cvss: list[float]
    matriz_dependencias: list[list[float]]
    risco_proprio: list[float]
    risco_efetivo: list[float]
    numero_condicao: float
    raio_espectral: float
    series_saltos: list[list[float]]
    prioridade_correcao: list[dict]
    perfil: str
    vetor_severidade: list[float]
    risco_relatorio: list[float]
    pesos_relatorio: list[float]
    indices: list[float]
    kappa: float
    tau: float
    residuo_absoluto: float
    residuo_relativo: float
    fatores_aplicados: list[float]

    def to_dict(self) -> dict:
        dados = asdict(self)
        for nome in ("matriz_incidencia", "matriz_dependencias"):
            if isinstance(dados[nome], VisaoMatriz):
                dados[nome] = dados[nome].to_json()
        return dados


class VisaoMatriz:
    """Sequência de linhas; materialização densa ocorre só na exportação explícita."""
    def __init__(self, matriz):
        self.matriz = matriz

    def __len__(self):
        return self.matriz.shape[0]

    def __getitem__(self, indice):
        if indice >= len(self) or indice < -len(self):
            raise IndexError(indice)
        return self.matriz[indice:indice+1].toarray().ravel().tolist()

    def __deepcopy__(self, memo):
        return self

    def to_json(self):
        csr = self.matriz.tocsr()
        return {"formato": "csr", "shape": list(csr.shape), "data": csr.data.tolist(),
                "indices": csr.indices.tolist(), "indptr": csr.indptr.tolist()}

    def tolist(self):
        return self.matriz.toarray().tolist()


def representar(matriz):
    return matriz.toarray().tolist() if max(matriz.shape, default=0) <= 300 else VisaoMatriz(matriz)


class ModeloRisco:
    LIMITE_CONDICAO = 1e12

    def __init__(
        self,
        ids_ativos: list[str],
        vulnerabilidades: list[Vulnerabilidade],
        incidencias: list[Incidencia],
        dependencias: list[Dependencia],
        fatores_exposicao: dict[str, float] | None = None,
        kev_ids: set[str] | None = None,
        pesos_relatorio: dict[str, float] | None = None,
        scores_ambientais: dict[str, float] | None = None,
    ):
        self.ids_ativos = ids_ativos
        self.vulnerabilidades = vulnerabilidades
        self.incidencias = incidencias
        self.dependencias = dependencias
        self.fatores = fatores_exposicao or {item: 1.0 for item in ids_ativos}
        self.kev_ids = kev_ids or set()
        self.pesos = pesos_relatorio or {}
        self.scores_ambientais = scores_ambientais or {}

    def montar(self):
        n, m = len(self.ids_ativos), len(self.vulnerabilidades)
        ai = {identificador: i for i, identificador in enumerate(self.ids_ativos)}
        vi = {v.id: j for j, v in enumerate(self.vulnerabilidades)}
        matriz_m = sparse.lil_matrix((n, m), dtype=float)
        for incidencia in self.incidencias:
            if incidencia.equipamento_id in ai and incidencia.vulnerabilidade_id in vi:
                status = incidencia.status.upper()
                if status not in {
                    "ABERTA",
                    "TRATAMENTO",
                    "ACEITA",
                    "CORRIGIDA",
                    "MITIGADA",
                    "SUGERIDA",
                }:
                    raise ValueError(f"Status de incidência desconhecido: {status}.")
                if status in {"ABERTA", "TRATAMENTO", "ACEITA"}:
                    matriz_m[ai[incidencia.equipamento_id], vi[incidencia.vulnerabilidade_id]] = 1.0
        vetor_v = np.array([v.cvss for v in self.vulnerabilidades], dtype=float)
        matriz_a = sparse.lil_matrix((n, n), dtype=float)
        for dep in self.dependencias:
            if dep.dependente_id in ai and dep.fornecedor_id in ai:
                matriz_a[ai[dep.dependente_id], ai[dep.fornecedor_id]] = dep.peso
        matriz_e = sparse.diags([self.fatores.get(i, 1.0) for i in self.ids_ativos], shape=(n,n), format="csr")
        return matriz_m.tocsr(), vetor_v, matriz_a.tocsr(), matriz_e

    def calcular(
        self,
        usar_exposicao: bool = False,
        saltos: int = 4,
        perfil: str = "puro",
        kappa: float = 0.3,
        tau: float = 25,
        precisao: int = 6,
        diagnostico: bool = False,
    ) -> ResultadoRisco:
        # O parâmetro legado continua disponível; corresponde ao perfil operacional.
        perfil = "operacional" if usar_exposicao else perfil
        if perfil not in {"puro", "operacional"}:
            raise ValueError("Escolha o perfil puro ou operacional.")
        if not np.all(np.isfinite([kappa, tau])) or kappa < 0 or tau <= 0:
            raise ValueError("kappa deve ser finito e não negativo; tau, finito e positivo.")
        m, v, a, e = self.montar()
        condicao, raio = validar_matriz(a, self.LIMITE_CONDICAO, diagnostico=diagnostico)
        if not np.all(np.isfinite(v)) or np.any(v < 0) or np.any(v > 10):
            raise ValueError("CVSS deve ser finito e estar entre 0 e 10.")
        if not np.all(np.isfinite(e.data)) or np.any(e.data < 0):
            raise ValueError("Fatores de exposição devem ser finitos e não negativos.")
        pesos = np.array([self.pesos.get(aid, 1) for aid in self.ids_ativos], dtype=float)
        if not np.all(np.isfinite(pesos)) or np.any(pesos <= 0):
            raise ValueError("Pesos do relatório devem ser finitos e positivos.")
        kev = np.array([vul.id in self.kev_ids for vul in self.vulnerabilidades])
        severidade = v * (1 + kappa * kev) if perfil == "operacional" else v.copy()
        incidencia_ponderada = e @ m if perfil == "operacional" else m
        b = incidencia_ponderada @ severidade
        if not np.all(np.isfinite(b)) or not np.all(np.isfinite(severidade)):
            raise ValueError("Parâmetros produziram risco fora da faixa numérica.")
        sistema = sparse.eye(len(self.ids_ativos), format="csc") - a
        resolver = splu(sistema.tocsc()).solve if len(b) else lambda rhs: np.zeros_like(rhs)
        x = resolver(b)
        residuo_absoluto, residuo_relativo = residuos(sistema, x, b)
        relatorio = pesos * x
        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(relatorio)):
            raise ValueError("Resultado de risco fora da faixa numérica.")
        termos = []
        atual = b.copy()
        for _ in range(max(1, saltos)):
            termos.append(atual.round(precisao).tolist())
            atual = a @ atual

        prioridades = []
        for j, vulnerabilidade in enumerate(self.vulnerabilidades):
            ganho_por_ativo = resolver(incidencia_ponderada[:,j].toarray().ravel()) * severidade[j]
            prioridades.append(
                {
                    "vulnerabilidade_id": vulnerabilidade.id,
                    "cve_id": vulnerabilidade.cve_id,
                    "cvss": vulnerabilidade.cvss,
                    "reducao_total_estimada": round(float(ganho_por_ativo.sum()), 6),
                    "reducao_por_ativo": ganho_por_ativo.round(precisao).tolist(),
                }
            )
        if self.scores_ambientais:
            prioridades.sort(key=lambda item: (item["reducao_total_estimada"] > 0, self.scores_ambientais.get(item["vulnerabilidade_id"],item["cvss"]),
                                                item["reducao_total_estimada"]),reverse=True)
        else:
            prioridades.sort(key=lambda item: item["reducao_total_estimada"], reverse=True)

        return ResultadoRisco(
            ids_ativos=self.ids_ativos,
            ids_vulnerabilidades=[item.id for item in self.vulnerabilidades],
            matriz_incidencia=representar(m),
            vetor_cvss=v.tolist(),
            matriz_dependencias=representar(a),
            risco_proprio=b.round(precisao).tolist(),
            risco_efetivo=x.round(precisao).tolist(),
            numero_condicao=round(condicao, 6) if condicao is not None else None,
            raio_espectral=round(raio, 6),
            series_saltos=termos,
            prioridade_correcao=prioridades,
            perfil=perfil,
            vetor_severidade=severidade.tolist(),
            risco_relatorio=relatorio.round(precisao).tolist(),
            pesos_relatorio=pesos.tolist(),
            indices=(-100 * np.expm1(-x / tau)).round(precisao).tolist(),
            kappa=kappa,
            tau=tau,
            residuo_absoluto=residuo_absoluto,
            residuo_relativo=residuo_relativo,
            fatores_aplicados=e.diagonal().tolist() if perfil == "operacional" else [1.0] * len(self.ids_ativos),
        )

    def simular(self, incidencias_corrigidas: list[str], **parametros) -> dict:
        if not isinstance(incidencias_corrigidas, list) or not all(
            isinstance(i, str) for i in incidencias_corrigidas
        ):
            raise ValueError("Envie uma lista de IDs de incidências.")
        selecionadas = set(incidencias_corrigidas)
        if len(selecionadas) != len(incidencias_corrigidas):
            raise ValueError("A lista de incidências contém IDs repetidos.")
        existentes = {i.id for i in self.incidencias}
        if selecionadas - existentes:
            raise ValueError("A lista contém incidências inexistentes.")
        antes = self.calcular(**parametros).to_dict()
        incidencias = [
            replace(i, status="CORRIGIDA") if i.id in selecionadas else i for i in self.incidencias
        ]
        candidato = ModeloRisco(
            self.ids_ativos,
            self.vulnerabilidades,
            incidencias,
            self.dependencias,
            self.fatores,
            self.kev_ids,
            self.pesos,
            self.scores_ambientais,
        )
        depois = candidato.calcular(**parametros).to_dict()
        ganho = np.array(antes["risco_efetivo"]) - np.array(depois["risco_efetivo"])
        return {
            "antes": antes,
            "depois": depois,
            "incidencias_corrigidas": incidencias_corrigidas,
            "ganho_por_ativo": ganho.round(6).tolist(),
            "ganho_total": round(float(ganho.sum()), 6),
        }

    def limiar_transmissao(
        self, indice_ativo: int, limite_risco: float, maximo: float = 2.0, tolerancia: float = 1e-6
    ) -> float | None:
        m, v, a, _ = self.montar()
        _, raio = validar_matriz(a, self.LIMITE_CONDICAO)
        if not 0 <= indice_ativo < len(self.ids_ativos):
            raise ValueError("Índice de ativo fora do inventário.")
        if not np.all(np.isfinite([limite_risco, maximo, tolerancia])):
            raise ValueError("Os parâmetros da bisseção devem ser finitos.")
        if limite_risco < 0 or maximo <= 0 or tolerancia <= 0:
            raise ValueError("Use risco não negativo, máximo e tolerância positivos.")
        if not np.all(np.isfinite(v)) or np.any(v < 0) or np.any(v > 10):
            raise ValueError("CVSS deve ser finito e estar entre 0 e 10.")
        b = m @ v

        def risco(lam: float) -> float:
            return float(spsolve(sparse.eye(len(b))-lam*a,b)[indice_ativo])

        # A propagação cresce monotonicamente somente enquanto λ·ρ(A) < 1.
        baixo = 0.0
        alto = min(maximo, (1 - 1e-6) / raio) if raio else maximo
        if risco(baixo) >= limite_risco:
            return 0.0
        if len(b) <= 300 and np.linalg.cond(np.eye(len(b)) - alto * a.toarray()) > self.LIMITE_CONDICAO:
            raise ValueError("Intervalo de bisseção numericamente instável.")
        if risco(alto) < limite_risco:
            return None
        for _ in range(100):
            meio = (baixo + alto) / 2
            if risco(meio) >= limite_risco:
                alto = meio
            else:
                baixo = meio
            if alto - baixo <= tolerancia:
                break
        return round((baixo + alto) / 2, 6)
