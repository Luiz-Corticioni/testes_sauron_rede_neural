"""Recomendação por similaridade, com dois sinais e memória limitada."""

from dataclasses import asdict, dataclass
import math
import re
import unicodedata

from inventario.matematica.euler import Derivador, FuncaoMatematica


def normalizar_texto(valor):
    texto = unicodedata.normalize("NFKD", str(valor or "").strip().lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


@dataclass(frozen=True)
class Antigeno:
    categoria: str
    tipo: str
    fabricante: str = ""
    familia: str = ""
    versao_maior: str = ""
    versao_menor: str = ""
    exposto_internet: bool = False
    vetor_ataque: str = ""
    cpe23: str = ""

    def normalizado(self, ignorados=()):
        # One-hot esparso: cada eixo é campo=valor, sem hashes/colisões.
        dados = asdict(self)
        for campo in ("cpe23", "categoria", "vetor_ataque", "versao_maior", "versao_menor"):
            dados.pop(campo)
        valores = {
            f"{campo}={normalizar_texto(valor)}": 1.0
            for campo, valor in dados.items()
            if campo not in ignorados and valor != ""
        }
        norma = math.sqrt(len(valores))
        return {k: v / norma for k, v in valores.items()} if norma else {}

    def to_dict(self):
        return asdict(self)


def similaridade_cosseno(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        produto = sum(v * b.get(k, 0) for k, v in a.items())
        valores_a, valores_b = a.values(), b.values()
    else:
        if len(a) != len(b):
            raise ValueError("Vetores com dimensões diferentes.")
        produto = sum(x * y for x, y in zip(a, b))
        valores_a, valores_b = a, b
    if not all(math.isfinite(float(v)) and v >= 0 for v in [*valores_a, *valores_b]):
        raise ValueError("Características precisam ser finitas e não negativas.")
    norma_a = math.sqrt(sum(x * x for x in valores_a))
    norma_b = math.sqrt(sum(x * x for x in valores_b))
    return min(1.0, max(0.0, produto / (norma_a * norma_b))) if norma_a and norma_b else 0.0


@dataclass
class Anticorpo:
    id: str
    vulnerabilidade_id: str
    prototipo: dict
    forca: float = 1.0
    confirmacoes: int = 1
    rejeicoes: int = 0

    def __post_init__(self):
        if not math.isfinite(self.forca) or not 0 <= self.forca <= 1:
            raise ValueError("Força deve estar entre zero e um.")
        Antigeno(**self.prototipo)

    def avaliar(self, alvo, ignorados=()):
        origem = Antigeno(**self.prototipo)
        if (origem.versao_maior and alvo.versao_maior
                and (origem.versao_maior, origem.versao_menor) != (alvo.versao_maior, alvo.versao_menor)):
            return 0.0
        if (origem.familia and alvo.familia
                and normalizar_texto(origem.familia) != normalizar_texto(alvo.familia)):
            return 0.0
        if origem.cpe23 and origem.cpe23 == alvo.cpe23:
            # Regra inata: dois vetores one-hot da identidade CPE têm cosseno 1.
            return 1.0
        return similaridade_cosseno(
            origem.normalizado(ignorados), alvo.normalizado(ignorados)
        )

    def reforcar(self, confirmado):
        if confirmado:
            self.confirmacoes += 1
            self.forca = min(1.0, self.forca + 0.1)
        else:
            self.rejeicoes += 1
            self.forca = max(0.0, self.forca - 0.15)

    def deve_suspender(self, limite=0.6, minimo=3):
        total = self.confirmacoes + self.rejeicoes
        return self.rejeicoes >= minimo and total > 0 and self.rejeicoes / total > limite

    def decaimento(self, dias, meia_vida):
        if not math.isfinite(dias) or dias < 0 or not math.isfinite(meia_vida) or meia_vida <= 0:
            raise ValueError("Idade deve ser não negativa e meia-vida positiva.")
        return self.forca * math.exp(-math.log(2) * dias / meia_vida)

    def curva(self, dias, meia_vida):
        self.decaimento(dias, meia_vida)  # Valida os parâmetros antes de formar a expressão.
        expressao = f"{self.forca}*exp(-log(2)*x/{meia_vida})"
        f = FuncaoMatematica(expressao)
        return {
            "expressao": expressao,
            "forca": f.avaliar(dias),
            "derivada": Derivador.central(f.avaliar, dias),
            "unidade": "força/dia",
        }


def avaliar_sinais(afinidade, sinais, limiar=0.75):
    if not math.isfinite(afinidade) or not 0 <= afinidade <= 1 or not 0 < limiar <= 1:
        raise ValueError("Afinidade/limiar inválidos.")
    if afinidade < limiar - 1e-9:
        return None
    return "PENDENTE" if sinais else "OBSERVACAO"


def separar_versao(versao):
    numeros = re.findall(r"\d+", versao or "")
    return (numeros[0] if numeros else "", numeros[1] if len(numeros) > 1 else "")
