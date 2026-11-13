from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import re

from inventario.dominio.enums import SeveridadeCVSS, classificar_cvss


CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
VUL_RE = re.compile(r"^VUL-[A-Z0-9]{2,8}-\d{4,}$")


@dataclass(slots=True)
class Vulnerabilidade:
    id: str
    descricao: str
    categoria: str
    cvss: float
    cve_id: str | None = None
    cvss_versao: str = "3.1"
    cvss_vetor: str = ""
    fonte: str = "Manual"
    publicada_em: str | None = None
    referencias: list[str] = field(default_factory=list)
    kev: bool = False
    kev_adicionada_em: str | None = None
    kev_prazo: str | None = None
    uso_ransomware: str = ""
    epss: float | None = None
    epss_data: str | None = None

    def __post_init__(self) -> None:
        self.id = self.id.strip().upper()
        if not VUL_RE.fullmatch(self.id):
            raise ValueError("ID de vulnerabilidade inválido. Ex.: VUL-RCE-0001.")
        if self.cve_id:
            self.cve_id = self.cve_id.strip().upper()
            if not CVE_RE.fullmatch(self.cve_id):
                raise ValueError("CVE inválido. Use CVE-AAAA-NNNN, com 4 ou mais dígitos finais.")
        classificar_cvss(self.cvss)
        if self.epss is not None:
            import math
            if isinstance(self.epss, bool) or not isinstance(self.epss, (int, float)) or not math.isfinite(self.epss) or not 0 <= self.epss <= 1:
                raise ValueError("EPSS deve ser número finito entre 0 e 1.")
        if self.epss_data is not None:
            try:
                date.fromisoformat(self.epss_data)
            except (TypeError, ValueError) as erro:
                raise ValueError("Data EPSS deve estar no formato AAAA-MM-DD.") from erro

    @property
    def severidade(self) -> SeveridadeCVSS:
        return classificar_cvss(self.cvss)

    def to_dict(self) -> dict:
        dados = asdict(self)
        dados["severidade"] = self.severidade.value
        return dados

    @classmethod
    def from_dict(cls, dados: dict) -> "Vulnerabilidade":
        dados = dict(dados)
        dados.pop("severidade", None)
        return cls(**dados)


@dataclass(slots=True)
class Incidencia:
    id: str
    equipamento_id: str
    vulnerabilidade_id: str
    status: str = "ABERTA"
    detectada_em: str = field(default_factory=lambda: date.today().isoformat())
    versao_afetada: str = ""
    observacoes: str = ""
    prazo_correcao: str | None = None
    aceita_por_id: int | None = None
    justificativa: str = ""
    aceita_ate: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class Dependencia:
    dependente_id: str
    fornecedor_id: str
    peso: float
    descricao: str = ""

    def __post_init__(self) -> None:
        self.peso = float(self.peso)
        if self.dependente_id == self.fornecedor_id:
            raise ValueError("Um ativo não pode depender de si próprio.")
        if not 0 <= self.peso < 1:
            raise ValueError("O peso da dependência deve estar em [0, 1).")

    def to_dict(self) -> dict:
        return asdict(self)
