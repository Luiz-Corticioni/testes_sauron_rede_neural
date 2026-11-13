"""Modelos SQL separados por responsabilidade; API pública preservada."""

from inventario.models.base import ModeloAuditavel, TravaDominio, ContadorAtivo, VersaoInventario
from inventario.models.salas import Sala
from inventario.models.ativos import Ativo
from inventario.models.vulnerabilidades import Vulnerabilidade
from inventario.models.incidencias import IncidenciasQuerySet, Incidencia
from inventario.models.dependencias import Dependencia
from inventario.models.operacionais import Incidente, CertificadoDigital, Software, Alerta
from inventario.models.imune import Anticorpo, Tolerancia, SugestaoImune
from inventario.models.historico import HistoricoIncidencia, SnapshotRisco, RegistroAuditoria

from inventario.models.mfa_email import DispositivoEmail

from inventario.models.limites_login import LimiteLogin

from inventario.models.epss import ObservacaoEPSS

from inventario.models.ssvc import AvaliacaoSSVC

from inventario.models.documentos import DocumentoInventario, ItemSBOM, AchadoComponente, DeclaracaoVEX
from inventario.models.relacoes import RelacaoAtivos
from inventario.models.cobertura import PerimetroRelacoes, MembroPerimetro, RevisaoCobertura

from inventario.models.honeypot import SensorHoneypot, EventoHoneypot
