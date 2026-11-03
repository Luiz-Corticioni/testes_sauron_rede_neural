"""Calculadora auditável do CVSS Base 3.1."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

from inventario.dominio.enums import classificar_cvss


VALORES = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20},
    "AC": {"L": 0.77, "H": 0.44},
    "UI": {"N": 0.85, "R": 0.62},
    "CIA": {"H": 0.56, "L": 0.22, "N": 0.0},
}
BASE_OBRIGATORIAS = ("AV", "AC", "PR", "UI", "S", "C", "I", "A")


def round_up_1(valor: float) -> float:
    # FIRST, Apêndice A: eliminar ruído além de cinco casas antes de elevar a nota.
    estavel = Decimal(str(valor)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)
    return float(estavel.quantize(Decimal("0.1"), rounding=ROUND_CEILING))


def interpretar_vetor(vetor: str) -> dict[str, str]:
    if not isinstance(vetor, str):
        raise ValueError("Informe o vetor CVSS como texto.")
    partes = vetor.strip().upper().split("/")
    if not partes or partes[0] != "CVSS:3.1":
        raise ValueError("O vetor deve começar com CVSS:3.1/.")
    metricas: dict[str, str] = {}
    for parte in partes[1:]:
        if ":" not in parte:
            raise ValueError(f"Métrica malformada: {parte}")
        nome, valor = parte.split(":", 1)
        if nome in metricas:
            raise ValueError(f"Métrica repetida: {nome}")
        if nome not in BASE_OBRIGATORIAS:
            raise ValueError("Esta calculadora aceita apenas as oito métricas do CVSS Base 3.1.")
        metricas[nome] = valor
    faltantes = [m for m in BASE_OBRIGATORIAS if m not in metricas]
    if faltantes:
        raise ValueError(f"Métricas base ausentes: {', '.join(faltantes)}")
    return metricas


@dataclass(frozen=True, slots=True)
class ResultadoCVSS:
    score: float
    severidade: str
    impacto: float
    explorabilidade: float
    vetor: str


class CalculadoraCVSS31:
    @staticmethod
    def calcular(vetor: str) -> ResultadoCVSS:
        m = interpretar_vetor(vetor)
        try:
            av = VALORES["AV"][m["AV"]]
            ac = VALORES["AC"][m["AC"]]
            ui = VALORES["UI"][m["UI"]]
            c, i, a = (VALORES["CIA"][m[k]] for k in ("C", "I", "A"))
            escopo = m["S"]
            if escopo not in {"U", "C"}:
                raise KeyError("S")
            pr_tabela = {
                "U": {"N": 0.85, "L": 0.62, "H": 0.27},
                "C": {"N": 0.85, "L": 0.68, "H": 0.50},
            }
            pr = pr_tabela[escopo][m["PR"]]
        except KeyError as erro:
            raise ValueError(f"Valor inválido no vetor CVSS: {erro}") from erro

        iss = 1 - ((1 - c) * (1 - i) * (1 - a))
        if escopo == "U":
            impacto = 6.42 * iss
        else:
            impacto = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)
        explorabilidade = 8.22 * av * ac * pr * ui

        if impacto <= 0:
            score = 0.0
        elif escopo == "U":
            score = round_up_1(min(impacto + explorabilidade, 10))
        else:
            score = round_up_1(min(1.08 * (impacto + explorabilidade), 10))

        return ResultadoCVSS(
            score=score,
            severidade=classificar_cvss(score).value,
            impacto=round(impacto, 4),
            explorabilidade=round(explorabilidade, 4),
            vetor=vetor.strip().upper(),
        )

    @staticmethod
    def ambiental(vetor,confidencialidade=None,integridade=None,disponibilidade=None):
        """FIRST 3.1 §7.3; CIA 1→Low, 2→Medium, 3/4→High."""
        if not isinstance(vetor,str):
            raise ValueError("Vetor deve ser texto.")
        m={}
        for trecho in vetor.upper().strip().split("/")[1:]:
            if trecho.count(":")!=1:
                raise ValueError("Métrica ambiental malformada.")
            chave,valor=trecho.split(":")
            if chave in m:
                raise ValueError("Métrica repetida.")
            m[chave]=valor
        base="CVSS:3.1/"+"/".join(f"{k}:{m[k]}" for k in BASE_OBRIGATORIAS if k in m)
        # Valida todas as métricas base sem alterar a calculadora base.
        CalculadoraCVSS31.calcular(base)
        adicionais={"CR":"XHML","IR":"XHML","AR":"XHML","E":"XHFPU","RL":"XUWTO","RC":"XCRU",
                    "MAV":"XNALP","MAC":"XLH","MPR":"XNLH","MUI":"XNR","MS":"XUC",
                    "MC":"XNLH","MI":"XNLH","MA":"XNLH"}
        if not vetor.strip().upper().startswith("CVSS:3.1/"):
            raise ValueError("Environmental exige CVSS:3.1.")
        for chave,valor in m.items():
            if chave not in BASE_OBRIGATORIAS and (chave not in adicionais or valor not in adicionais[chave] or len(valor)!=1):
                raise ValueError("Métrica ambiental inválida.")
        for nome,valor in zip(("CR","IR","AR"),(confidencialidade,integridade,disponibilidade)):
            if valor is not None:
                if type(valor) is not int or not 1<=valor<=4:
                    raise ValueError("Requisitos CIA devem estar entre 1 e 4.")
                m[nome]={1:"L",2:"M",3:"H",4:"H"}[valor]
        def modificada(chave):
            v=m.get("M"+chave,"X")
            return m[chave] if v=="X" else v
        requisitos={"X":1,"M":1,"H":1.5,"L":.5}
        c,i,a=(VALORES["CIA"][modificada(k)]*requisitos[m.get(r,"X")] for k,r in zip(("C","I","A"),("CR","IR","AR")))
        miss=min(1-(1-c)*(1-i)*(1-a),.915)
        escopo=modificada("S")
        impacto=6.42*miss if escopo=="U" else 7.52*(miss-.029)-3.25*(miss*.9731-.02)**13
        pr=({"N":.85,"L":.62,"H":.27} if escopo=="U" else {"N":.85,"L":.68,"H":.5})[modificada("PR")]
        exp=8.22*VALORES["AV"][modificada("AV")]*VALORES["AC"][modificada("AC")]*pr*VALORES["UI"][modificada("UI")]
        e={"X":1,"H":1,"F":.97,"P":.94,"U":.91}[m.get("E","X")]
        rl={"X":1,"U":1,"W":.97,"T":.96,"O":.95}[m.get("RL","X")]
        rc={"X":1,"C":1,"R":.96,"U":.92}[m.get("RC","X")]
        score=0.0 if impacto<=0 else round_up_1(round_up_1(min((impacto+exp)*(1 if escopo=="U" else 1.08),10))*e*rl*rc)
        completo="CVSS:3.1/"+"/".join(f"{k}:{v}" for k,v in m.items())
        return ResultadoCVSS(score,classificar_cvss(score).value,round(impacto,4),round(exp,4),completo)


def score_ambiental_ativo(vulnerabilidade,ativo):
    """3.0/4.0 usam score da fonte; nunca se passa vetor 3.0 pelo algoritmo 3.1."""
    if vulnerabilidade.cvss_versao=="3.1" and vulnerabilidade.cvss_vetor:
        return CalculadoraCVSS31.ambiental(vulnerabilidade.cvss_vetor,ativo.confidencialidade,
                                          ativo.integridade,ativo.disponibilidade).score
    return vulnerabilidade.cvss


def vetor_base31(vetor):
    """Valida vetor 3.1 completo e extrai as oito métricas para conferir a nota base."""
    CalculadoraCVSS31.ambiental(vetor)
    metricas=dict(trecho.split(":") for trecho in vetor.strip().upper().split("/")[1:])
    return "CVSS:3.1/"+"/".join(f"{k}:{metricas[k]}" for k in BASE_OBRIGATORIAS)
