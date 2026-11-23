"""Envio manual com registro antecipado e sem repetição automática de tentativas."""
import base64
import re
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection, transaction

from inventario.aplicacao.autorizacao import exigir
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.infraestrutura.tickets import GLPI, Jira
from inventario.models import Incidencia, TicketRemediacao

PERMISSOES_TICKET = ("inventario.view_incidencia", "inventario.view_ativo", "inventario.view_vulnerabilidade",
                     "inventario.view_ticketremediacao", "inventario.add_ticketremediacao")


def adaptador(provedor):
    if provedor == "jira" and settings.SAURON_TICKETS_JIRA_ENABLED:
        usuario, token = settings.SAURON_JIRA_USER, settings.SAURON_JIRA_API_TOKEN
        if not usuario or not token or ":" in usuario or any(c in usuario + token for c in "\r\n"):
            raise ValueError("Credenciais Jira inválidas.")
        autorizacao = "Basic " + base64.b64encode(f"{usuario}:{token}".encode()).decode("ascii")
        return Jira(settings.SAURON_JIRA_URL, autorizacao,
                    settings.SAURON_JIRA_PROJECT, settings.SAURON_JIRA_ISSUE_TYPE)
    if provedor == "glpi" and settings.SAURON_TICKETS_GLPI_ENABLED:
        return GLPI(settings.SAURON_GLPI_URL, settings.SAURON_GLPI_SESSION_TOKEN, settings.SAURON_GLPI_APP_TOKEN)
    raise ValidationError("Integração desativada ou provedor inválido.")


def criar_ticket(incidencia_id, provedor, usuario):
    if connection.in_atomic_block:
        raise ValidationError("Envio externo exige execução fora de uma transação existente.")
    with transaction.atomic():
        travar_escrita()
        usuario = exigir(usuario, *PERMISSOES_TICKET)
        try:
            cliente = adaptador(provedor)
        except ValueError as erro:
            raise ValidationError("Configuração de integração inválida.") from erro
        inc = Incidencia.objects.select_related("vulnerabilidade").get(pk=incidencia_id)
        if inc.status not in {"ABERTA", "TRATAMENTO", "ACEITA", "MITIGADA"}:
            raise ValidationError("A incidência deve estar confirmada e ainda não corrigida.")
        cve = inc.vulnerabilidade.cve_id or inc.vulnerabilidade_id
        if any(not re.fullmatch(r"[A-Za-z0-9_.-]{1,50}", valor) for valor in (inc.pk, cve)):
            raise ValidationError("Os identificadores da incidência e vulnerabilidade devem ser simples, sem marcação.")
        existente = TicketRemediacao.objects.filter(incidencia=inc, provedor=provedor).first()
        if existente:
            return existente
        with usar_usuario(usuario):
            ticket = TicketRemediacao.objects.create(incidencia=inc, provedor=provedor,
                                                     estado="ENVIANDO", solicitado_por=usuario)
            registrar_evento("TICKET_INICIADO", "TicketRemediacao", ticket.pk,
                             {"incidencia": inc.pk, "provedor": provedor})
        titulo = f"Sauron: {inc.pk} - {cve}"
        referencia = f"Incidência Sauron {inc.pk}; prazo interno: {inc.prazo_correcao or 'não definido'}."
    try:
        externo = cliente.criar(titulo, referencia)
        estado = "CRIADO"
    except Exception:
        # Timeout, falha de conexão e resposta inválida podem ocorrer após criação.
        # Não registrar exceção: respostas/cabeçalhos podem conter credenciais.
        externo, estado = "", "INCERTO"
    with transaction.atomic():
        travar_escrita()
        ticket = TicketRemediacao.objects.select_for_update().get(pk=ticket.pk)
        with usar_usuario(usuario):
            ticket.estado, ticket.referencia_externa = estado, externo
            ticket.save(update_fields=["estado", "referencia_externa", "atualizado_em"])
            registrar_evento("TICKET_RESULTADO", "TicketRemediacao", ticket.pk,
                             {"estado": estado, "referencia": externo})
    return ticket
