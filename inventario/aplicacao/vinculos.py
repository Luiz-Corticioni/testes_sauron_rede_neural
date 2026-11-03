"""Casos de uso da ficha do ativo; consulta externa não confirma incidência."""

from django.db import transaction

from inventario.aplicacao.cadastros import salvar_cadastro
from inventario.aplicacao.operacao import exigir
from inventario.infraestrutura.auditoria import travar_escrita
from inventario.models import Incidencia


@transaction.atomic
def vincular_existente(incidencia, usuario):
    travar_escrita()
    usuario = exigir(usuario, "inventario.view_ativo", "inventario.view_vulnerabilidade", "inventario.add_incidencia")
    existente = Incidencia.objects.filter(
        ativo_id=incidencia.ativo_id, vulnerabilidade_id=incidencia.vulnerabilidade_id
    ).first()
    if existente:
        # Reenvio nunca reabre uma falha corrigida nem sobrescreve um aceite.
        return existente, False
    return salvar_cadastro(incidencia, usuario), True


@transaction.atomic
def cadastrar_e_vincular(vulnerabilidade, ativo, usuario):
    """Ou cadastro, incidência e auditoria são confirmados juntos, ou nada é gravado."""
    travar_escrita()
    usuario = exigir(usuario, "inventario.view_ativo", "inventario.view_vulnerabilidade", "inventario.add_vulnerabilidade", "inventario.add_incidencia")
    salvar_cadastro(vulnerabilidade, usuario)
    incidencia = Incidencia(
        ativo=ativo, vulnerabilidade=vulnerabilidade, status=Incidencia.Status.SUGERIDA,
        observacoes="Cadastro contextual: revisar versão/produto antes de confirmar a incidência.",
    )
    return salvar_cadastro(incidencia, usuario)
