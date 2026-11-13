"""Tipos declarativos: registro automático e comportamento por instância."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
import re
from typing import ClassVar
from inventario.dominio.enums import TipoEquipamento

ID_ATIVO_RE = re.compile(r"^[1-9][A-Z][0-9]{5}$")


def _como_tipo(tipo: TipoEquipamento | str) -> TipoEquipamento:
    return tipo if isinstance(tipo, TipoEquipamento) else TipoEquipamento(str(tipo))


def codigo_fabricante(fabricante: str) -> str:
    letras = "".join(c for c in fabricante.upper() if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    if not letras:
        raise ValueError("O fabricante deve possuir ao menos uma letra de A a Z.")
    return letras[0]


def gerar_id_ativo(tipo: TipoEquipamento | str, fabricante: str, sequencia: int) -> str:
    if not 0 < sequencia <= 99999:
        raise ValueError("A sequência do ativo deve estar entre 1 e 99999.")
    return f"{_como_tipo(tipo).value}{codigo_fabricante(fabricante)}{sequencia:05d}"


def validar_id_ativo(identificador: str, tipo: TipoEquipamento | str | None = None) -> str:
    identificador = identificador.strip().upper()
    if not ID_ATIVO_RE.fullmatch(identificador):
        raise ValueError("ID inválido. Use: tipo + fabricante + 5 números, ex.: 4H21444.")
    if tipo is not None and identificador[0] != _como_tipo(tipo).value:
        raise ValueError("O primeiro algarismo do ID não corresponde ao tipo do ativo.")
    return identificador


def gerar_hostname(tipo: TipoEquipamento | str, fabricante: str, sequencia: int) -> str:
    classe = Equipamento.REGISTRO[_como_tipo(tipo)]
    fab = "".join(c for c in fabricante.upper() if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return f"SAU-{classe.PREFIXO_HOST}-{fab[:4] or 'GEN'}-{sequencia:05d}"


@dataclass
class Equipamento(ABC):
    REGISTRO: ClassVar[dict[TipoEquipamento, type[Equipamento]]] = {}
    FATOR_BASE: ClassVar[float] = 1.0
    PREFIXO_HOST: ClassVar[str]
    ROTULO: ClassVar[str]
    id: str
    nome: str
    hostname: str
    fabricante: str
    modelo: str = ""
    ip: str = ""
    sistema_operacional: str = ""
    versao: str = ""
    responsavel: str = ""
    sala_id: str | None = None
    criticidade: int = 1
    metadados: dict = field(default_factory=dict)
    id_numerico: int | None = None

    @property
    @abstractmethod
    def TIPO(self) -> TipoEquipamento:
        """A subclasse concretiza o contrato declarando TIPO como ClassVar."""
        raise NotImplementedError

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        tipo = cls.__dict__.get("TIPO")
        if tipo is not None:
            tipo = _como_tipo(tipo)
            if tipo in Equipamento.REGISTRO:
                raise ValueError(f"Tipo {tipo.value} já registrado.")
            Equipamento.REGISTRO[tipo] = cls

    @property
    def tipo(self) -> TipoEquipamento:
        return self.TIPO

    @property
    def estado_operacional(self):
        return self.metadados.get("estado_operacional", {})

    def fator_exposicao(self) -> float:
        return self.FATOR_BASE

    def exibir_detalhes(self) -> str:
        return (
            f"{self.ROTULO} {self.hostname} ({self.id}) — {self.fabricante} {self.modelo}".strip()
        )

    def to_dict(self) -> dict:
        dados = asdict(self)
        dados.update(
            tipo=self.tipo.value, classe=type(self).__name__, fator_exposicao=self.fator_exposicao()
        )
        return dados

    @classmethod
    def from_dict(cls, dados: dict):
        dados = dict(dados)
        tipo = _como_tipo(dados.pop("tipo"))
        dados.pop("classe", None)
        dados.pop("fator_exposicao", None)
        dados["id"] = validar_id_ativo(dados["id"], tipo)
        numero = dados.get("id_numerico")
        if numero is not None and (type(numero) is not int or not 1 <= numero <= 2**63 - 1):
            raise ValueError("O ID numérico deve ser um inteiro positivo.")
        return cls.REGISTRO[tipo](**dados)


class Servidor(Equipamento):
    TIPO: ClassVar[TipoEquipamento] = TipoEquipamento.SERVIDOR
    FATOR_BASE: ClassVar[float] = 1.25
    PREFIXO_HOST: ClassVar[str] = "SRV"
    ROTULO: ClassVar[str] = "Servidor"

    def exibir_detalhes(self) -> str:
        sistema = f"{self.sistema_operacional} {self.versao}".strip() or "não informado"
        return f"{super().exibir_detalhes()} | sistema: {sistema}"


class Notebook(Equipamento):
    TIPO: ClassVar[TipoEquipamento] = TipoEquipamento.NOTEBOOK
    FATOR_BASE: ClassVar[float] = 1.05
    PREFIXO_HOST: ClassVar[str] = "NBK"
    ROTULO: ClassVar[str] = "Notebook"

    def exibir_detalhes(self) -> str:
        return f"{super().exibir_detalhes()} | custódia: {self.responsavel or 'não informada'}"


class EstacaoTrabalho(Equipamento):
    TIPO: ClassVar[TipoEquipamento] = TipoEquipamento.ESTACAO
    FATOR_BASE: ClassVar[float] = 1.0
    PREFIXO_HOST: ClassVar[str] = "WKS"
    ROTULO: ClassVar[str] = "Estação de Trabalho"


class Switch(Equipamento):
    TIPO: ClassVar[TipoEquipamento] = TipoEquipamento.SWITCH
    FATOR_BASE: ClassVar[float] = 1.15
    PREFIXO_HOST: ClassVar[str] = "SWT"
    ROTULO: ClassVar[str] = "Switch"


class Roteador(Equipamento):
    TIPO: ClassVar[TipoEquipamento] = TipoEquipamento.ROTEADOR
    FATOR_BASE: ClassVar[float] = 1.2
    PREFIXO_HOST: ClassVar[str] = "RTR"
    ROTULO: ClassVar[str] = "Roteador"

    def administracao_remota(self) -> bool:
        estado = self.estado_operacional
        remota = self.metadados.get("administracao_remota", False)
        portas = {
            p.get("porta") if isinstance(p, dict) else p for p in estado.get("portas_servicos", [])
        }
        return bool(remota or {22, 23, 3389, 8443} & portas)

    def fator_exposicao(self):
        fator = self.FATOR_BASE * (1.25 if self.estado_operacional.get("exposto_internet") else 1)
        return fator * (1.10 if self.administracao_remota() else 1)

    def exibir_detalhes(self) -> str:
        remota = "indicada no cadastro" if self.administracao_remota() else "não indicada"
        return f"{super().exibir_detalhes()} | administração remota: {remota}"


class ImpressoraRede(Equipamento):
    TIPO: ClassVar[TipoEquipamento] = TipoEquipamento.IMPRESSORA
    FATOR_BASE: ClassVar[float] = 0.75
    PREFIXO_HOST: ClassVar[str] = "PRN"
    ROTULO: ClassVar[str] = "Impressora de Rede"


class AplicacaoWeb(Equipamento):
    TIPO: ClassVar[TipoEquipamento] = TipoEquipamento.APLICACAO_WEB
    FATOR_BASE: ClassVar[float] = 1.35
    PREFIXO_HOST: ClassVar[str] = "WEB"
    ROTULO: ClassVar[str] = "Aplicação Web"

    def fator_exposicao(self):
        return self.FATOR_BASE * (1.25 if self.estado_operacional.get("exposto_internet") else 1)


class BancoDados(Equipamento):
    TIPO: ClassVar[TipoEquipamento] = TipoEquipamento.BANCO_DADOS
    FATOR_BASE: ClassVar[float] = 1.4
    PREFIXO_HOST: ClassVar[str] = "DBS"
    ROTULO: ClassVar[str] = "Banco de Dados"


class SoftwareLicenciado(Equipamento):
    TIPO: ClassVar[TipoEquipamento] = TipoEquipamento.SOFTWARE
    FATOR_BASE: ClassVar[float] = 0.9
    PREFIXO_HOST: ClassVar[str] = "SWL"
    ROTULO: ClassVar[str] = "Software Licenciado"


def criar_equipamento(dados: dict) -> Equipamento:
    """Nome público mantido para leitores JSON antigos; não há tabela manual."""
    return Equipamento.from_dict(dados)
