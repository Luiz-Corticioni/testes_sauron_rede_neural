from enum import Enum


class TipoEquipamento(str, Enum):
    SERVIDOR = "1"
    NOTEBOOK = "2"
    ESTACAO = "3"
    SWITCH = "4"
    ROTEADOR = "5"
    IMPRESSORA = "6"
    APLICACAO_WEB = "7"
    BANCO_DADOS = "8"
    SOFTWARE = "9"

    @property
    def codigo(self) -> int:
        """Código inteiro da categoria; value preserva o formato textual legado."""
        return int(self.value)

    @property
    def rotulo(self) -> str:
        from inventario.dominio.equipamentos import Equipamento

        return Equipamento.REGISTRO[self].ROTULO


class SeveridadeCVSS(str, Enum):
    NENHUMA = "Nenhuma"
    BAIXA = "Baixa"
    MEDIA = "Média"
    ALTA = "Alta"
    CRITICA = "Crítica"


def classificar_cvss(score: float) -> SeveridadeCVSS:
    score = float(score)
    if not 0 <= score <= 10:
        raise ValueError("O CVSS deve estar entre 0 e 10.")
    if score == 0:
        return SeveridadeCVSS.NENHUMA
    if score < 4:
        return SeveridadeCVSS.BAIXA
    if score < 7:
        return SeveridadeCVSS.MEDIA
    if score < 9:
        return SeveridadeCVSS.ALTA
    return SeveridadeCVSS.CRITICA
