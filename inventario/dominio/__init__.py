"""Núcleo de domínio puro: não depende de Django nem de interface."""

from inventario.dominio.equipamentos import Equipamento, criar_equipamento
from inventario.dominio.vulnerabilidades import Vulnerabilidade, Incidencia, Dependencia

__all__ = [
    "Equipamento",
    "Vulnerabilidade",
    "Incidencia",
    "Dependencia",
    "criar_equipamento",
]
